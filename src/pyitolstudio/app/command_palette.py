"""Command palette (⌘K) — design book §5.1/§6.

A light ``QDialog`` holding a ``QLineEdit`` over a ``QListView``.  It indexes
three sources so a heavy user never has to hunt through the UI:

* **annotation units** — jump straight to one in the left rail;
* **template types** — open the wizard already on that type (31 types make a
  browsable grid a slow way to reach the one you want);
* **commands** — the same actions the toolbar exposes, by name.

The dialog owns no application state: the caller hands it a list of entries
whose ``run`` callables are already bound.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QEasingCurve, QModelIndex, QPropertyAnimation, QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
)

from ..i18n import tr
from ..icons import icon, icon_pixmap
from ..theme import FONT_SIZE, FONT_SIZE_CAPTION, FONT_SIZE_MONO, RADIUS_S, SPACE_2, SPACE_3
from ..theme_mode import theme_color, theme_qcolor

KIND_UNIT = "unit"
KIND_TYPE = "type"
KIND_COMMAND = "command"

ENTRY_KIND_ROLE = int(Qt.ItemDataRole.UserRole) + 1
ENTRY_HINT_ROLE = int(Qt.ItemDataRole.UserRole) + 2
ENTRY_SEARCH_ROLE = int(Qt.ItemDataRole.UserRole) + 3
ENTRY_ICON_ROLE = int(Qt.ItemDataRole.UserRole) + 4

ROW_HEIGHT = 32


@dataclass(frozen=True)
class PaletteEntry:
    """One reachable thing in the palette."""

    kind: str
    title: str
    hint: str
    icon_name: str
    run: Callable[[], None]
    extra_search: str = ""

    @property
    def searchable(self) -> str:
        return f"{self.title} {self.hint} {self.extra_search}".lower()


class PaletteRowDelegate(QStyledItemDelegate):
    """Paints icon + title on the left, kind and shortcut hint on the right."""

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:  # noqa: N802
        kind = str(index.data(ENTRY_KIND_ROLE) or "")
        hint = str(index.data(ENTRY_HINT_ROLE) or "")
        title = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect
        if selected:
            body = QPainterPath()
            body.addRoundedRect(rect.adjusted(SPACE_2, 1, -SPACE_2, -1), RADIUS_S, RADIUS_S)
            painter.fillPath(body, theme_qcolor("accent_soft"))
            bar = QPainterPath()
            bar.addRoundedRect(
                QRect(rect.left() + SPACE_2, rect.top() + 7, 2, rect.height() - 14), 1, 1
            )
            painter.fillPath(bar, theme_qcolor("accent"))

        glyph = icon_pixmap(
            str(index.data(ENTRY_ICON_ROLE) or "circle-dot"),
            15,
            theme_color("accent" if selected else "text_dim"),
        )
        painter.drawPixmap(rect.left() + SPACE_3 + SPACE_2, rect.center().y() - 7, glyph)

        kind_label = _kind_label(kind)  # computed once per paint (UI P2-6)
        right_font = QFont()
        right_font.setPixelSize(FONT_SIZE_CAPTION)
        right_metrics = QFontMetrics(right_font)
        right_width = right_metrics.horizontalAdvance(hint) + SPACE_3 * 2
        kind_width = right_metrics.horizontalAdvance(kind_label) + SPACE_3 * 2

        title_rect = QRect(
            rect.left() + SPACE_3 + SPACE_2 + 15 + SPACE_3,
            rect.top(),
            max(rect.width() - 15 - kind_width - right_width - SPACE_3 * 6, 0),
            rect.height(),
        )
        font = painter.font()
        font.setPixelSize(FONT_SIZE_MONO if kind == KIND_UNIT else FONT_SIZE)
        painter.setFont(font)
        painter.setPen(theme_qcolor("text"))
        painter.drawText(
            title_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            QFontMetrics(font).elidedText(title, Qt.TextElideMode.ElideRight, title_rect.width()),
        )

        painter.setFont(right_font)
        painter.setPen(theme_qcolor("text_tertiary"))
        kind_rect = QRect(
            title_rect.right() + SPACE_3, rect.top(), kind_width, rect.height()
        )
        painter.drawText(
            kind_rect,
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            kind_label,
        )
        if hint:
            hint_rect = QRect(
                rect.right() - SPACE_3 - right_width, rect.top(), right_width, rect.height()
            )
            painter.drawText(
                hint_rect,
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                hint,
            )
        painter.restore()

    def sizeHint(self, option, index: QModelIndex) -> QSize:  # noqa: N802
        return QSize(0, ROW_HEIGHT)


def _kind_label(kind: str) -> str:
    return {
        KIND_UNIT: tr("cmd.kind_unit"),
        KIND_TYPE: tr("cmd.kind_type"),
        KIND_COMMAND: tr("cmd.kind_command"),
    }.get(kind, "")


class CommandPalette(QDialog):
    """⌘K: type, arrow, Enter."""

    def __init__(self, entries: list[PaletteEntry], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("commandPalette")
        self.setWindowTitle(tr("cmd.title"))
        self.setModal(True)
        self.resize(560, 420)
        self._entries: list[PaletteEntry] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)

        self.search = QLineEdit()
        self.search.setObjectName("commandSearch")
        self.search.setPlaceholderText(tr("cmd.placeholder"))
        self.search.setClearButtonEnabled(True)
        self.search.addAction(
            icon("search", 13, theme_color("text_tertiary")), QLineEdit.ActionPosition.LeadingPosition
        )
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setObjectName("commandList")
        self.list.setItemDelegate(PaletteRowDelegate(self.list))
        self.list.setUniformItemSizes(True)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.list, 1)

        self.search.textChanged.connect(self._refill)
        self.search.returnPressed.connect(self.activate_current)
        self.list.itemActivated.connect(lambda _item: self.activate_current())

        self.set_entries(entries)

    # -- population ------------------------------------------------------
    def set_entries(self, entries: list[PaletteEntry]) -> None:
        self._entries = list(entries)
        self.search.clear()
        self._refill("")
        self.search.setFocus()

    def _refill(self, query: str) -> None:
        needle = (query or "").strip().lower()
        self.list.clear()
        for entry in self._entries:
            if needle and needle not in entry.searchable:
                continue
            item = QListWidgetItem(entry.title)
            item.setData(ENTRY_KIND_ROLE, entry.kind)
            item.setData(ENTRY_HINT_ROLE, entry.hint)
            item.setData(ENTRY_SEARCH_ROLE, entry.searchable)
            item.setData(ENTRY_ICON_ROLE, entry.icon_name)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    # -- activation ------------------------------------------------------
    def current_entry(self) -> PaletteEntry | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def activate_current(self) -> None:
        entry = self.current_entry()
        if entry is None:
            return
        self.accept()
        entry.run()

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        # The search field owns the arrow keys while it has focus; forward them
        # to the list so the palette is fully keyboard-driven.
        if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up) and self.list.count():
            row = self.list.currentRow()
            row += 1 if event.key() == Qt.Key.Key_Down else -1
            self.list.setCurrentRow(max(0, min(row, self.list.count() - 1)))
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt API)
        """Fade the palette in over 140 ms (review P2 — modal pop-in)."""
        super().showEvent(event)
        self.setWindowOpacity(0.0)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(140)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        self._fade_anim = anim
        anim.start()
