"""Data grid for the center pane (FR-3, design book §9.2).

Structure of a row, left to right::

    [ 行号 ] [ 数据列 … ] [ 状态 ]

* the row-number column is read-only, right-aligned, mono, ``text-tertiary``
* data columns come from the IDL (``adapter/form_idl.py``), so a new template
  type still needs zero GUI code; the first (tree-ID) column and every numeric
  column render in the mono face — the design book's "数据可辨" rule
* the status column is drawn as a chip: icon **and** text, so the verdict never
  depends on colour alone
* a row whose ID is absent from the reference tree gets a ``danger-soft``
  background; the cell text colour is left alone to keep it readable

Column resolution and clipboard parsing live in :mod:`pyitolstudio.tables`
(Qt-free) so they can be unit-tested without a QApplication.
"""

from __future__ import annotations

from typing import Any, NamedTuple

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, QRectF, QSettings, Qt, Signal
from PySide6.QtGui import (
    QFont,
    QFontMetrics,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedLayout,
    QStyledItemDelegate,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..icons import icon, icon_pixmap
from ..tables import (
    MAX_EDIT_COLS,
    MAX_EDIT_ROWS,
    PASTE_COLUMNS,
    PASTE_EMPTY,
    column_labels,
    is_numeric_column,
    parse_pasted_table,
    resolve_columns,
    within_edit_envelope,
)
from ..theme import (
    FONT_SIZE_CAPTION,
    FONT_SIZE_MONO,
    MONO_FAMILIES,
    RADIUS_S,
    SPACE_1,
    SPACE_2,
    SPACE_3,
)
from ..theme_mode import theme_color, theme_qcolor

STATUS_MATCHED = "matched"
STATUS_MISSING = "missing"
STATUS_UNCHECKED = "unchecked"

# Shared invalid-model-index sentinel for Qt model-API default arguments
# (calling ``QModelIndex()`` per call in a default is both wasteful and a
# bugbear B008 hit; the default-constructed index is immutable and reusable).
_INVALID_INDEX = QModelIndex()

# View columns
COL_ROW_NUMBER = 0

# Column metrics.  The grid used to hand every column a fixed width, so a
# 3-column template filled 336 of the 860 px centre pane and the leftover
# strip became the brightest thing on screen (UI review §05).  The data
# columns now share whatever is left after the two fixed ones.
COL_ROW_NUMBER_WIDTH = 44
COL_STATUS_WIDTH = 132
DATA_COLUMN_MIN = 100
# Several data columns share the pane between them, so there is no reason to
# cap them — a cap just leaves a strip of empty grid at the right, which is
# what made the old fixed widths look broken.  A *single* data column does get
# a cap: without it a one-column template stretches into an empty runway.
DATA_COLUMN_MAX_SINGLE = 360
DATA_COLUMN_FALLBACK = 160

# Custom role: raw status key, so the chip delegate can style itself without
# re-deriving the verdict.
STATUS_ROLE = int(Qt.ItemDataRole.UserRole) + 1

# status key → (icon name, foreground token, background token, border token)
# The matched foreground reads ``accent_link`` (AA-safe on light ground) rather
# than ``accent`` — design review P0#3: the plain brand green is 3.5:1 on
# white, too low for 11px text.
STATUS_CHIP: dict[str, tuple[str, str, str, str]] = {
    STATUS_MATCHED: ("circle-check", "accent_link", "accent_soft", "accent_line"),
    STATUS_MISSING: ("triangle-alert", "danger", "danger_soft", "danger"),
    STATUS_UNCHECKED: ("circle-dashed", "text_tertiary", "panel_alt", "line2"),
}

_ROW_HEIGHT = 28
_PREVIEW_RATIO_KEY = "ui/preview_ratio"
_DEFAULT_PREVIEW_RATIO = 0.62  # grid share; preview gets the remainder


_MONO_FONT: QFont | None = None


def _mono_font() -> QFont:
    """Cached monospace font for the grid.

    ``data()`` is queried per cell per repaint; allocating a fresh ``QFont``
    every time is wasteful on the hot path (UI review P2-6).  ``QFont`` is
    implicitly shared and only read here, so one cached instance is safe —
    and the mono face does not change with the theme, so it never needs
    invalidating.
    """
    global _MONO_FONT  # noqa: PLW0603
    if _MONO_FONT is None:
        font = QFont()
        font.setFamilies(list(MONO_FAMILIES))
        font.setPixelSize(FONT_SIZE_MONO)
        _MONO_FONT = font
    return _MONO_FONT


class DataTableModel(QAbstractTableModel):
    """IDL-driven grid: row-number column + data columns + status column."""

    invalidity_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._frame = pd.DataFrame()
        self._columns: list[str] = []
        self._labels: list[str] = []
        self._numeric: list[bool] = []
        self._valid_ids: set[str] | None = None
        self._idl_columns: list[str] = []
        self._idl_labels: list[str] = []
        self._dynamic: str | None = None
        self._editable = True

    # -- Qt model API ---------------------------------------------------
    def rowCount(self, parent: QModelIndex = _INVALID_INDEX) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._frame)

    def columnCount(self, parent: QModelIndex = _INVALID_INDEX) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._columns) + 2

    @property
    def status_column(self) -> int:
        return len(self._columns) + 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        column = index.column()
        if column == COL_ROW_NUMBER:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(index.row() + 1)
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if role == Qt.ItemDataRole.ForegroundRole:
                return theme_qcolor("text_tertiary")
            if role == Qt.ItemDataRole.FontRole:
                return _mono_font()
            return None
        if column == self.status_column:
            return self._status_data(index.row(), role)
        if column - 1 >= len(self._columns):
            return None

        data_col = column - 1
        value = self._frame.iat[index.row(), data_col]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return "" if pd.isna(value) else str(value)
        if role == Qt.ItemDataRole.BackgroundRole:
            # Whole row, not just the offending cell — and the text colour is
            # deliberately left alone (design book §9.2).
            return theme_qcolor("danger_soft") if self._row_is_bad(index.row()) else None
        if role == Qt.ItemDataRole.FontRole:
            return _mono_font() if (data_col == 0 or self._numeric[data_col]) else None
        if role == Qt.ItemDataRole.TextAlignmentRole and self._numeric[data_col]:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def _status_data(self, row: int, role: int) -> Any:
        status = self.status_of_row(row)
        if role == STATUS_ROLE:
            return status
        if role == Qt.ItemDataRole.DisplayRole:
            return {
                STATUS_MATCHED: tr("table.status_matched"),
                STATUS_MISSING: tr("table.status_missing"),
                STATUS_UNCHECKED: tr("table.status_unchecked"),
            }[status]
        if role == Qt.ItemDataRole.DecorationRole:
            name, token = STATUS_CHIP[status][0], STATUS_CHIP[status][1]
            return icon(name, 13, theme_color(token))
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:  # noqa: N802
        if role != Qt.ItemDataRole.EditRole or not index.isValid() or not self._editable:
            return False
        column = index.column()
        if column == COL_ROW_NUMBER or column == self.status_column:
            return False
        data_col = column - 1
        if data_col >= len(self._columns):
            return False
        self._frame.iat[index.row(), data_col] = "" if value is None else str(value)
        self._numeric[data_col] = is_numeric_column(
            [str(v) for v in self._frame.iloc[:, data_col]]
        )
        self.dataChanged.emit(
            self.index(index.row(), 0), self.index(index.row(), self.status_column)
        )
        # Validation runs here, never in paintEvent (design book §9.2).
        self.invalidity_changed.emit()
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        base = Qt.ItemFlag.ItemIsEnabled
        column = index.column()
        if column == COL_ROW_NUMBER:
            # The row number is a ruler, not data: read-only, no editing, and
            # outside the cell-level selection.
            return base
        if column == self.status_column or not self._editable:
            return base | Qt.ItemFlag.ItemIsSelectable
        return base | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            # QHeaderView reads the alignment from this role (falling back to
            # setDefaultAlignment, which a stylesheet overrides) — and the
            # required-column marker is painted next to a left-aligned label.
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if section == COL_ROW_NUMBER:
            return ""
        if section == self.status_column:
            return tr("table.col_status")
        if section - 1 < len(self._labels):
            return self._labels[section - 1]
        return ""

    # -- spec / data ----------------------------------------------------
    def set_idl(self, idl: dict[str, Any] | None) -> None:
        """Adopt the IDL's column layout (keys, labels, dynamic tail)."""
        idl = idl or {}
        self._idl_columns = [str(c) for c in idl.get("data_columns", [])]
        self._idl_labels = [str(c) for c in idl.get("data_column_labels", [])]
        self._dynamic = idl.get("data_columns_dynamic")

    def set_frame(self, frame: pd.DataFrame | None, valid_ids: set[str] | None = None) -> None:
        self.beginResetModel()
        self._frame = frame.copy() if frame is not None else pd.DataFrame()
        self._valid_ids = valid_ids
        self._resolve_columns()
        self.endResetModel()
        self.invalidity_changed.emit()

    def set_valid_ids(self, valid_ids: set[str] | None) -> None:
        """Re-run ID validation against a (new) reference tree."""
        self._valid_ids = valid_ids
        self._touch_all()
        self.invalidity_changed.emit()

    def set_editable(self, editable: bool) -> None:
        if editable == self._editable:
            return
        self._editable = editable
        self._touch_all()

    def _touch_all(self) -> None:
        if len(self._frame):
            self.dataChanged.emit(
                self.index(0, 0), self.index(len(self._frame) - 1, self.status_column)
            )

    @property
    def editable(self) -> bool:
        return self._editable

    @property
    def dynamic(self) -> str | None:
        return self._dynamic

    @property
    def idl_columns(self) -> list[str]:
        return list(self._idl_columns)

    def _resolve_columns(self) -> None:
        frame_columns = [str(c) for c in self._frame.columns]
        columns = resolve_columns(frame_columns, self._idl_columns, self._dynamic)
        if not columns:
            # An empty unit still shows the columns its type will need, so the
            # grid is not a blank slate.
            columns = list(self._idl_columns)
        if list(self._frame.columns) != columns:
            self._frame = self._frame.reindex(columns=columns, fill_value="")
        self._columns = columns
        self._labels = column_labels(columns, self._idl_columns, self._idl_labels)
        self._numeric = [is_numeric_column([str(v) for v in self._frame[c]]) for c in columns]

    # -- helpers ---------------------------------------------------------
    @property
    def frame(self) -> pd.DataFrame:
        return self._frame

    @property
    def columns(self) -> list[str]:
        return list(self._columns)

    def view_column(self, name: str) -> int:
        """View index of a data column, row-number offset included."""
        return self._columns.index(name) + 1

    def status_of_row(self, row: int) -> str:
        if self._valid_ids is None or not self._columns:
            return STATUS_UNCHECKED
        value = str(self._frame.iat[row, 0]).strip()
        if not value or value.lower() == "nan":
            # Nothing to match yet (e.g. a freshly added row); "树中无此 ID"
            # would be a false claim.
            return STATUS_UNCHECKED
        return STATUS_MATCHED if value in self._valid_ids else STATUS_MISSING

    def _row_is_bad(self, row: int) -> bool:
        return self.status_of_row(row) == STATUS_MISSING

    def unmatched_ids(self) -> list[str]:
        """First-column values not present in the reference tree.

        Must share ``status_of_row``'s verdict: a blank cell (a freshly added
        row) is "unchecked", not "missing" — otherwise the footer's
        ``match_stats`` and the inspector banner report contradictory counts
        (UI review P1-4 / code review P1-2).
        """
        if self._frame.empty or self._valid_ids is None or not self._columns:
            return []
        return [
            str(self._frame.iat[r, 0])
            for r in range(len(self._frame))
            if self.status_of_row(r) == STATUS_MISSING
        ]

    def match_stats(self) -> tuple[int, int, int]:
        """(rows, matched, missing) for the footer."""
        rows = len(self._frame)
        if self._valid_ids is None:
            return rows, 0, 0
        statuses = [self.status_of_row(r) for r in range(rows)]
        return (
            rows,
            sum(1 for s in statuses if s == STATUS_MATCHED),
            sum(1 for s in statuses if s == STATUS_MISSING),
        )

    def to_rows(self) -> list[dict[str, str]]:
        """DataFrame → list of row dicts for the engine (columns preserved)."""
        if self._frame.empty:
            return []
        return [
            {str(col): ("" if pd.isna(val) else str(val)) for col, val in zip(self._columns, row, strict=False)}
            for row in self._frame.itertuples(index=False, name=None)
        ]

    # -- editing ---------------------------------------------------------
    def append_row(self) -> bool:
        if not self._editable or not self._columns:
            return False
        row = len(self._frame)
        self.beginInsertRows(QModelIndex(), row, row)
        self._frame.loc[row] = ["" for _ in self._columns]
        self.endInsertRows()
        self.invalidity_changed.emit()
        return True

    def _pasted_keys(self, width: int) -> list[str]:
        """Column keys for a pasted block *width* columns wide.

        Fixed columns come from the IDL; an open-ended tail is named the same
        way the wizard names it (``value_2``, ``value_3`` … by absolute index)
        so a pasted matrix round-trips identically.
        """
        if self._idl_columns and width >= len(self._idl_columns):
            keys = list(self._idl_columns)
            if self._dynamic:
                prefix = self._dynamic.split("_")[0]
                keys += [f"{prefix}_{i}" for i in range(len(keys), width)]
            else:
                keys += [f"col_{i}" for i in range(len(keys), width)]
            return keys[:width]
        if self._idl_columns and not self._dynamic and width < len(self._idl_columns):
            # Under-width paste for a fixed-layout type (should already have
            # been rejected upstream): keep the real IDL column names for the
            # cells that are present instead of renaming every one to col_N
            # (code review P0-3).
            return self._idl_columns[:width]
        if self._columns and width == len(self._columns):
            return list(self._columns)
        return [f"col_{i}" for i in range(width)]

    def apply_rows(self, rows: list[list[str]]) -> None:
        """Replace the table with a pasted block in a single model reset."""
        if not rows:
            return
        keys = self._pasted_keys(len(rows[0]))
        records = [dict(zip(keys, row, strict=False)) for row in rows]
        self.beginResetModel()
        self._frame = pd.DataFrame(records, columns=keys)
        self._columns = keys
        self._labels = column_labels(keys, self._idl_columns, self._idl_labels)
        self._numeric = [is_numeric_column([str(v) for v in self._frame[c]]) for c in keys]
        self.endResetModel()
        self.invalidity_changed.emit()

    def retranslate_ui(self) -> None:
        """Re-emit the status column after a locale switch."""
        self._touch_all()
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, self.status_column, self.status_column
        )


class StatusChipDelegate(QStyledItemDelegate):
    """Paints the status cell as a chip (icon + text + tinted fill)."""

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:  # noqa: N802
        status = index.data(STATUS_ROLE)
        if status not in STATUS_CHIP:
            super().paint(painter, option, index)
            return
        icon_name, fg, bg, border = STATUS_CHIP[status]
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        chip = option.rect.adjusted(SPACE_3, 4, -SPACE_3, -4)
        path = QPainterPath()
        path.addRoundedRect(QRectF(chip), RADIUS_S, RADIUS_S)
        painter.fillPath(path, theme_qcolor(bg))
        painter.strokePath(path, QPen(theme_qcolor(border), 1))

        glyph = icon_pixmap(icon_name, 12, theme_color(fg))
        left = chip.left() + SPACE_2
        painter.drawPixmap(left, chip.center().y() - 6, glyph)

        font = painter.font()
        font.setPixelSize(FONT_SIZE_CAPTION)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(theme_qcolor(fg))
        text_rect = QRect(
            left + 12 + SPACE_2, chip.top(), chip.width() - 12 - SPACE_2 * 3, chip.height()
        )
        painter.drawText(
            text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text
        )
        painter.restore()

    def sizeHint(self, option, index: QModelIndex):  # noqa: N802
        hint = super().sizeHint(option, index)
        hint.setWidth(max(hint.width(), 120))
        return hint


class GridHeader(QHeaderView):
    """Header that left-aligns captions and appends a brand-coloured ``*``.

    This header paints its own sections instead of delegating to the stylesheet.
    Reason: once ``QHeaderView::section`` is styled, QStyleSheetStyle forces
    centred captions and ignores both ``text-align`` and
    ``setDefaultAlignment``, and PySide6 does not expose ``initStyleOption`` for
    headers — so there is no way to learn where the label was drawn and place
    the marker next to it.  Owning the paint keeps the label and the marker in
    a known relationship, and the tokens still supply every colour.
    """

    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        self._required: set[int] = set()

    def set_required_columns(self, sections: set[int]) -> None:
        self._required = set(sections)
        self.viewport().update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        """Own the whole header strip, not just the sections on it.

        ``paintSection`` only receives the rect of its own section, so whatever
        sits to the right of the last column belongs to nobody and fell through
        to the palette — which, with only the stylesheet applied, was still the
        system's ``#efefef``.  That is where the 428x32 light rectangle in the
        middle of the dark window came from.  Fill the strip here, then let the
        base class draw the sections on top.
        """
        painter = QPainter(self.viewport())
        painter.fillRect(event.rect(), theme_qcolor("panel"))
        painter.end()
        super().paintEvent(event)

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:  # noqa: N802
        painter.save()
        painter.fillRect(rect, theme_qcolor("panel"))
        painter.setPen(QPen(theme_qcolor("line2"), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        font = QFont()
        font.setPixelSize(FONT_SIZE_CAPTION)
        # Medium, not Bold: an 11px CJK caption in a synthesised bold smears.
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        metrics = QFontMetrics(font)

        label = ""
        if self.model() is not None:
            label = str(
                self.model().headerData(
                    logical_index, self.orientation(), Qt.ItemDataRole.DisplayRole
                )
                or ""
            )
        marker = "*" if logical_index in self._required else ""
        room = rect.width() - SPACE_3 * 2 - (metrics.horizontalAdvance(marker) + SPACE_1)
        text_rect = QRect(rect.left() + SPACE_3, rect.top(), max(room, 0), rect.height())
        painter.setPen(theme_qcolor("text_tertiary"))
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            metrics.elidedText(label, Qt.TextElideMode.ElideRight, max(room, 0)),
        )
        if marker:
            painter.setPen(theme_qcolor("accent_link"))
            painter.drawText(
                text_rect.adjusted(metrics.horizontalAdvance(label) + SPACE_1, 0, 0, 0),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                marker,
            )
        painter.restore()


class DataTableView(QTableView):
    """Table view that claims ⌘V only when no cell editor is open."""

    paste_requested = Signal()

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if (
            event.matches(QKeySequence.StandardKey.Paste)
            and self.state() != QAbstractItemView.State.EditingState
        ):
            self.paste_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class DataGridParts(NamedTuple):
    """The objects that make up a themed data grid."""

    table: DataTableView
    header: GridHeader
    model: DataTableModel
    status_delegate: StatusChipDelegate


def build_data_grid(parent: QWidget | None = None) -> DataGridParts:
    """Create a data grid wired the way both call sites need it.

    Shared by the workbench's centre pane and the wizard's data step.  The two
    used to disagree: a real grid in one, a plain TSV text box in the other, so
    the same data had two editing experiences and the wizard's version had no
    column headers, no status chips, no paste validation and no ID checking.
    Building both from one factory is what keeps them from drifting apart again
    (UI review §03 P0-3).
    """
    model = DataTableModel(parent)
    table = DataTableView(parent)
    table.setObjectName("dataGrid")
    table.setModel(model)
    table.setShowGrid(False)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    table.setEditTriggers(
        QAbstractItemView.EditTrigger.DoubleClicked
        | QAbstractItemView.EditTrigger.EditKeyPressed
        | QAbstractItemView.EditTrigger.AnyKeyPressed
    )
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(_ROW_HEIGHT)
    table.setWordWrap(False)
    header = GridHeader(Qt.Orientation.Horizontal, table)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    table.setHorizontalHeader(header)
    status_delegate = StatusChipDelegate(table)
    table.verticalHeader().setDefaultSectionSize(_ROW_HEIGHT)
    return DataGridParts(table, header, model, status_delegate)


def data_column_width(table: QTableView, count: int) -> int:
    """Width that lets *count* data columns fill the pane.

    Floored at ``DATA_COLUMN_MIN`` so numeric cells do not elide, and capped
    only when there is one column (``DATA_COLUMN_MAX_SINGLE``) so a
    single-column template does not stretch into an empty runway.  With two or
    more columns they simply share the pane and the grid fills it edge to edge.
    """
    available = table.viewport().width() - COL_ROW_NUMBER_WIDTH - COL_STATUS_WIDTH
    if available <= 0:
        return DATA_COLUMN_FALLBACK
    share = available // max(count, 1)
    if count <= 1:
        return max(DATA_COLUMN_MIN, min(DATA_COLUMN_MAX_SINGLE, share))
    return max(DATA_COLUMN_MIN, share)


def layout_grid_columns(parts: DataGridParts) -> None:
    """Give a grid its column widths: fixed row number and status, data between.

    Shared by both call sites so the two grids cannot end up with different
    column geometry.
    """
    width = parts.model.columnCount()
    parts.header.set_required_columns({1} if parts.model.columns else set())
    parts.header.setSectionResizeMode(COL_ROW_NUMBER, QHeaderView.ResizeMode.Fixed)
    parts.table.setColumnWidth(COL_ROW_NUMBER, COL_ROW_NUMBER_WIDTH)
    if width:
        status = width - 1
        parts.table.setItemDelegateForColumn(status, parts.status_delegate)
        parts.header.setSectionResizeMode(status, QHeaderView.ResizeMode.Fixed)
        parts.table.setColumnWidth(status, COL_STATUS_WIDTH)
    # Data columns stay draggable, but their default width fills the pane.
    data_columns = list(range(1, max(width - 1, 1)))
    each = data_column_width(parts.table, len(data_columns)) if data_columns else 0
    for i in data_columns:
        parts.header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        parts.table.setColumnWidth(i, each)


class DataEditorPage(QWidget):
    """Data grid on top, template preview below (main workbench center pane)."""

    wizard_requested = Signal()

    def __init__(self, preview, parent=None) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QSplitter

        parts = build_data_grid(self)
        self._parts = parts
        self.model = parts.model
        self.table = parts.table
        self.header = parts.header
        self._status_delegate = parts.status_delegate
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_menu)
        self.table.paste_requested.connect(self.paste_from_clipboard)
        self.model.modelReset.connect(self._on_model_reset)

        # The grid and the empty-state guide share one slot; the footer stays
        # pinned below (design review P1#4).
        self._grid_stack = QStackedLayout()
        self._grid_stack.setContentsMargins(0, 0, 0, 0)
        self._grid_stack.addWidget(self.table)
        self._grid_stack.addWidget(self._build_empty_state())

        self.preview = preview
        top = QWidget()
        top.setObjectName("dataPane")
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addLayout(self._grid_stack, 1)
        top_layout.addWidget(self._build_footer())

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.addWidget(top)
        splitter.addWidget(self.preview)
        self._preview_splitter = splitter
        self._preview_ratio = self._load_preview_ratio()
        splitter.splitterMoved.connect(self._on_splitter_moved)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self._layout_columns()
        self.retranslate_ui()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().showEvent(event)
        # Column widths depend on the viewport, and the viewport only has a
        # width once the page is on screen.  A grid fitted while hidden keeps
        # the fallback width and grows a scroll bar it does not need, so refit
        # on every show.
        layout_grid_columns(self._parts)
        # Same reason for the split ratio: at construction the splitter has no
        # real height yet, so the saved/default ratio only lands once shown
        # (UI review P2-4).
        self._apply_preview_ratio()

    # -- footer ----------------------------------------------------------
    def _build_footer(self) -> QWidget:
        host = QWidget()
        host.setObjectName("gridFooter")
        row = QHBoxLayout(host)
        row.setContentsMargins(SPACE_3, SPACE_2, SPACE_3, SPACE_2)
        row.setSpacing(SPACE_3)
        self.count_label = QLabel("")
        self.count_label.setObjectName("monoData")
        self.notice_label = QLabel("")
        self.notice_label.setObjectName("noticeChip")
        self.notice_label.setProperty("state", "danger")
        self.notice_label.hide()
        self.add_row_button = QPushButton(icon("plus", 14), tr("table.add_row"))
        self.add_row_button.setObjectName("smallButton")
        self.add_row_button.clicked.connect(self.add_row)
        self.paste_button = QPushButton(icon("clipboard-paste", 14), tr("table.paste_tsv"))
        self.paste_button.setObjectName("smallButton")
        self.paste_button.setToolTip(tr("table.paste_hint"))
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        self.preview_toggle = QPushButton()
        self.preview_toggle.setObjectName("smallButton")
        self.preview_toggle.setToolTip(tr("table.preview_collapse"))
        self.preview_toggle.clicked.connect(self.toggle_preview)
        row.addWidget(self.count_label)
        row.addWidget(self.notice_label)
        row.addStretch(1)
        row.addWidget(self.preview_toggle)
        row.addWidget(self.add_row_button)
        row.addWidget(self.paste_button)
        self._update_preview_toggle()
        return host

    def _build_empty_state(self) -> QWidget:
        """Centered guide shown when there is neither data nor a unit context
        (design review P1#4)."""
        host = QWidget()
        host.setObjectName("emptyState")
        stack = QVBoxLayout(host)
        stack.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stack.setSpacing(SPACE_3)
        title = QLabel(tr("table.empty_title"))
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(tr("table.empty_body"))
        body.setObjectName("emptyBody")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)
        cta = QPushButton(icon("wand", 14, theme_color("on_accent")), tr("table.empty_cta"))
        cta.setObjectName("emptyCta")
        cta.setCursor(Qt.CursorShape.PointingHandCursor)
        cta.clicked.connect(self.wizard_requested.emit)
        stack.addStretch(1)
        stack.addWidget(title)
        stack.addWidget(body)
        stack.addWidget(cta, 0, Qt.AlignmentFlag.AlignHCenter)
        stack.addStretch(2)
        return host

    # -- preview pane ----------------------------------------------------
    @staticmethod
    def _load_preview_ratio() -> float:
        try:
            return float(QSettings().value(_PREVIEW_RATIO_KEY, _DEFAULT_PREVIEW_RATIO))
        except (TypeError, ValueError):
            return _DEFAULT_PREVIEW_RATIO

    def _apply_preview_ratio(self) -> None:
        total = self._preview_splitter.height()
        if total <= 0:
            return
        grid = max(int(total * self._preview_ratio), 120)
        self._preview_splitter.setSizes([grid, max(total - grid, 6 * 17)])

    def _on_splitter_moved(self, _pos, _index) -> None:
        sizes = self._preview_splitter.sizes()
        total = sum(sizes)
        if total:
            self._preview_ratio = sizes[0] / total
            QSettings().setValue(_PREVIEW_RATIO_KEY, self._preview_ratio)

    def toggle_preview(self) -> None:
        """Collapse / expand the template preview below the grid."""
        was_visible = self.preview.isVisible()
        self.preview.setVisible(not was_visible)
        if not was_visible:
            # Just expanded — restore the saved split.  Collapsing is handled
            # by Qt giving the freed space back to the grid, so no-op there
            # (previously both branches called the same thing).
            self._apply_preview_ratio()
        self._update_preview_toggle()

    def _update_preview_toggle(self) -> None:
        collapsed = not self.preview.isVisible()
        name = "eye" if collapsed else "eye-off"
        self.preview_toggle.setIcon(icon(name, 13, theme_color("text_tertiary")))
        self.preview_toggle.setText(
            tr("table.preview_expand") if collapsed else tr("table.preview_collapse")
        )

    def _show_notice(self, message: str, state: str = "danger") -> None:
        self.notice_label.setProperty("state", state)
        self.notice_label.setText(message)
        self.notice_label.style().unpolish(self.notice_label)
        self.notice_label.style().polish(self.notice_label)
        self.notice_label.show()

    def _clear_notice(self) -> None:
        self.notice_label.hide()

    def _update_footer(self) -> None:
        rows, matched, missing = self.model.match_stats()
        self.count_label.setText(tr("table.footer_count", rows, matched, missing))
        self.add_row_button.setEnabled(self.model.editable)

    def _on_model_reset(self) -> None:
        self._layout_columns()
        self._update_footer()
        self._sync_empty_state()

    def _sync_empty_state(self) -> None:
        """Show the guide page only when there is neither data nor a unit.

        The grid and the empty-state guide share one QStackedLayout, but the
        stack index was never switched — the whole guide block and its
        ``table.empty_*`` copy were unreachable (UI review P1-5).  An empty
        *selected* unit still has IDL columns, so it correctly keeps the grid;
        only a truly context-less centre pane (no unit) drops to the guide.
        """
        has_rows = self.model.rowCount() > 0 or bool(self.model.columns)
        self._grid_stack.setCurrentIndex(0 if has_rows else 1)

    def _layout_columns(self) -> None:
        layout_grid_columns(self._parts)

    # -- public API ------------------------------------------------------
    def load_dataframe(
        self,
        frame: pd.DataFrame,
        valid_ids: set[str] | None = None,
        idl: dict[str, Any] | None = None,
    ) -> None:
        self.model.set_idl(idl)
        self.model.set_frame(frame, valid_ids)
        self._clear_notice()
        # Envelope last: it may raise the read-only notice for large units.
        self._apply_edit_envelope()
        self._update_footer()

    def _apply_edit_envelope(self) -> None:
        """Large units go through the read-only channel (design book §9.2)."""
        rows = self.model.rowCount()
        columns = len(self.model.columns)
        editable = within_edit_envelope(rows, columns)
        self.model.set_editable(editable)
        self.paste_button.setEnabled(editable)
        if not editable:
            self._show_notice(
                tr("table.readonly_notice", rows, columns, MAX_EDIT_ROWS, MAX_EDIT_COLS),
                "warn",
            )

    def retranslate_ui(self) -> None:
        self.add_row_button.setText(tr("table.add_row"))
        self.paste_button.setText(tr("table.paste_tsv"))
        self.paste_button.setToolTip(tr("table.paste_hint"))
        self.model.retranslate_ui()
        self._update_footer()

    def retheme_ui(self) -> None:
        """Re-rasterise baked-in icon pixmaps after a theme switch."""
        self.add_row_button.setIcon(icon("plus", 14))
        self.paste_button.setIcon(icon("clipboard-paste", 14))
        self._update_preview_toggle()
        self.table.viewport().update()

    # -- editing ---------------------------------------------------------
    def add_row(self) -> None:
        if self.model.append_row():
            self._clear_notice()
            self._update_footer()

    def _show_table_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        paste_action = menu.addAction(icon("clipboard-paste", 14), tr("table.paste"))
        add_action = menu.addAction(icon("plus", 14), tr("table.add_row"))
        paste_action.setEnabled(self.model.editable)
        add_action.setEnabled(self.model.editable)
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == paste_action:
            self.paste_from_clipboard()
        elif chosen == add_action:
            self.add_row()

    def paste_from_clipboard(self) -> None:
        """Paste TSV/Excel text, replacing the table in one model reset."""
        if not self.model.editable:
            return
        text = QApplication.clipboard().text()
        parsed = parse_pasted_table(text, self.model.idl_columns, self.model.dynamic)
        if parsed.status == PASTE_EMPTY:
            self._show_notice(tr("table.paste_empty"), "warn")
            return
        if parsed.status == PASTE_COLUMNS:
            # Reported inline in the footer — never a modal (design book §9.2).
            self._show_notice(
                tr("table.paste_col_mismatch", parsed.expected_columns, parsed.received_columns)
            )
            return
        self.model.apply_rows(parsed.rows)
        self._clear_notice()
        self._apply_edit_envelope()
        self._update_footer()
