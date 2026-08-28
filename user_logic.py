"""
user_logic.py — 회원가입·로그인·초대코드 (파트1)
────────────────────────────────────────
· 로직(Model) 계층: 판단은 전부 여기서. 화면(tab_window.py)은 결과만 표시
· 핵심 규칙 (표준참고문서 5.2~5.3):
  1) 가입은 초대코드 필수 → 통과 시 기본 등급 C(employee)
     B(자재담당)는 관리자가 부여, A(관리자)는 코드 발급 권한
  2) 초대코드 = SHA-256(관리자ID+발급일시) 앞 8자리 대문자, 1회용(used)
  3) 로그인 5회 실패 → 5분 잠금 (locked_until 에 해제 시각 저장)
"""
import time
import hashlib
from datetime import datetime

from pw_hash import hash_password
from user_save import MemberStorage

LOCK_SECONDS = 300      # 5분
MAX_FAIL = 5


class MemberModel:
    def __init__(self):
        self.storage = MemberStorage()
        self._seed_defaults()

    # ── 시연용 기본 계정 3개 (실제 배포 시 제거) ──
    def _seed_defaults(self):
        data = self.storage.load()
        if data["members"]:
            return
        for uid, pw, name, role in [
            ("admin",    "admin123",    "관리자", "A"),
            ("stocker",  "stocker123",  "박담당", "B"),
            ("employee", "employee123", "이직원", "C"),
        ]:
            data["members"].append({
                "id": uid,
                "password_hash": hash_password(pw),   # 평문 저장 금지!
                "name": name, "email": "", "phone": "",
                "role": role,
                "fail_count": 0, "locked_until": 0,
            })
        self.storage.save(data)

    # ── 초대코드 발급 (admin 전용) ──
    def make_invite(self, admin_id: str) -> str:
        now = datetime.now().strftime("%Y%m%d%H%M%S%f")
        # 관리자ID + 발급일시 → 해시 앞 8자리 (문서 5.3 명세 그대로)
        code = hashlib.sha256(f"{admin_id}{now}".encode()).hexdigest()[:8].upper()
        data = self.storage.load()
        data["invite_codes"].append({"code": code, "used": False,
                                     "issued_by": admin_id, "used_by": ""})
        self.storage.save(data)
        return code

    def invite_list(self) -> list:
        return self.storage.load()["invite_codes"]

    # ── 회원가입: 초대코드 검증이 관문 ──
    def register(self, code, user_id, password, name) -> tuple[bool, str]:
        if not all([code, user_id, password, name]):
            return False, "모든 항목을 입력해주세요."
        data = self.storage.load()

        # 1) 초대코드 검증 — used:False 인 코드만 통과
        inv = next((c for c in data["invite_codes"]
                    if c["code"] == code.upper() and not c["used"]), None)
        if inv is None:
            return False, "초대코드가 유효하지 않거나 이미 사용되었습니다."

        # 2) ID 중복 검사
        if any(m["id"] == user_id for m in data["members"]):
            return False, "이미 사용 중인 아이디입니다."

        # 3) 저장 — 초대코드 가입은 무조건 C등급 (역할을 본인이 고르지 않음)
        data["members"].append({
            "id": user_id, "password_hash": hash_password(password),
            "name": name, "email": "", "phone": "",
            "role": "C", "fail_count": 0, "locked_until": 0,
        })
        inv["used"] = True                 # 1회용 → 즉시 만료
        inv["used_by"] = name
        self.storage.save(data)
        return True, "가입 완료! 로그인해주세요. (등급: C 일반직원)"

    # ── 로그인: 해시 비교 + 5회 잠금 ──
    def login(self, user_id, password) -> tuple[bool, str, dict]:
        data = self.storage.load()
        m = next((x for x in data["members"] if x["id"] == user_id), None)
        if m is None:
            return False, "계정을 찾을 수 없습니다.", {}

        # 잠금 확인 — 현재시각 < 해제시각이면 거부
        remain = int(m["locked_until"] - time.time())
        if remain > 0:
            return False, f"계정 잠김 — {remain // 60}분 {remain % 60}초 후 재시도", {}

        # 입력 비번을 해시해서 저장된 해시와 비교 (원문 비교가 아님!)
        if hash_password(password) == m["password_hash"]:
            m["fail_count"] = 0
            m["locked_until"] = 0
            self.storage.save(data)
            return True, "로그인 성공", m

        m["fail_count"] += 1
        if m["fail_count"] >= MAX_FAIL:
            m["locked_until"] = time.time() + LOCK_SECONDS
            self.storage.save(data)
            return False, f"{MAX_FAIL}회 실패 — 5분간 잠깁니다.", {}
        self.storage.save(data)
        return False, f"비밀번호 오류 ({m['fail_count']}/{MAX_FAIL}회)", {}


# ── 단독 테스트 (학습용) ──────────────────────────────
# if __name__ == "__main__":
#     logic = MemberModel()
#     print(logic.login("admin", "admin123"))       # 성공
#     print(logic.login("admin", "틀린비번"))        # 실패 카운트 증가
#     code = logic.make_invite("admin")
#     print("발급 코드:", code)
#     print(logic.register(code, "test1", "pw1234", "테스트"))   # 성공
#     print(logic.register(code, "test2", "pw1234", "테스트2"))  # 코드 재사용 → 실패
