"""
stock_inout.py — 입출고 화면 (파트3)
────────────────────────────────────────
· 권한 분기 (표준참고문서 5.2):
    C(employee) → 조회 + 출고요청만  (입력 위젯 자체를 만들지 않음)
    B(stocker)  → 일반품목 입출고
    A(admin)    → 전체 + 특수브라켓 + 입고 승인
· 특수브라켓 = 실물 사진 4유형(QPixmap) 대조 선택 → 검수 3항목 필수
· 출고 확정 전 QDialog 수량 확인창 — exec() 결과가 Accepted일 때만 차감
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QListWidget, QSpinBox, QLineEdit, QDialog, QCheckBox,
    QTabWidget, QMessageBox, QListWidgetItem, QTextEdit, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from inout_logic import InoutModel
from camera import take_photo

ASSETS = Path(__file__).parent / "assets"

# 특수브라켓 4유형 — (품목명, 사진 파일)  ★ 목업 v16의 2x2 사진 그리드와 동일
SPECIAL_TYPES = [
    ("특수브라켓 A형", "bracket_a.jpg", "플레이트"),
    ("특수브라켓 B형", "bracket_b.jpg", "커버"),
    ("특수브라켓 C형", "bracket_c.jpg", "홀더"),
    ("특수브라켓 D형", "bracket_d.jpg", "마운트"),
]

INSPECT_ITEMS = ["외관 손상 여부 확인", "규격 일치 확인", "수량 일치 확인"]


class OutConfirmDialog(QDialog):
    """출고 수량 확인창 — 문서 명세 'QDialog' 그대로"""

    def __init__(self, item, qty, member, parent=None):
        super().__init__(parent)
        self.setWindowTitle("출고 확인")
        lay = QVBoxLayout(self)
        after = item["수량"] - qty
        low = after < item["최소수량"]
        rows = [("품목", item["품목명"]), ("출고 수량", f"{qty}개"),
                ("출고 후 재고", f"{after}개" + (" ⚠ 부족" if low else "")),
                ("담당자", member["name"])]
        for k, v in rows:
            r = QHBoxLayout()
            r.addWidget(QLabel(k))
            r.addStretch()
            vl = QLabel(v)
            if "⚠" in v:
                vl.setStyleSheet("color:#dc2626;font-weight:700;")
            r.addWidget(vl)
            lay.addLayout(r)
        btns = QHBoxLayout()
        cancel = QPushButton("취소")
        ok = QPushButton("출고 확정")
        ok.setStyleSheet("background:#1d4ed8;color:white;font-weight:700;min-height:36px;")
        cancel.clicked.connect(self.reject)   # reject() → exec()가 Rejected 반환
        ok.clicked.connect(self.accept)       # accept() → Accepted 반환
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)


class SpecialCard(QFrame):
    """특수브라켓 사진 카드 — 클릭으로 유형 선택 (사진과 실물 대조가 목적)"""

    def __init__(self, name, img, kind, on_click):
        super().__init__()
        self.name, self.on_click = name, on_click
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        pic = QLabel()
        pm = QPixmap(str(ASSETS / img))
        # scaledToWidth: 원본 비율 유지하며 가로 130px로 축소
        pic.setPixmap(pm.scaledToWidth(130, Qt.SmoothTransformation))
        pic.setAlignment(Qt.AlignCenter)
        cap = QLabel(f"{name.split()[-1]} · {kind}")
        cap.setAlignment(Qt.AlignCenter)
        cap.setStyleSheet("font-size:12px;font-weight:700;color:#92400e;border:none;")
        lay.addWidget(pic)
        lay.addWidget(cap)
        self.set_selected(False)

    def set_selected(self, sel: bool):
        border = "#1d4ed8" if sel else "#fbbf24"
        self.setStyleSheet(f"QFrame{{background:#fffbeb;border:2px solid {border};"
                           f"border-radius:10px;}} QLabel{{border:none;}}")

    def mousePressEvent(self, e):
        self.on_click(self.name)


class InoutForm(QWidget):
    """입고/출고 입력 폼 — B·A 등급 전용"""

    def __init__(self, model: InoutModel, member: dict, on_change):
        super().__init__()
        self.model, self.member, self.on_change = model, member, on_change
        self.mode = "출고"
        self.selected_special = None
        self.photo_path, self.gps = "", ""
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)

        # ── 입고/출고 토글 (목업 big2 버튼) ──
        row = QHBoxLayout()
        self.mode_btns = {}
        for m in ("입고", "출고"):
            b = QPushButton(("📥 " if m == "입고" else "📤 ") + m)
            b.clicked.connect(lambda _, x=m: self._set_mode(x))
            row.addWidget(b)
            self.mode_btns[m] = b
        lay.addLayout(row)

        # ── 창고/구역 선택 ──
        sel = QHBoxLayout()
        self.wh_combo = QComboBox(); self.wh_combo.addItems(["창고1", "창고2"])
        self.zone_combo = QComboBox(); self.zone_combo.addItems(["A구역", "B구역", "C구역", "D구역"])
        self.wh_combo.currentTextChanged.connect(self._reload_items)
        self.zone_combo.currentTextChanged.connect(self._reload_items)
        sel.addWidget(self.wh_combo); sel.addWidget(self.zone_combo)
        lay.addLayout(sel)

        # ── 품목 목록 ──
        self.item_list = QListWidget()
        self.item_list.setMaximumHeight(110)
        self.item_list.itemClicked.connect(self._on_item_pick)
        lay.addWidget(self.item_list)

        # ── 특수브라켓 영역 (admin만 보임) ──
        self.special_box = QWidget()
        sp_lay = QVBoxLayout(self.special_box)
        sp_lay.setContentsMargins(0, 0, 0, 0)
        warn = QLabel("⚠ 특수브라켓 유형 선택 — 사진과 실물 대조")
        warn.setStyleSheet("font-size:12px;font-weight:700;color:#92400e;")
        sp_lay.addWidget(warn)
        grid = QGridLayout()
        self.sp_cards = {}
        for i, (name, img, kind) in enumerate(SPECIAL_TYPES):
            card = SpecialCard(name, img, kind, self._on_special_pick)
            grid.addWidget(card, i // 2, i % 2)        # 2x2
            self.sp_cards[name] = card
        sp_lay.addLayout(grid)
        # 검수 체크리스트 — 3개 전부 체크해야 등록 가능
        self.checks = [QCheckBox(t) for t in INSPECT_ITEMS]
        for c in self.checks:
            sp_lay.addWidget(c)
        lay.addWidget(self.special_box)
        self.special_box.setVisible(self.member["role"] == "A")

        # ── 수량 / 메모 / 촬영 ──
        qrow = QHBoxLayout()
        qrow.addWidget(QLabel("수량"))
        self.qty = QSpinBox(); self.qty.setRange(1, 99999)
        qrow.addWidget(self.qty, 1)
        lay.addLayout(qrow)
        self.memo = QLineEdit(); self.memo.setPlaceholderText("용도/메모 (예: B동 라인용)")
        lay.addWidget(self.memo)

        cam = QPushButton("📷 사진 촬영하기")
        cam.setStyleSheet("background:#1a202c;color:white;min-height:40px;"
                          "border-radius:9px;font-weight:700;")
        cam.clicked.connect(self._on_photo)
        lay.addWidget(cam)
        self.photo_lbl = QLabel("사진 없음 (촬영 실패해도 등록 가능 — 예외처리)")
        self.photo_lbl.setStyleSheet("font-size:11px;color:#6b7280;")
        lay.addWidget(self.photo_lbl)

        self.submit = QPushButton("✓ 등록")
        self.submit.setStyleSheet("background:#16a34a;color:white;min-height:44px;"
                                  "border-radius:9px;font-size:15px;font-weight:700;")
        self.submit.clicked.connect(self._on_submit)
        lay.addWidget(self.submit)
        lay.addStretch()

        self._set_mode("출고")
        self._reload_items()

    def _set_mode(self, mode):
        self.mode = mode
        for m, b in self.mode_btns.items():
            on = (m == mode)
            color = ("#f0fdf4;border:2px solid #86efac;color:#166534" if m == "입고"
                     else "#eff6ff;border:2px solid #1d4ed8;color:#1d4ed8")
            b.setStyleSheet(f"min-height:46px;font-size:15px;font-weight:800;border-radius:11px;"
                            + (f"background:{color};" if on
                               else "background:white;border:2px solid #e4e7ec;color:#6b7280;"))
        self.submit.setText("✓ 등록 (관리자 승인 대기)" if mode == "입고" else "✓ 출고 진행")

    def _reload_items(self):
        self.item_list.clear()
        wh, zone = self.wh_combo.currentText(), self.zone_combo.currentText()
        for it in self.model.stock.zone_items(wh, zone):
            special = self.model.is_special(it["품목명"])
            # B등급은 특수브라켓을 목록에서 제외 — 권한 분기의 실제 코드
            if special and self.member["role"] != "A":
                continue
            low = " ⚠부족" if self.model.stock.is_low(it) else ""
            QListWidgetItem(f"{it['품목명']}  ({it['수량']}개{low})", self.item_list)

    def _current_item_name(self):
        if self.selected_special:
            return self.selected_special
        cur = self.item_list.currentItem()
        return cur.text().split("  (")[0] if cur else None

    def _on_item_pick(self, _):
        name = self.item_list.currentItem().text().split("  (")[0]
        if self.model.is_special(name):
            self._on_special_pick(name)     # 목록에서 골라도 사진 카드와 동기화
        else:
            self.selected_special = None
            for c in self.sp_cards.values():
                c.set_selected(False)

    def _on_special_pick(self, name):
        self.selected_special = name
        for n, c in self.sp_cards.items():
            c.set_selected(n == name)

    def _on_photo(self):
        self.photo_path, self.gps = take_photo()
        if self.photo_path:
            self.photo_lbl.setText(f"📍 GPS 기록됨 {self.gps} · {Path(self.photo_path).name}")
            self.photo_lbl.setStyleSheet("font-size:11px;color:#1e40af;font-weight:600;")
        else:
            self.photo_lbl.setText("촬영 실패/카메라 없음 — 사진 없이 등록 진행 가능")

    def _on_submit(self):
        name = self._current_item_name()
        if not name:
            QMessageBox.warning(self, "안내", "품목을 선택해주세요.")
            return
        special = self.model.is_special(name)

        # ── 특수브라켓 안전장치: 검수 3항목 모두 체크해야 통과 ──
        if special and not all(c.isChecked() for c in self.checks):
            QMessageBox.warning(self, "검수 필요",
                                "특수브라켓은 검수 체크리스트 3항목을 모두 완료해야 합니다.")
            return

        wh, zone = self.wh_combo.currentText(), self.zone_combo.currentText()
        qty = self.qty.value()

        if self.mode == "출고":
            data = self.model.storage.load()
            item = self.model._find(data, wh, zone, name)
            if item is None:
                QMessageBox.warning(self, "안내", "해당 구역에 품목이 없습니다.")
                return
            # ★ QDialog 확인창 — Accepted(확정)일 때만 실제 차감
            dlg = OutConfirmDialog(item, qty, self.member, self)
            if dlg.exec() != QDialog.Accepted:
                return
            ok, msg = self.model.stock_out(self.member, wh, zone, name, qty,
                                           self.photo_path, self.gps, self.memo.text())
        else:
            ok, msg = self.model.stock_in_request(self.member, wh, zone, name, qty,
                                                  self.photo_path, self.gps,
                                                  self.memo.text(), inspected=special)

        (QMessageBox.information if ok else QMessageBox.warning)(self, "결과", msg)
        if ok:
            for c in self.checks:
                c.setChecked(False)
            self.photo_path, self.gps = "", ""
            self.photo_lbl.setText("사진 없음")
            self._reload_items()
            self.on_change()                # 배치도·알림 갱신 신호


class ApproveTab(QWidget):
    """입고 승인 대기 (admin) — 승인 시점에만 재고 반영"""

    def __init__(self, model, member, on_change):
        super().__init__()
        self.model, self.member, self.on_change = model, member, on_change
        self.lay = QVBoxLayout(self)
        self.refresh()

    def refresh(self):
        while self.lay.count():
            w = self.lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        pend = self.model.pending_list()
        if not pend:
            lbl = QLabel("승인 대기 건이 없습니다.")
            lbl.setAlignment(Qt.AlignCenter)
            self.lay.addWidget(lbl)
        for p in pend:
            card = QFrame()
            card.setStyleSheet("QFrame{background:white;border:1.5px solid #e4e7ec;"
                               "border-radius:10px;} QLabel{border:none;}")
            cl = QVBoxLayout(card)
            insp = " · 검수완료" if p["검수완료"] else ""
            photo = " · 📷사진" if p["사진"] else ""
            cl.addWidget(QLabel(f"<b>{p['품목']} +{p['수량']}개</b>  "
                                f"<span style='color:#92400e;'>승인 대기</span>"))
            cl.addWidget(QLabel(f"{p['창고']} {p['구역']} · 등록:{p['직원명']} · "
                                f"{p['일시']}{insp}{photo}"))
            btns = QHBoxLayout()
            ok_b = QPushButton("승인 → 재고 반영")
            ok_b.setStyleSheet("background:#16a34a;color:white;font-weight:700;min-height:32px;")
            rj_b = QPushButton("반려")
            rj_b.setStyleSheet("background:#dc2626;color:white;font-weight:700;min-height:32px;")
            pid = p["pending_id"]
            ok_b.clicked.connect(lambda _, x=pid: self._do(self.model.approve, self.member, x))
            rj_b.clicked.connect(lambda _, x=pid: self._do(self.model.reject, x))
            btns.addWidget(ok_b); btns.addWidget(rj_b)
            cl.addLayout(btns)
            self.lay.addWidget(card)
        self.lay.addStretch()

    def _do(self, fn, *args):
        ok, msg = fn(*args)
        QMessageBox.information(self, "결과", msg)
        self.refresh()
        self.on_change()


class RecordTab(QWidget):
    """입출고 기록 + 반납[3차] + 특수브라켓 잔여 사유서[3차]"""

    def __init__(self, model, member, on_change):
        super().__init__()
        self.model, self.member, self.on_change = model, member, on_change
        self.lay = QVBoxLayout(self)
        self.refresh()

    def refresh(self):
        while self.lay.count():
            w = self.lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        recs = self.model.records()[:12]              # 최근 12건만 표시
        if not recs:
            lbl = QLabel("기록이 없습니다.")
            lbl.setAlignment(Qt.AlignCenter)
            self.lay.addWidget(lbl)
        for r in recs:
            card = QFrame()
            card.setStyleSheet("QFrame{background:white;border:1.5px solid #e4e7ec;"
                               "border-radius:10px;} QLabel{border:none;}")
            cl = QVBoxLayout(card)
            sign = {"출고": "−", "입고": "+", "반납": "+"}[r["종류"]]
            state = "반납 완료" if r["반납됨"] else r["종류"]
            cl.addWidget(QLabel(f"<b>{r['품목']} {sign}{r['수량']}개</b>  [{state}]"))
            gps = f" · 📍{r['GPS']}" if r["GPS"] else ""
            cl.addWidget(QLabel(f"{r['직원명']} · {r['일시']} · {r['창고']} {r['구역']}{gps}"))
            btns = QHBoxLayout()
            # 반납 버튼: 출고건 & 미반납 & B/A 권한
            if (r["종류"] == "출고" and not r["반납됨"]
                    and self.member["role"] in ("A", "B")):
                rb = QPushButton("↩ 반납 (재고 재반영)")
                rb.clicked.connect(lambda _, x=r["record_id"]: self._return(x))
                btns.addWidget(rb)
            # 사유서 버튼: 특수브라켓 출고건 [3차 기능]
            if r["종류"] == "출고" and self.model.is_special(r["품목"]):
                sb = QPushButton("📝 잔여 사유서")
                sb.clicked.connect(lambda _, x=r: self._report(x))
                btns.addWidget(sb)
            if btns.count():
                cl.addLayout(btns)
            self.lay.addWidget(card)
        self.lay.addStretch()

    def _return(self, record_id):
        ok, msg = self.model.return_item(self.member, record_id)
        QMessageBox.information(self, "결과", msg)
        self.refresh()
        self.on_change()

    def _report(self, rec):
        # 잔여 사유서 — 간단한 QDialog + QTextEdit (문서상 3차 기능)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{rec['품목']} 잔여 사유서")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(f"출고 {rec['수량']}개 중 잔여 발생 시 사유 작성 → 관리자 전송"))
        text = QTextEdit()
        text.setPlaceholderText("예: 현장 설계 변경으로 3개 미사용")
        lay.addWidget(text)
        send = QPushButton("사유서 관리자 전송")
        send.setStyleSheet("background:#d97706;color:white;font-weight:700;min-height:36px;")
        def _send():
            QMessageBox.information(dlg, "전송 완료",
                                    "사유서가 기록되었습니다. (게시판/관리자 알림 연동은 확장 지점)")
            dlg.accept()
        send.clicked.connect(_send)
        lay.addWidget(send)
        dlg.exec()


class InoutView(QWidget):
    """파트3 메인 — 권한별로 다른 화면 구성"""

    def __init__(self, model: InoutModel, member: dict, on_change=lambda: None):
        super().__init__()
        lay = QVBoxLayout(self)
        role = member["role"]

        if role == "C":
            # ── C등급: 조회 전용 + 출고요청 (입력 위젯을 아예 안 만듦 = 권한 분기) ──
            info = QLabel("C등급(일반직원)은 재고 조회와 출고 요청만 가능합니다.\n"
                          "입출고 입력은 B(자재담당)/A(관리자) 권한입니다.")
            info.setStyleSheet("background:#eff6ff;border:1.5px solid #bfdbfe;"
                               "border-radius:9px;padding:10px;color:#1e40af;")
            lay.addWidget(info)
            req = QPushButton("출고 요청하기 (채팅으로 담당자에게 전달)")
            req.setStyleSheet("min-height:44px;border:2px solid #1d4ed8;color:#1d4ed8;"
                              "border-radius:9px;font-weight:700;background:white;")
            req.clicked.connect(lambda: QMessageBox.information(
                self, "출고 요청", "채팅 탭에서 담당자에게 요청 메시지를 보내세요."))
            lay.addWidget(req)
            self.record_tab = RecordTab(model, member, on_change)
            lay.addWidget(self.record_tab)
            return

        tabs = QTabWidget()
        self.form = InoutForm(model, member, on_change)
        tabs.addTab(self.form, "입출고")
        if role == "A":                                # 승인 탭은 admin만
            self.approve_tab = ApproveTab(model, member, on_change)
            tabs.addTab(self.approve_tab, "입고 승인")
            tabs.currentChanged.connect(
                lambda _: self.approve_tab.refresh())
        self.record_tab = RecordTab(model, member, on_change)
        tabs.addTab(self.record_tab, "기록·반납")
        tabs.currentChanged.connect(lambda _: self.record_tab.refresh())
        lay.addWidget(tabs)


# ── 단독 테스트 (학습용) — admin 계정으로 이 화면만 띄워보기 ─────
# if __name__ == "__main__":
#     import sys
#     from PySide6.QtWidgets import QApplication
#     app = QApplication(sys.argv)
#     me = {"name": "관리자", "role": "A"}
#     w = InoutView(InoutModel(), me)
#     w.resize(430, 700); w.show()
#     sys.exit(app.exec())
