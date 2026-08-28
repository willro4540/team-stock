"""
board_screen.py — 게시판 화면·글 작성·상태 관리 (파트5)
────────────────────────────────────────
· 처리상태 3단계 흐름이 이 파트의 핵심:
    미확인(빨강) → 확인(노랑) → 처리완료(초록)
    상태 전환 버튼은 admin만 — 권한 분기
· 필터 탭: 전체 / 미확인 / 처리완료  (리스트 컴프리헨션 한 줄 필터)
"""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QDialog, QListWidget, QListWidgetItem, QMessageBox,
)
from PySide6.QtCore import Qt

from board_save import BoardStorage

STATUS_FLOW = ["미확인", "확인", "처리완료"]           # 순서가 곧 흐름
STATUS_COLOR = {"미확인": "#b91c1c", "확인": "#92400e", "처리완료": "#166534"}


class BoardView(QWidget):
    def __init__(self, member: dict):
        super().__init__()
        self.member = member
        self.storage = BoardStorage()
        self.filter = "전체"
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)

        # ── 필터 탭 ──
        tabs = QHBoxLayout()
        self.tab_btns = {}
        for f in ("전체", "미확인", "처리완료"):
            b = QPushButton(f)
            b.clicked.connect(lambda _, x=f: self._set_filter(x))
            tabs.addWidget(b)
            self.tab_btns[f] = b
        lay.addLayout(tabs)

        # ── 글 목록 ──
        self.post_list = QListWidget()
        self.post_list.itemClicked.connect(self._open_detail)
        lay.addWidget(self.post_list, 1)

        write_btn = QPushButton("+ 글쓰기 (등록 시 status: 미확인)")
        write_btn.setStyleSheet("background:#1d4ed8;color:white;min-height:42px;"
                                "border-radius:9px;font-weight:700;")
        write_btn.clicked.connect(self._write)
        lay.addWidget(write_btn)

        self._set_filter("전체")

    def _set_filter(self, f):
        self.filter = f
        for name, b in self.tab_btns.items():
            b.setStyleSheet("min-height:34px;font-weight:700;border-radius:8px;"
                            + ("background:#1d4ed8;color:white;" if name == f
                               else "background:white;border:1.5px solid #e4e7ec;color:#6b7280;"))
        self.refresh()

    def refresh(self):
        self.post_list.clear()
        posts = self.storage.load()["posts"]
        # 필터: "전체"가 아니면 status 일치 글만 (리스트 컴프리헨션)
        if self.filter != "전체":
            posts = [p for p in posts if p["status"] == self.filter]
        for p in sorted(posts, key=lambda x: x["id"], reverse=True):   # 최신순
            item = QListWidgetItem(f"[{p['status']}] {p['title']}\n"
                                   f"   {p['author']} · {p['created_at']}")
            item.setData(Qt.UserRole, p["id"])       # 항목에 글 id 숨겨두기
            self.post_list.addItem(item)

    # ── 글쓰기 — id 자동 증가, status는 무조건 "미확인"으로 시작 ──
    def _write(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("글쓰기")
        dlg.resize(380, 320)
        lay = QVBoxLayout(dlg)
        title = QLineEdit(); title.setPlaceholderText("제목을 입력하세요")
        content = QTextEdit()
        content.setPlaceholderText("내용을 입력하세요...\n(담당자 오프라인 시 문의 남기기 용도)")
        submit = QPushButton("등록")
        submit.setStyleSheet("background:#1d4ed8;color:white;min-height:38px;font-weight:700;")
        lay.addWidget(title); lay.addWidget(content); lay.addWidget(submit)

        def _save():
            if not title.text().strip():
                QMessageBox.warning(dlg, "안내", "제목을 입력하세요.")
                return
            data = self.storage.load()
            # id 자동 증가: 기존 최대 id + 1
            new_id = max((p["id"] for p in data["posts"]), default=0) + 1
            data["posts"].append({
                "id": new_id, "author": self.member["name"],
                "title": title.text().strip(), "content": content.toPlainText(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "미확인",
            })
            self.storage.save(data)
            dlg.accept()
            self.refresh()
        submit.clicked.connect(_save)
        dlg.exec()

    # ── 상세 보기 + 상태 전환 (admin만) ──
    def _open_detail(self, item: QListWidgetItem):
        post_id = item.data(Qt.UserRole)
        data = self.storage.load()
        p = next((x for x in data["posts"] if x["id"] == post_id), None)
        if p is None:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("게시글 상세")
        dlg.resize(380, 340)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(f"<h3>{p['title']}</h3>"))
        lay.addWidget(QLabel(f"{p['author']} · {p['created_at']}"))
        body = QLabel(p["content"] or "(내용 없음)")
        body.setWordWrap(True)
        lay.addWidget(body, 1)

        flow = QLabel("  →  ".join(
            f"<span style='color:{STATUS_COLOR[s]};font-weight:"
            f"{'800' if s == p['status'] else '400'};'>{s}</span>"
            for s in STATUS_FLOW))
        flow.setAlignment(Qt.AlignCenter)
        lay.addWidget(flow)

        # 상태 전환은 admin 권한 — 다음 단계가 있을 때만 버튼 생성
        idx = STATUS_FLOW.index(p["status"])
        if self.member["role"] == "A" and idx < len(STATUS_FLOW) - 1:
            nxt = STATUS_FLOW[idx + 1]
            btn = QPushButton(f"상태 변경: {p['status']} → {nxt}")
            btn.setStyleSheet("background:#16a34a;color:white;min-height:38px;font-weight:700;")
            def _advance():
                p["status"] = nxt                # 다음 단계로 한 칸 전진
                self.storage.save(data)
                dlg.accept()
                self.refresh()
            btn.clicked.connect(_advance)
            lay.addWidget(btn)
        dlg.exec()


# ── 단독 테스트 (학습용) — admin으로 상태 전환까지 해보기 ─────
# if __name__ == "__main__":
#     import sys
#     from PySide6.QtWidgets import QApplication
#     app = QApplication(sys.argv)
#     w = BoardView({"name": "관리자", "role": "A"})
#     w.resize(420, 560); w.show()
#     sys.exit(app.exec())
