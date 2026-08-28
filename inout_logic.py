"""
inout_logic.py — 입출고 데이터 처리 (파트3)
────────────────────────────────────────
· 흐름 3가지 (표준참고문서 5.5 파트3):
  출고: 수량 확인(QDialog는 화면 담당) → 여기서 재고 차감 + 기록
  입고: 등록 → pending 목록 → 관리자 승인 → 그때 재고 반영
  반납: 출고 기록을 찾아 재고 재반영 [3차 기능]
· 기록(record) = 직원명·품목·수량·일시·사진경로·GPS — 책임소재의 근거
"""
import uuid
from datetime import datetime

from stock_save import StockStorage
from stock_logic import StockModel

SPECIAL_PREFIX = "특수브라켓"     # 이 접두어면 검수 절차 강제 (admin 전용)


class InoutModel:
    def __init__(self):
        self.storage = StockStorage()
        self.stock = StockModel()

    # ── 내부: 품목 찾기 ──
    def _find(self, data, wh, zone, name):
        for i in data[wh][zone]:
            if i["품목명"] == name:
                return i
        return None

    def _record(self, data, kind, member, wh, zone, name, qty, photo="", gps="", memo=""):
        data["records"].insert(0, {                  # 최신이 맨 앞
            "record_id": uuid.uuid4().hex[:8],
            "종류": kind,                             # 출고 / 입고 / 반납
            "직원명": member["name"], "창고": wh, "구역": zone,
            "품목": name, "수량": qty,
            "일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "사진": photo, "GPS": gps, "메모": memo,
            "반납됨": False,
        })

    # ── 출고: 화면의 QDialog에서 "확정" 눌렀을 때 호출 ──
    def stock_out(self, member, wh, zone, name, qty, photo="", gps="", memo="") -> tuple[bool, str]:
        data = self.storage.load()
        item = self._find(data, wh, zone, name)
        if item is None:
            return False, "품목을 찾을 수 없습니다."
        if qty <= 0 or qty > item["수량"]:
            return False, f"출고 수량 오류 (보유 {item['수량']}개)"
        item["수량"] -= qty                           # ★ 재고 차감
        self._record(data, "출고", member, wh, zone, name, qty, photo, gps, memo)
        self.storage.save(data)
        low = " ⚠ 재고 부족 상태!" if item["수량"] < item["최소수량"] else ""
        return True, f"출고 완료 — 남은 재고 {item['수량']}개{low}"

    # ── 입고 등록: 바로 반영하지 않고 pending에 넣음 ──
    def stock_in_request(self, member, wh, zone, name, qty, photo="", gps="", memo="",
                         inspected=False) -> tuple[bool, str]:
        if qty <= 0:
            return False, "입고 수량 오류"
        data = self.storage.load()
        data["pending"].append({
            "pending_id": uuid.uuid4().hex[:8],
            "직원명": member["name"], "창고": wh, "구역": zone,
            "품목": name, "수량": qty,
            "일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "사진": photo, "GPS": gps, "메모": memo,
            "검수완료": inspected,                    # 특수브라켓이면 True 필수
        })
        self.storage.save(data)
        return True, "입고 등록 완료 — 관리자 승인 후 재고 반영됩니다."

    def pending_list(self) -> list:
        return self.storage.load()["pending"]

    # ── 승인: 이 순간에만 재고가 실제로 늘어남 ──
    def approve(self, admin, pending_id) -> tuple[bool, str]:
        data = self.storage.load()
        p = next((x for x in data["pending"] if x["pending_id"] == pending_id), None)
        if p is None:
            return False, "대기 건을 찾을 수 없습니다."
        item = self._find(data, p["창고"], p["구역"], p["품목"])
        if item is None:                              # 신규 품목이면 새로 추가
            item = {"품목명": p["품목"], "수량": 0,
                    "입고일": datetime.now().strftime("%Y-%m-%d"), "최소수량": 5}
            data[p["창고"]][p["구역"]].append(item)
        item["수량"] += p["수량"]                      # ★ 재고 반영
        item["입고일"] = datetime.now().strftime("%Y-%m-%d")
        data["pending"].remove(p)
        self._record(data, "입고", admin, p["창고"], p["구역"], p["품목"], p["수량"],
                     p["사진"], p["GPS"], f"등록:{p['직원명']} → 승인:{admin['name']}")
        self.storage.save(data)
        return True, f"승인 완료 — {p['품목']} +{p['수량']}개 반영"

    def reject(self, pending_id) -> tuple[bool, str]:
        data = self.storage.load()
        before = len(data["pending"])
        data["pending"] = [x for x in data["pending"] if x["pending_id"] != pending_id]
        self.storage.save(data)
        return (True, "반려 완료") if len(data["pending"]) < before else (False, "대상 없음")

    # ── 반납 [3차]: 출고 기록 기준으로 재고 재반영 ──
    def return_item(self, member, record_id) -> tuple[bool, str]:
        data = self.storage.load()
        rec = next((r for r in data["records"]
                    if r["record_id"] == record_id and r["종류"] == "출고"
                    and not r["반납됨"]), None)
        if rec is None:
            return False, "반납 가능한 출고 기록이 없습니다."
        item = self._find(data, rec["창고"], rec["구역"], rec["품목"])
        if item is None:
            return False, "품목이 삭제되어 반납 불가"
        item["수량"] += rec["수량"]                    # ★ 재고 재반영
        rec["반납됨"] = True
        self._record(data, "반납", member, rec["창고"], rec["구역"], rec["품목"], rec["수량"])
        self.storage.save(data)
        return True, f"반납 완료 — {rec['품목']} +{rec['수량']}개"

    def records(self) -> list:
        return self.storage.load()["records"]

    # ── 특수브라켓 판별 — True면 화면에서 검수 체크리스트 강제 ──
    @staticmethod
    def is_special(name: str) -> bool:
        return name.startswith(SPECIAL_PREFIX)


# ── 단독 테스트 (학습용) ──────────────────────────────
# if __name__ == "__main__":
#     m = InoutModel()
#     me = {"name": "테스트직원"}
#     print(m.stock_out(me, "창고1", "D구역", "안전모", 2))
#     ok, msg = m.stock_in_request(me, "창고1", "B구역", "너트", 100)
#     print(msg)
#     pid = m.pending_list()[-1]["pending_id"]
#     print(m.approve({"name": "관리자"}, pid))
#     rid = m.records()[-1]["record_id"]     # 방금 출고 기록
#     print(m.is_special("특수브라켓 A형"), m.is_special("안전모"))
