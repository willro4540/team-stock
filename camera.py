"""
camera.py — cv2 카메라 촬영·GPS 위치 기록 (파트3)
────────────────────────────────────────
· 계획서 예외처리 명세: "사진 등록 실패 시에도 등록 가능하도록"
  → try/except 로 감싸고, 실패하면 (경로 "", GPS "") 반환 후 등록은 계속 진행
· cv2가 없거나 카메라가 없는 PC(실습실)에서도 앱이 죽지 않게
  import 자체를 try로 감쌈 — "없어도 돌아가는 코드"가 현장용 프로그램의 기본
· GPS: 노트북에는 GPS 센서가 없어 상수 좌표(창고 위치)를 기록.
  실제 폰 배포 시 EXIF GPS 태그 기록으로 교체하는 확장 지점 (주석 참고)
"""
from datetime import datetime
from pathlib import Path

try:
    import cv2                      # OpenCV — 없으면 촬영 기능만 비활성
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

PHOTO_DIR = Path(__file__).parent / "data" / "photos"

# 창고 고정 좌표 (광주 인재개발원 인근 예시값)
WAREHOUSE_GPS = "35.15N, 126.85E"


def take_photo() -> tuple[str, str]:
    """
    카메라 1장 촬영 → (사진 경로, GPS 문자열) 반환.
    어떤 이유로든 실패하면 ("", "") — 호출한 쪽은 등록을 계속 진행하면 됨.
    """
    if not HAS_CV2:
        return "", ""
    try:
        cap = cv2.VideoCapture(0)            # 0번 = 기본 카메라
        ok, frame = cap.read()               # 1프레임 읽기 = 촬영
        cap.release()
        if not ok:
            return "", ""
        PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        path = PHOTO_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(str(path), frame)
        # ── 확장 지점: EXIF GPS 태그 기록 ──
        # piexif 라이브러리로 path 파일에 GPSLatitude/GPSLongitude 태그를
        # 직접 쓸 수 있음. 여기서는 기록(JSON)에 GPS 문자열로 남김.
        return str(path), WAREHOUSE_GPS
    except Exception:
        return "", ""                        # ★ 실패해도 앱은 계속


# ── 단독 테스트 (학습용) ──────────────────────────────
# if __name__ == "__main__":
#     path, gps = take_photo()
#     if path:
#         print("촬영 성공:", path, "/ GPS:", gps)
#     else:
#         print("카메라 없음 or 실패 — 그래도 프로그램은 정상 (예외처리 확인)")
