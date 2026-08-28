"""
main.py — TeamStock 실행 진입점
────────────────────────────────────────
실행:  python main.py
· import 연동 관계 (표준참고문서 4.3):
    main.py → tab_window.py → (user_logic, storage_map, stock_inout,
                                chat_screen, board_screen) → 각 logic → 각 save
· 시연 계정: admin/admin123 · stocker/stocker123 · employee/employee123
· 채팅 사용법: admin 로그인 → 채팅 탭 → [서버 시작] → [연결]
              다른 PC는 관리자 PC의 IP 입력 후 [연결]
"""
import sys

from PySide6.QtWidgets import QApplication

from tab_window import TabWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")            # OS 상관없이 통일된 룩
    win = TabWindow()
    win.show()
    sys.exit(app.exec())
