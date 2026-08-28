"""
pw_hash.py — 비밀번호 해시 변환 (파트1)
────────────────────────────────────────
· hashlib SHA-256 = 단방향 해시. 원문 복원 불가 → 평문 저장 금지 원칙
· 로그인 검증은 "입력값을 다시 해시해서 저장된 해시와 비교"하는 방식
· 커리큘럼 File 8강 내용 (교수님 회원가입 과제)
"""
import hashlib


def hash_password(password: str) -> str:
    # encode(): str → bytes (해시 함수는 bytes만 받음)
    # hexdigest(): 해시 결과를 16진수 문자열로 (JSON 저장용)
    return hashlib.sha256(password.encode()).hexdigest()


# ── 단독 테스트 (학습용) ──────────────────────────────
# 주석을 풀고  python pw_hash.py  로 실행해보기
# if __name__ == "__main__":
#     h1 = hash_password("1234")
#     h2 = hash_password("1234")
#     print(h1)                  # 같은 입력 → 항상 같은 해시
#     print(h1 == h2)            # True
#     print(hash_password("1235") == h1)  # 한 글자만 달라도 False
