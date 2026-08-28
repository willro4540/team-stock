"""
stock_logic.py — 재고 조회·검색·선입선출 (파트2)
────────────────────────────────────────
· 선입선출(FIFO) = 입고일 오름차순 정렬 → 리스트 맨 앞이 "먼저 출고할 것"
  → sorted(key=...) 한 줄이 곧 선입선출 구현
· 부족 판정 = 수량 < 최소수량  (조건문 if 하나가 알림의 근거)
"""
from stock_save import StockStorage


class StockModel:
    def __init__(self):
        self.storage = StockStorage()

    # ── 구역 품목 조회 (선입선출 정렬 적용) ──
    def zone_items(self, warehouse: str, zone: str) -> list:
        data = self.storage.load()
        items = data.get(warehouse, {}).get(zone, [])
        # 입고일 문자열이 "YYYY-MM-DD" 형식이라 문자열 정렬 = 날짜 정렬
        return sorted(items, key=lambda i: i["입고일"])

    # ── 실시간 검색 — QLineEdit.textChanged 마다 호출됨 ──
    def search(self, warehouse: str, zone: str, keyword: str) -> list:
        return [i for i in self.zone_items(warehouse, zone)
                if keyword in i["품목명"]]          # 부분일치 색인

    # ── 부족 판정 ──
    @staticmethod
    def is_low(item: dict) -> bool:
        return item["수량"] < item["최소수량"]

    # ── 부족 품목 전체 수집 → 알림 목록의 재료 ──
    def low_items(self) -> list:
        data = self.storage.load()
        result = []
        for wh in ("창고1", "창고2"):
            for zone, items in data.get(wh, {}).items():
                for i in items:
                    if self.is_low(i):
                        result.append({"창고": wh, "구역": zone, **i})
        return result

    # ── 구역에 부족 품목이 하나라도 있으면 배치도에서 빨간 표시 ──
    def zone_has_low(self, warehouse: str, zone: str) -> bool:
        return any(self.is_low(i) for i in self.zone_items(warehouse, zone))


# ── 단독 테스트 (학습용) ──────────────────────────────
# if __name__ == "__main__":
#     m = StockModel()
#     for i in m.zone_items("창고1", "A구역"):
#         print(i["입고일"], i["품목명"], "◀ 먼저 출고" if i == m.zone_items("창고1","A구역")[0] else "")
#     print("검색 '특수':", [i["품목명"] for i in m.search("창고1", "A구역", "특수")])
#     print("부족:", [(i["품목명"], i["수량"]) for i in m.low_items()])
