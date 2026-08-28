"""
user_save.py — member.json 읽기·쓰기 (파트1)
────────────────────────────────────────
· 저장(Storage) 계층: 파일 입출력만 담당. 검증·판단 로직은 user_logic.py 몫
· 역할을 나누는 이유 = 나중에 JSON을 DB로 바꿔도 이 파일만 고치면 됨
· member.json 구조 (표준참고문서 6.1):
    {"members": [...], "invite_codes": [...]}
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"   # 프로젝트/data 폴더
FILE = DATA_DIR / "member.json"


class MemberStorage:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        if not FILE.exists():                # 첫 실행 시 자동 생성
            self.save({"members": [], "invite_codes": []})

    def load(self) -> dict:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: dict):
        # ensure_ascii=False: 한글이 \uXXXX 로 깨지지 않게 / indent=2: 사람이 읽기 좋게
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ── 단독 테스트 (학습용) ──────────────────────────────
# if __name__ == "__main__":
#     st = MemberStorage()
#     d = st.load()
#     print("직원 수:", len(d["members"]))
#     print("초대코드 수:", len(d["invite_codes"]))
