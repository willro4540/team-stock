"""
stock_save.py — stock.json 읽기·쓰기 (파트2)
────────────────────────────────────────
· stock.json 구조 (표준참고문서 6.2 + 확장):
    {
      "창고1": {"A구역":[{품목명,수량,입고일,최소수량}, ...], "B구역":[...], ...},
      "창고2": {...},
      "pending": [...],   # 확장: 입고 승인 대기 목록 (승인 전 재고 미반영)
      "records": [...]    # 확장: 입출고 기록 (직원명·품목·수량·일시·사진·GPS)
    }
· 구역 명세: A선반=브라켓류 / B선반=볼트류 / C선반=공구 / D바닥=안전용품
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
FILE = DATA_DIR / "stock.json"


def _seed() -> dict:
    """첫 실행 시 만들어지는 초기 재고 (목업 v16과 동일한 시연 데이터)"""
    def item(name, qty, date, min_qty):
        return {"품목명": name, "수량": qty, "입고일": date, "최소수량": min_qty}
    return {
        "창고1": {
            "A구역": [
                item("소형브라켓", 200, "2026-06-24", 50),
                item("중형브라켓", 120, "2026-06-20", 50),
                item("대형브라켓", 12,  "2026-06-25", 50),      # 부족 시연용
                item("특수브라켓 A형", 15, "2026-06-27", 5),
                item("특수브라켓 B형", 8,  "2026-06-27", 5),
                item("특수브라켓 C형", 20, "2026-06-26", 5),
                item("특수브라켓 D형", 6,  "2026-06-28", 5),
            ],
            "B구역": [
                item("앙카볼트", 500, "2026-06-22", 100),
                item("육각볼트", 800, "2026-06-23", 100),
                item("너트", 900, "2026-06-23", 100),
                item("와셔", 1200, "2026-06-21", 100),
            ],
            "C구역": [
                item("전동드릴", 6, "2026-06-15", 2),
                item("스패너세트", 10, "2026-06-18", 3),
                item("공구박스", 8, "2026-06-18", 3),
            ],
            "D구역": [
                item("안전장갑(3M)", 8, "2026-06-25", 30),      # 부족 시연용
                item("안전모", 40, "2026-06-19", 10),
                item("안전조끼", 35, "2026-06-19", 10),
                item("작업복", 25, "2026-06-17", 10),
            ],
        },
        "창고2": {
            "A구역": [item("소형브라켓", 80, "2026-06-26", 30)],
            "B구역": [item("앙카볼트", 200, "2026-06-26", 50)],
            "C구역": [item("스패너세트", 4, "2026-06-26", 2)],
            "D구역": [item("안전모", 15, "2026-06-26", 5)],
        },
        "pending": [],
        "records": [],
    }


class StockStorage:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        if not FILE.exists():
            self.save(_seed())

    def load(self) -> dict:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: dict):
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ── 단독 테스트 (학습용) ──────────────────────────────
# if __name__ == "__main__":
#     st = StockStorage()
#     d = st.load()
#     for zone, items in d["창고1"].items():
#         print(zone, "→", [i["품목명"] for i in items])
