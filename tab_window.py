"""
tab_window.py — 로그인·회원가입·메인 화면 (파트1)
────────────────────────────────────────
· 문서 명세: QTabWidget으로 로그인/회원가입 탭 분리 (교수님 8·9강 과제 구조)
· 전체 화면 흐름 (QStackedWidget 인덱스):
    0 = AuthTabs(QTabWidget: 로그인 | 회원가입)
    1 = MainView (로그인 성공 시 생성)
· MainView = 목업 v16의 2행 상단바(시계+벨뱃지 / 이름+등급) + 기능 탭 5개
· 부족 알림: 벨 클릭 → NotiDialog. 뱃지 숫자 = StockModel.low_items() 개수
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QStackedWidget, QMessageBox, QDialog, QFrame,
)
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtGui import QPixmap

from user_logic import MemberModel
from stock_logic import StockModel
from inout_logic import InoutModel
from storage_map import WarehouseView
from stock_inout import InoutView
from chat_screen import ChatView
from board_screen import BoardView

ASSETS = Path(__file__).parent / "assets"
ROLE_KR = {"A": "관리자", "B": "자재담당", "C": "일반직원"}
ROLE_STYLE = {   # 목업의 role-pill 3색
    "A": "background:#fee2e2;color:#b91c1c;",
    "B": "background:#fef3c7;color:#92400e;",
    "C": "background:#dbeafe;color:#1e40af;",
}


class LoginView(QWidget):
    """로그인 탭 — QLineEdit EchoMode.Password로 비번 마스킹"""

    def __init__(self, model: MemberModel, on_login):
        super().__init__()
        self.model, self.on_login = model, on_login
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignTop)
        lay.setContentsMargins(40, 30, 40, 20)

        logo = QLabel()
        pm = QPixmap(str(ASSETS / "logo.png"))
        if not pm.isNull():
            logo.setPixmap(pm.scaledToWidth(72, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        name = QLabel("TeamStock")
        name.setStyleSheet("font-size:20px;font-weight:800;color:#1d4ed8;")
        name.setAlignment(Qt.AlignCenter)
        lay.addWidget(logo); lay.addWidget(name); lay.addSpacing(14)

        self.id_inp = QLineEdit(); self.id_inp.setPlaceholderText("ID")
        self.pw_inp = QLineEdit(); self.pw_inp.setPlaceholderText("PW")
        self.pw_inp.setEchoMode(QLineEdit.Password)     # ★ 마스킹 (문서 명세)
        self.pw_inp.returnPressed.connect(self._login)  # 엔터로 로그인
        for w in (self.id_inp, self.pw_inp):
            w.setStyleSheet("min-height:44px;padding-left:12px;font-size:14px;"
                            "border:1.5px solid #e4e7ec;border-radius:9px;background:#f0f2f5;")
            lay.addWidget(w)

        btn = QPushButton("로그인")
        btn.setStyleSheet("background:#1d4ed8;color:white;min-height:46px;"
                          "border-radius:9px;font-size:15px;font-weight:700;")
        btn.clicked.connect(self._login)               # clicked.connect (문서 명세)
        lay.addWidget(btn)

        # 5회 잠금 안내 배너 — 잠겼을 때만 보임
        self.lock_lbl = QLabel()
        self.lock_lbl.setStyleSheet("background:#fef2f2;border:1.5px solid #fecaca;"
                                    "border-radius:9px;padding:10px;color:#b91c1c;")
        self.lock_lbl.setAlignment(Qt.AlignCenter)
        self.lock_lbl.hide()
        lay.addWidget(self.lock_lbl)

        hint = QLabel("시연 계정: admin/admin123 · stocker/stocker123 · employee/employee123")
        hint.setStyleSheet("font-size:10.5px;color:#9ca3af;")
        hint.setAlignment(Qt.AlignCenter)
        lay.addWidget(hint)

    def _login(self):
        ok, msg, member = self.model.login(self.id_inp.text().strip(),
                                           self.pw_inp.text())
        if ok:
            self.lock_lbl.hide()
            self.pw_inp.clear()
            self.on_login(member)          # 성공 → TabWindow가 메인으로 전환
        else:
            if "잠" in msg:                 # 잠금 메시지는 빨간 배너로
                self.lock_lbl.setText(msg)
                self.lock_lbl.show()
            else:
                QMessageBox.warning(self, "로그인 실패", msg)


class SignupView(QWidget):
    """회원가입 탭 — 초대코드가 관문. 역할 선택란은 일부러 없음(무조건 C)"""

    def __init__(self, model: MemberModel, on_done):
        super().__init__()
        self.model, self.on_done = model, on_done
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignTop)
        lay.setContentsMargins(40, 30, 40, 20)

        self.code = QLineEdit(); self.code.setPlaceholderText("초대코드 (예: A3F9B2C1)")
        self.code.setStyleSheet("min-height:44px;padding-left:12px;font-weight:700;"
                                "letter-spacing:1px;border:1.5px solid #93c5fd;"
                                "border-radius:9px;background:#eff6ff;color:#1d4ed8;")
        lay.addWidget(self.code)

        self.name_inp = QLineEdit(); self.name_inp.setPlaceholderText("이름")
        self.id_inp = QLineEdit(); self.id_inp.setPlaceholderText("ID")
        self.pw_inp = QLineEdit(); self.pw_inp.setPlaceholderText("PW")
        self.pw2_inp = QLineEdit(); self.pw2_inp.setPlaceholderText("PW 확인")
        self.pw_inp.setEchoMode(QLineEdit.Password)
        self.pw2_inp.setEchoMode(QLineEdit.Password)
        for w in (self.name_inp, self.id_inp, self.pw_inp, self.pw2_inp):
            w.setStyleSheet("min-height:44px;padding-left:12px;font-size:14px;"
                            "border:1.5px solid #e4e7ec;border-radius:9px;background:#f0f2f5;")
            lay.addWidget(w)

        btn = QPushButton("가입하기")
        btn.setStyleSheet("background:#1d4ed8;color:white;min-height:46px;"
                          "border-radius:9px;font-size:15px;font-weight:700;")
        btn.clicked.connect(self._signup)
        lay.addWidget(btn)

        hint = QLabel("초대코드 검증 통과 시에만 가입 (기본 등급 C)\nB등급은 관리자가 부여")
        hint.setStyleSheet("font-size:11px;color:#6b7280;")
        hint.setAlignment(Qt.AlignCenter)
        lay.addWidget(hint)

    def _signup(self):
        if self.pw_inp.text() != self.pw2_inp.text():
            QMessageBox.warning(self, "안내", "비밀번호 확인이 일치하지 않습니다.")
            return
        ok, msg = self.model.register(self.code.text().strip(),
                                      self.id_inp.text().strip(),
                                      self.pw_inp.text(),
                                      self.name_inp.text().strip())
        (QMessageBox.information if ok else QMessageBox.warning)(self, "회원가입", msg)
        if ok:
            self.on_done()                 # 로그인 탭으로 이동


class InviteView(QWidget):
    """초대코드 발급 (admin 전용 탭) — SHA-256 앞 8자리, 1회용"""

    def __init__(self, model: MemberModel, member: dict):
        super().__init__()
        self.model, self.member = model, member
        self.lay = QVBoxLayout(self)

        self.code_lbl = QLabel("—")
        self.code_lbl.setAlignment(Qt.AlignCenter)
        self.code_lbl.setStyleSheet("font-size:26px;font-weight:800;letter-spacing:4px;"
                                    "color:#1d4ed8;border:2px dashed #1d4ed8;"
                                    "border-radius:12px;padding:18px;")
        self.lay.addWidget(self.code_lbl)
        meta = QLabel("관리자ID + 발급일시 → SHA-256 앞 8자리 · 1회용")
        meta.setStyleSheet("font-size:11px;color:#6b7280;")
        meta.setAlignment(Qt.AlignCenter)
        self.lay.addWidget(meta)

        btn = QPushButton("+ 새 코드 발급")
        btn.setStyleSheet("background:#1d4ed8;color:white;min-height:42px;"
                          "border-radius:9px;font-weight:700;")
        btn.clicked.connect(self._issue)
        self.lay.addWidget(btn)

        self.hist_box = QVBoxLayout()
        self.lay.addLayout(self.hist_box)
        self.lay.addStretch()
        self._refresh_hist()

    def _issue(self):
        code = self.model.make_invite(self.member["id"])
        self.code_lbl.setText(code)
        self._refresh_hist()

    def _refresh_hist(self):
        while self.hist_box.count():
            w = self.hist_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        for c in reversed(self.model.invite_list()[-6:]):     # 최근 6개
            row = QLabel(("❌ " if c["used"] else "✅ ") + c["code"]
                         + (f"  — 사용됨({c['used_by']})" if c["used"] else "  — 사용 가능"))
            row.setStyleSheet("background:white;border:1.5px solid #e4e7ec;"
                              "border-radius:9px;padding:9px;font-size:13px;"
                              + ("color:#9ca3af;" if c["used"] else "color:#166534;"))
            self.hist_box.addWidget(row)


class NotiDialog(QDialog):
    """부족 알림 목록 — 수량 < 최소수량 자동 수집 [2차]"""

    def __init__(self, stock: StockModel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("알림 — 재고 부족")
        self.resize(360, 300)
        lay = QVBoxLayout(self)
        lows = stock.low_items()
        if not lows:
            lay.addWidget(QLabel("부족 품목이 없습니다. ✅"))
        for i in lows:
            card = QLabel(f"⚠ <b>{i['품목명']}</b> 재고 부족<br>"
                          f"현재 {i['수량']}개 / 최소 {i['최소수량']}개 · "
                          f"{i['창고']} {i['구역']}")
            card.setStyleSheet("background:white;border:1.5px solid #e4e7ec;"
                               "border-left:4px solid #ef4444;border-radius:9px;"
                               "padding:10px;font-size:13px;")
            lay.addWidget(card)
        lay.addStretch()


class MainView(QWidget):
    """메인 — 2행 상단바(시계·벨뱃지·이름·등급) + 기능 탭"""

    def __init__(self, member: dict, on_logout):
        super().__init__()
        self.member = member
        self.on_logout = on_logout
        self.stock = StockModel()
        self.inout = InoutModel()
        self.member_model = MemberModel()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── 2행 상단바 (목업 topbar-wrap) ──
        bar = QFrame()
        bar.setStyleSheet("background:#1d4ed8;")
        bl = QVBoxLayout(bar)
        bl.setContentsMargins(14, 8, 14, 8)

        row1 = QHBoxLayout()                       # 행1: 시계 | 벨+뱃지
        self.clock = QLabel(QTime.currentTime().toString("HH:mm"))
        self.clock.setStyleSheet("color:white;font-weight:700;font-size:14px;")
        row1.addWidget(self.clock)
        row1.addStretch()
        self.bell = QPushButton("🔔")
        self.bell.setStyleSheet("color:white;background:transparent;border:none;"
                                "font-size:16px;")
        self.bell.clicked.connect(lambda: NotiDialog(self.stock, self).exec())
        row1.addWidget(self.bell)
        bl.addLayout(row1)

        row2 = QHBoxLayout()                       # 행2: 이름 + 등급 pill + 로그아웃
        row2.addStretch()
        nm = QLabel(self.member["name"])
        nm.setStyleSheet("color:white;font-weight:700;font-size:13px;")
        pill = QLabel(f"{self.member['role']} · {ROLE_KR[self.member['role']]}")
        pill.setStyleSheet("font-size:10px;font-weight:700;padding:2px 8px;"
                           "border-radius:10px;" + ROLE_STYLE[self.member["role"]])
        out = QPushButton("로그아웃")
        out.setStyleSheet("font-size:11px;color:white;border:none;"
                          "background:rgba(255,255,255,.2);border-radius:6px;padding:3px 9px;")
        out.clicked.connect(self.on_logout)
        row2.addWidget(nm); row2.addWidget(pill); row2.addWidget(out)
        bl.addLayout(row2)
        lay.addWidget(bar)

        # 시계 10초마다 갱신 (QTimer → Signal → 슬롯)
        t = QTimer(self)
        t.timeout.connect(lambda: self.clock.setText(
            QTime.currentTime().toString("HH:mm")))
        t.start(10000)

        # ── 기능 탭 — 파트2~5 화면을 여기에 조립 ──
        tabs = QTabWidget()
        self.warehouse = WarehouseView(self.stock)
        tabs.addTab(self.warehouse, "창고")
        tabs.addTab(InoutView(self.inout, self.member, self._on_stock_change), "입출고")
        tabs.addTab(ChatView(self.member), "채팅")
        tabs.addTab(BoardView(self.member), "게시판")
        if self.member["role"] == "A":             # 초대코드 탭은 admin만
            tabs.addTab(InviteView(self.member_model, self.member), "초대코드")
        lay.addWidget(tabs)

        self._update_bell()

    def _on_stock_change(self):
        """입출고 발생 → 배치도의 부족 표시 + 벨 뱃지 갱신"""
        self.warehouse.refresh()
        self._update_bell()

    def _update_bell(self):
        n = len(self.stock.low_items())            # 부족 품목 수 = 뱃지 숫자
        self.bell.setText(f"🔔 {n}" if n else "🔔")


class TabWindow(QStackedWidget):
    """최상위 창 — 0:인증(QTabWidget) ↔ 1:메인"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TeamStock — 현장 재고관리 + 직원 소통")
        self.resize(460, 760)                      # 목업 폰 비율에 맞춤
        self.model = MemberModel()

        # 인증 화면: 문서 명세대로 QTabWidget 탭 분리
        self.auth = QTabWidget()
        self.auth.addTab(LoginView(self.model, self._on_login), "로그인")
        self.auth.addTab(SignupView(self.model,
                                    lambda: self.auth.setCurrentIndex(0)), "회원가입")
        self.addWidget(self.auth)                  # index 0
        self.setCurrentIndex(0)

    def _on_login(self, member: dict):
        # 이전 메인뷰가 있으면 제거 (재로그인 시 새 권한으로 다시 구성)
        while self.count() > 1:
            w = self.widget(1)
            self.removeWidget(w)
            w.deleteLater()
        self.addWidget(MainView(member, self._on_logout))   # index 1
        self.setCurrentIndex(1)

    def _on_logout(self):
        self.setCurrentIndex(0)


# ── 단독 테스트 (학습용) — main.py 없이 창 전체 띄워보기 ─────
# if __name__ == "__main__":
#     import sys
#     from PySide6.QtWidgets import QApplication
#     app = QApplication(sys.argv)
#     win = TabWindow(); win.show()
#     sys.exit(app.exec())
