"""
board_save.py — board.json 읽기·쓰기 (파트5)
────────────────────────────────────────
· board.json 구조 (표준참고문서 6.3):
    {"posts": [{id, author, title, content, created_at, status}, ...]}
· status 3단계: 미확인 → 확인 → 처리완료  (담당자 오프라인 시 문의용)
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
FILE = DATA_DIR / "board.json"


class BoardStorage:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        if not FILE.exists():
            self.save({"posts": []})

    def load(self) -> dict:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: dict):
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ── 단독 테스트 (학습용) ──────────────────────────────
# if __name__ == "__main__":
#     st = BoardStorage()
#     print("게시글 수:", len(st.load()["posts"]))
