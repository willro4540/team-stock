"""
chat_screen.py — 채팅 화면 (파트4)
────────────────────────────────────────
· 목업 v16 구성 그대로:
    상단 = 접속자 목록 (녹색 ● 표시, user_list 브로드캐스트 수신 시 갱신)
    중앙 = 전체 채팅 (공지는 노란 강조)
    하단 = 입력 + 전송 / 귓속말 모드 토글
· admin이면 "서버 시작" 버튼 표시 — 관리자 PC가 서버 (계획서 명세)
· 귓속말: 접속자 목록에서 대상 선택 → 그 사람에게만 전송 [2차]
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QTextBrowser, QComboBox, QMessageBox,
)
from PySide6.QtCore import Qt

from client import ChatClient
from server import run_in_background, PORT


class ChatView(QWidget):
    def __init__(self, member: dict):
        super().__init__()
        self.member = member
        self.client = ChatClient()
        self.server = None
        self._build()

        # ── Signal → 슬롯 연결: 수신 스레드의 데이터가 안전하게 UI로 ──
        self.client.message_received.connect(self._on_message)
        self.client.users_updated.connect(self._on_users)
        self.client.disconnected.connect(
            lambda: self.status.setText("연결 끊김 — 다시 연결하세요"))

    def _build(self):
        lay = QVBoxLayout(self)

        # ── 접속 바: 서버 주소 + 연결 (+admin이면 서버 시작) ──
        top = QHBoxLayout()
        self.host_inp = QLineEdit("127.0.0.1")
        self.host_inp.setPlaceholderText("서버 IP (관리자 PC)")
        conn_btn = QPushButton("연결")
        conn_btn.clicked.connect(self._connect)
        top.addWidget(self.host_inp, 1)
        top.addWidget(conn_btn)
        if self.member["role"] == "A":
            sv_btn = QPushButton("서버 시작")
            sv_btn.setToolTip("관리자 PC가 서버 역할 — 같은 LAN의 직원들이 이 PC IP로 접속")
            sv_btn.clicked.connect(self._start_server)
            top.addWidget(sv_btn)
        lay.addLayout(top)

        self.status = QLabel("미접속 — admin은 [서버 시작] 후 [연결]")
        self.status.setStyleSheet("font-size:11px;color:#6b7280;")
        lay.addWidget(self.status)

        # ── 접속자 목록 (녹색 ●) ──
        self.user_list = QListWidget()
        self.user_list.setMaximumHeight(70)
        self.user_list.setFlow(QListWidget.LeftToRight)   # 가로 나열
        lay.addWidget(QLabel("접속자 목록 — user_list 수신 시 자동 갱신"))
        lay.addWidget(self.user_list)

        # ── 채팅 로그 (QTextBrowser: HTML 서식 가능) ──
        self.log = QTextBrowser()
        self.log.setStyleSheet("background:#f0f2f5;border:none;border-radius:9px;"
                               "padding:8px;font-size:13px;")
        lay.addWidget(self.log, 1)

        # ── 전송 바: 모드(전체/공지/귓속말) + 대상 + 입력 ──
        send_row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(["전체", "귓속말"])
        if self.member["role"] == "A":
            self.mode.addItem("공지")               # 공지 발신은 admin만
        self.dm_target = QComboBox()
        self.dm_target.setVisible(False)
        self.mode.currentTextChanged.connect(
            lambda t: self.dm_target.setVisible(t == "귓속말"))
        self.msg_inp = QLineEdit()
        self.msg_inp.setPlaceholderText("메시지 입력...")
        self.msg_inp.returnPressed.connect(self._send)    # 엔터로도 전송
        send_btn = QPushButton("▶")
        send_btn.setFixedWidth(44)
        send_btn.setStyleSheet("background:#1d4ed8;color:white;font-weight:700;"
                               "min-height:36px;border-radius:9px;")
        send_btn.clicked.connect(self._send)
        send_row.addWidget(self.mode)
        send_row.addWidget(self.dm_target)
        send_row.addWidget(self.msg_inp, 1)
        send_row.addWidget(send_btn)
        lay.addLayout(send_row)

    # ── 서버/접속 ──
    def _start_server(self):
        if self.server is None:
            self.server = run_in_background()
            self.status.setText(f"서버 실행 중 (포트 {PORT}) — 이제 [연결]을 누르세요")

    def _connect(self):
        if self.client.connect_server(self.host_inp.text().strip(), PORT,
                                      self.member["name"]):
            self.status.setText(f"접속 완료 — {self.member['name']}")
        else:
            QMessageBox.warning(self, "연결 실패",
                                "서버에 연결할 수 없습니다.\n"
                                "admin: [서버 시작] 먼저 / 직원: 관리자 PC IP 확인")

    # ── 수신 슬롯 (Signal이 메인 스레드에서 호출해줌 — UI 조작 안전) ──
    def _on_users(self, users: list):
        self.user_list.clear()
        for u in users:
            self.user_list.addItem(f"🟢 {u}")       # 목록에 있음 = 접속 중 = 녹색
        # 귓속말 대상 갱신 (본인 제외)
        self.dm_target.clear()
        self.dm_target.addItems([u for u in users if u != self.member["name"]])

    def _on_message(self, msg: dict):
        t, frm, body = msg.get("type"), msg.get("from", "?"), msg.get("msg", "")
        if t == "notice":
            self.log.append(f"<div style='color:#92400e;background:#fffbeb;'>"
                            f"📢 <b>공지</b> — {body} ({frm})</div>")
        elif t == "dm":
            self.log.append(f"<span style='color:#7c3aed;'>🤫 [귓속말] "
                            f"<b>{frm}</b> → {msg.get('to')}: {body}</span>")
        else:
            me = (frm == self.member["name"])
            color = "#1d4ed8" if me else "#1f2937"
            self.log.append(f"<span style='color:{color};'><b>{frm}</b>: {body}</span>")

    # ── 송신 ──
    def _send(self):
        text = self.msg_inp.text().strip()
        if not text:
            return
        if not self.client.sock:
            QMessageBox.warning(self, "안내", "먼저 서버에 연결하세요.")
            return
        mode = self.mode.currentText()
        if mode == "공지":
            self.client.send_notice(text)
        elif mode == "귓속말":
            to = self.dm_target.currentText()
            if not to:
                QMessageBox.warning(self, "안내", "귓속말 대상을 선택하세요.")
                return
            self.client.send_dm(to, text)
        else:
            self.client.send_chat(text)
        self.msg_inp.clear()


# ── 단독 테스트 (학습용) — 창 2개 띄워서 서로 대화해보기 ─────
# if __name__ == "__main__":
#     import sys
#     from PySide6.QtWidgets import QApplication
#     app = QApplication(sys.argv)
#     w1 = ChatView({"name": "관리자", "role": "A"})   # [서버 시작]→[연결]
#     w2 = ChatView({"name": "박담당", "role": "B"})   # [연결]만
#     w1.resize(420, 560); w1.show()
#     w2.resize(420, 560); w2.move(500, 100); w2.show()
#     sys.exit(app.exec())
