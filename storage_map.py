"""
storage_map.py — 창고 배치도·구역 클릭·재고 팝업 (파트2)
────────────────────────────────────────
· 문서 명세의 3요소를 전부 구현:
  1) mousePressEvent  → ZoneCell 이 클릭을 직접 감지 (QLabel 배치도 방식의 핵심 개념)
  2) QTableWidget     → 구역 팝업에 품목 표 표시
  3) QLineEdit.textChanged → 실시간 색인 검색
· 선입선출: 표의 첫 행(입고일 가장 오래됨)에 초록 배경 + "◀ 먼저 출고"
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QDialog, QTableWidget, QTableWidgetItem, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from stock_logic import StockModel

ZONE_DESC = {   # 표준참고문서 5.4 창고 구성
    "A구역": "선반 · 브라켓류",
    "B구역": "선반 · 볼트류",
    "C구역": "선반 · 공구",
    "D구역": "바닥 · 안전용품",
}


class ZoneCell(QFrame):
    """배치도의 구역 1칸 — mousePressEvent 오버라이드로 클릭 감지"""

    def __init__(self, zone: str, has_low: bool, on_click):
        super().__init__()
        self.zone = zone
        self.on_click = on_click
        # 부족 품목이 있으면 빨간 톤 (목업 v16 .map-cell.full 과 동일)
        border, bg, fg = (("#fca5a5", "#fff5f5", "#dc2626") if has_low
                          else ("#e4e7ec", "#ffffff", "#1f2937"))
        self.setStyleSheet(f"QFrame{{background:{bg};border:2px solid {border};"
                           f"border-radius:10px;}}")
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        title = QLabel(zone)
        title.setStyleSheet(f"font-size:18px;font-weight:800;color:{fg};border:none;")
        title.setAlignment(Qt.AlignCenter)
        desc = QLabel(ZONE_DESC[zone] + ("\n⚠ 부족 품목 있음" if has_low else ""))
        desc.setStyleSheet("font-size:11px;color:#6b7280;border:none;")
        desc.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)
        lay.addWidget(desc)

    # ★ 문서 명세의 핵심 — 마우스 클릭 이벤트를 위젯이 직접 받음
    def mousePressEvent(self, event):
        self.on_click(self.zone)


class ZoneDialog(QDialog):
    """구역 팝업 — QTableWidget + 실시간 검색 + 선입선출 표시"""

    def __init__(self, model: StockModel, warehouse: str, zone: str, parent=None):
        super().__init__(parent)
        self.model, self.wh, self.zone = model, warehouse, zone
        self.setWindowTitle(f"{warehouse} · {zone} — {ZONE_DESC[zone]}")
        self.resize(430, 380)

        lay = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 품목명 검색 (실시간 색인)")
        self.search.setStyleSheet("min-height:36px;padding-left:10px;font-size:13px;")
        # textChanged: 글자 하나 칠 때마다 시그널 발생 → 즉시 재필터 = 실시간 검색
        self.search.textChanged.connect(self._refresh)
        lay.addWidget(self.search)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["품목", "수량", "입고일", "상태"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 150)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 조회 전용
        lay.addWidget(self.table)

        hint = QLabel("입고일 오름차순 = 선입선출 · 첫 행부터 출고  |  수량<최소수량 → 빨간 표시")
        hint.setStyleSheet("font-size:11px;color:#6b7280;")
        lay.addWidget(hint)

        self._refresh()

    def _refresh(self):
        keyword = self.search.text()
        items = self.model.search(self.wh, self.zone, keyword)
        self.table.setRowCount(len(items))
        for r, it in enumerate(items):
            low = self.model.is_low(it)
            date_txt = it["입고일"] + ("  ◀ 먼저 출고" if r == 0 and not keyword else "")
            cells = [it["품목명"], str(it["수량"]), date_txt,
                     "부족 ⚠" if low else "정상"]
            for c, txt in enumerate(cells):
                cell = QTableWidgetItem(txt)
                if low:                                   # 부족 → 빨간 글씨
                    cell.setForeground(QColor("#dc2626"))
                if r == 0 and not keyword:                # 선입선출 1순위 → 초록 배경
                    cell.setBackground(QColor("#f0fdf4"))
                self.table.setItem(r, c, cell)


class WarehouseView(QWidget):
    """창고1/창고2 전환 탭 + 2x2 구역 그리드"""

    def __init__(self, model: StockModel):
        super().__init__()
        self.model = model
        self.current_wh = "창고1"
        self._build()

    def _build(self):
        self.lay = QVBoxLayout(self)

        # 창고 전환 버튼 2개 (문서: 창고 1·2 각 150m²)
        row = QHBoxLayout()
        self.wh_btns = {}
        for wh in ("창고1", "창고2"):
            b = QPushButton(wh)
            b.setCheckable(True)
            b.clicked.connect(lambda _, w=wh: self._switch(w))
            row.addWidget(b)
            self.wh_btns[wh] = b
        self.lay.addLayout(row)

        self.grid_holder = QWidget()
        self.lay.addWidget(self.grid_holder)
        self.lay.addStretch()

        hint = QLabel("구역 클릭 → 품목 테이블 팝업 (mousePressEvent)")
        hint.setStyleSheet("font-size:11px;color:#6b7280;")
        hint.setAlignment(Qt.AlignCenter)
        self.lay.addWidget(hint)

        self._switch("창고1")

    def _switch(self, wh: str):
        self.current_wh = wh
        for name, b in self.wh_btns.items():
            b.setChecked(name == wh)
            b.setStyleSheet(
                "min-height:38px;font-weight:700;border-radius:8px;"
                + ("background:#1d4ed8;color:white;" if name == wh
                   else "background:white;border:1.5px solid #e4e7ec;color:#6b7280;"))
        self._rebuild_grid()

    def _rebuild_grid(self):
        # 이전 그리드 제거 후 새로 구성 (부족 상태가 바뀔 수 있으므로 매번 다시 그림)
        old = self.grid_holder.layout()
        if old is not None:
            while old.count():
                w = old.takeAt(0).widget()
                if w:
                    w.deleteLater()
        grid = old or QGridLayout(self.grid_holder)
        for idx, zone in enumerate(("A구역", "B구역", "C구역", "D구역")):
            has_low = self.model.zone_has_low(self.current_wh, zone)
            cell = ZoneCell(zone, has_low, self._open_zone)
            cell.setMinimumHeight(110)
            grid.addWidget(cell, idx // 2, idx % 2)      # 2x2 배치

    def _open_zone(self, zone: str):
        ZoneDialog(self.model, self.current_wh, zone, self).exec()

    def refresh(self):
        """입출고 후 배치도의 부족 표시 갱신용 (외부에서 호출)"""
        self._rebuild_grid()


# ── 단독 테스트 (학습용) — 이 화면만 띄워보기 ─────────
# if __name__ == "__main__":
#     import sys
#     from PySide6.QtWidgets import QApplication
#     app = QApplication(sys.argv)
#     w = WarehouseView(StockModel())
#     w.resize(430, 500); w.show()
#     sys.exit(app.exec())
