"""Left rail: reference-tree card + annotation-unit list (design book §5.1).

The rail answers two questions at a glance:

* **which tree am I working against, and how well does the data match it** —
  the tree card, promoted out of the status bar;
* **which units are on, what colour are they, and in what order will iTOL
  stack them** — the unit list, whose order is the dataset order.

The list is a ``QListWidget`` with a custom delegate rather than per-row item
widgets: item widgets do not survive ``InternalMove`` drag & drop, and the
row's own affordances (grip, eye, overflow) need to be hit-testable.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QModelIndex, QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..icons import icon, icon_pixmap
from ..theme import FONT_SIZE_MONO, RADIUS_M, SPACE_2, SPACE_3, SPACE_4
from ..theme_mode import qcolor, theme_color, theme_qcolor

# Item roles
UNIT_ID_ROLE = int(Qt.ItemDataRole.UserRole)
UNIT_TYPE_ROLE = int(Qt.ItemDataRole.UserRole) + 1
UNIT_COLOR_ROLE = int(Qt.ItemDataRole.UserRole) + 2
UNIT_HIDDEN_ROLE = int(Qt.ItemDataRole.UserRole) + 3

ROW_HEIGHT = 30

# Type → Lucide glyph.  iTOL's 31 types fall into a handful of shapes; anything
# unlisted gets a neutral glyph rather than a blank row.
TYPE_ICONS: dict[str, str] = {
    "dataset_colorstrip": "rectangle-horizontal",
    "dataset_simple_bar": "chart-no-axes-column",
    "dataset_multibar": "chart-column",
    "dataset_heatmap": "grid-3x3",
    "dataset_binary": "grid-2x2",
    "dataset_symbols": "shapes",
    "dataset_piechart": "chart-pie",
    "dataset_linechart": "chart-line",
    "dataset_connections": "network",
    "dataset_domains": "ruler",
    "dataset_labels": "type",
    "dataset_tree_colors": "palette",
    "dataset_collapse": "scissors",
    "dataset_prune": "scissors",
    "dataset_spacing": "move-horizontal",
    "dataset_popup_info": "info",
    "dataset_manual": "book-open",
    "dataset_meme": "dna",
    "dataset_placement": "layout-grid",
    "dataset_treestyle": "settings-2",
    "dataset_alignment": "text-align-justify",
    "dataset_range": "brackets",
    "dataset_timescale": "timer",
    "dataset_tanglegram": "git-branch",
    "dataset_gradient": "blend",
    "dataset_externalshape": "square",
    "dataset_image": "image",
    "dataset_arrows": "move-up-right",
    "dataset_boxplot": "rows-3",
    "dataset_style": "paintbrush",
    "dataset_text": "text-cursor",
}
DEFAULT_TYPE_ICON = "sliders-horizontal"


def type_icon_name(type_name: str) -> str:
    """Lucide glyph name for one annotation type (neutral when unlisted)."""
    return TYPE_ICONS.get(type_name, DEFAULT_TYPE_ICON)


def unit_type_icon(type_name: str, size: int = 15, color: str | None = None):
    """Lucide icon for one annotation type."""
    return icon(type_icon_name(type_name), size, color)


class TreeCard(QWidget):
    """Which tree is loaded, how well the IDs match, and how to change it."""

    change_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("treeCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)

        top = QHBoxLayout()
        top.setSpacing(SPACE_3)
        self._icon = QLabel()
        self._icon.setObjectName("treeCardIcon")
        self._icon.setFixedSize(26, 26)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setPixmap(icon_pixmap("folder-tree", 15, theme_color("accent")))
        text = QVBoxLayout()
        text.setSpacing(0)
        self.name_label = QLabel("")
        self.name_label.setObjectName("treeCardName")
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("treeCardMeta")
        text.addWidget(self.name_label)
        text.addWidget(self.meta_label)
        top.addWidget(self._icon)
        top.addLayout(text, 1)
        layout.addLayout(top)

        self.progress = QProgressBar()
        self.progress.setObjectName("treeProgress")
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.loading_label = QLabel("")
        self.loading_label.setObjectName("treeCardLoading")
        self.loading_label.hide()
        layout.addWidget(self.loading_label)

        foot = QHBoxLayout()
        foot.setSpacing(SPACE_3)
        self.match_label = QLabel("")
        self.match_label.setObjectName("treeCardMatch")
        self.change_button = QPushButton(tr("nav.tree_change"))
        self.change_button.setObjectName("linkButton")
        self.change_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_button.clicked.connect(self.change_requested.emit)
        foot.addWidget(self.match_label)
        foot.addStretch(1)
        foot.addWidget(self.change_button)
        layout.addLayout(foot)
        self.retranslate_ui()

    def set_tree(
        self,
        path: str,
        leaf_count: int | None = None,
        matched: int = 0,
        total: int = 0,
        loading: bool = False,
    ) -> None:
        """Render the card for a tree path (or clear it when empty)."""
        if not path:
            self.name_label.setText(tr("nav.tree_none"))
            self.meta_label.setText("")
            self.match_label.setText("")
            self.loading_label.hide()
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.setToolTip("")
            return
        self.name_label.setText(Path(path).name)
        self.setToolTip(path)
        if loading:
            # Leaf IDs are being read on a worker thread — show indeterminate
            # progress instead of a stale "0 matched" verdict (review P1#3).
            self.loading_label.setText(tr("nav.tree_loading"))
            self.loading_label.show()
            self.meta_label.setText("")
            self.match_label.setText("")
            self.progress.setRange(0, 0)
            return
        self.loading_label.hide()
        if leaf_count is None:
            self.meta_label.setText(tr("nav.tree_meta_unknown"))
        else:
            self.meta_label.setText(tr("nav.tree_meta", f"{leaf_count:,}"))
        if total:
            self.match_label.setText(tr("nav.tree_match", matched, total))
            self.progress.setRange(0, total)
            self.progress.setValue(matched)
        else:
            self.match_label.setText(tr("nav.tree_match_none"))
            self.progress.setRange(0, 1)
            self.progress.setValue(0)

    def retranslate_ui(self) -> None:
        self.change_button.setText(tr("nav.tree_change"))
        if self.loading_label.isVisible():
            self.loading_label.setText(tr("nav.tree_loading"))

    def retheme_ui(self) -> None:
        self._icon.setPixmap(icon_pixmap("folder-tree", 15, theme_color("accent")))


class UnitRowDelegate(QStyledItemDelegate):
    """Paints one unit row and hit-tests its eye / overflow affordances."""

    toggle_hidden = Signal(str)
    overflow_requested = Signal(str, QPoint)

    def _layout(self, rect: QRect) -> dict[str, QRect]:
        # A 3px bar leads the row where a 7px chip used to sit between the name
        # and the eye.  The chip was unlabelled and ambiguous — nothing said
        # whether it meant "category colour" or "state" — and it crowded the
        # row's trailing controls.  A leading bar reads as "this unit's colour"
        # and costs 3px instead of 14 (UI review §04 ⑥).
        x = rect.left() + SPACE_2 + 2  # leave the 2px selection bar its lane
        colour_bar = QRect(x, rect.top() + 6, 3, rect.height() - 12)
        x += 3 + SPACE_3
        grip = QRect(x, rect.top(), 10, rect.height())
        x += 10 + SPACE_3
        type_icon = QRect(x, rect.top(), 15, rect.height())
        x += 15 + SPACE_3
        overflow = QRect(rect.right() - SPACE_2 - 16, rect.top(), 16, rect.height())
        eye = QRect(overflow.left() - 4 - 20, rect.top(), 20, rect.height())
        name = QRect(x, rect.top(), max(eye.left() - SPACE_3 - x, 0), rect.height())
        return {
            "colour_bar": colour_bar,
            "grip": grip,
            "type": type_icon,
            "name": name,
            "eye": eye,
            "overflow": overflow,
        }

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:  # noqa: N802
        hidden = bool(index.data(UNIT_HIDDEN_ROLE))
        color = str(index.data(UNIT_COLOR_ROLE) or "")
        type_name = str(index.data(UNIT_TYPE_ROLE) or "")
        label = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect
        body = QRectF(rect.adjusted(SPACE_2, 0, -SPACE_2, 0))
        body_path = QPainterPath()
        body_path.addRoundedRect(body, RADIUS_M, RADIUS_M)
        if selected:
            # Double encoding: brand-tinted fill *and* a 2px bar, so the
            # selection never depends on colour alone (design book §5.1/§7).
            painter.fillPath(body_path, theme_qcolor("accent_soft"))
            bar = QPainterPath()
            bar.addRoundedRect(QRectF(body.left(), body.top() + 6, 2, body.height() - 12), 1, 1)
            painter.fillPath(bar, theme_qcolor("accent"))
        elif hovered:
            painter.fillPath(body_path, theme_qcolor("hover"))

        parts = self._layout(rect)
        # Selected body text uses accent_link: accent (#0e9c68) over
        # accent_soft is only 2.94:1 in light mode, below AA for the 12px
        # unit name.  The icon keeps accent — the 3:1 non-text bar is met
        # (UI review P0-3).
        name_token = "text_tertiary" if hidden else ("accent_link" if selected else "text")
        icon_token = "text_disabled" if hidden else ("accent" if selected else "text_dim")

        if hovered or selected:
            glyph = icon_pixmap("grip-vertical", 10, theme_color("text_disabled"))
            painter.drawPixmap(parts["grip"].left(), parts["grip"].center().y() - 5, glyph)
        glyph = icon_pixmap(type_icon_name(type_name), 15, theme_color(icon_token))
        painter.drawPixmap(parts["type"].left(), parts["type"].center().y() - 7, glyph)

        font = painter.font()
        font.setPixelSize(FONT_SIZE_MONO)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        painter.setPen(theme_qcolor(name_token))
        painter.drawText(
            parts["name"],
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            metrics.elidedText(label, Qt.TextElideMode.ElideRight, parts["name"].width()),
        )

        bar_path = QPainterPath()
        bar_path.addRoundedRect(QRectF(parts["colour_bar"]), 1.5, 1.5)
        bar_fill = qcolor(color) if _is_hex(color) else theme_qcolor("line2")
        if hidden:
            # A hidden unit is greyed out as a whole, its colour bar included.
            bar_fill.setAlpha(90)
        painter.fillPath(bar_path, bar_fill)

        if hovered or hidden:
            eye = "eye-off" if hidden else "eye"
            glyph = icon_pixmap(eye, 13, theme_color("text_tertiary"))
            painter.drawPixmap(parts["eye"].center().x() - 6, parts["eye"].center().y() - 6, glyph)
        if hovered:
            glyph = icon_pixmap("ellipsis-vertical", 13, theme_color("text_tertiary"))
            painter.drawPixmap(
                parts["overflow"].center().x() - 6, parts["overflow"].center().y() - 6, glyph
            )
        painter.restore()

    def sizeHint(self, option, index: QModelIndex):  # noqa: N802
        hint = super().sizeHint(option, index)
        hint.setHeight(ROW_HEIGHT)
        return hint

    def editorEvent(self, event, model, option, index: QModelIndex) -> bool:  # noqa: N802
        if event.type() not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            return False
        unit_id = index.data(UNIT_ID_ROLE)
        if not unit_id:
            return False
        pos = event.position().toPoint()
        parts = self._layout(option.rect)
        if event.type() == QEvent.Type.MouseButtonPress:
            # Claim the click so the row is not dragged or re-selected.
            return parts["eye"].contains(pos) or parts["overflow"].contains(pos)
        if parts["eye"].contains(pos):
            self.toggle_hidden.emit(str(unit_id))
            return True
        if parts["overflow"].contains(pos):
            self.overflow_requested.emit(
                str(unit_id), option.widget.viewport().mapToGlobal(parts["overflow"].bottomLeft())
            )
            return True
        return False


def _is_hex(value: str) -> bool:
    text = value.strip()
    return text.startswith("#") and len(text) in (4, 7, 9)


class UnitListWidget(QListWidget):
    """Annotation units, in iTOL dataset (stacking) order."""

    unit_activated = Signal(str)
    toggle_hidden = Signal(str)
    overflow_requested = Signal(str, QPoint)
    reordered = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("unitList")
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self._delegate = UnitRowDelegate(self)
        self.setItemDelegate(self._delegate)
        self._delegate.toggle_hidden.connect(self.toggle_hidden)
        self._delegate.overflow_requested.connect(self.overflow_requested)
        self._all_units: list = []
        self._query = ""
        # The unit the user intends to have selected, kept even while a filter
        # hides it, so clearing the filter can restore it (code review P2-1).
        self._pending_selection: str | None = None
        # Populated by set_units(), but the search box can filter before the
        # first population — initialise so _reflow never hits a missing attr.
        self._hidden: set[str] = set()
        self.currentItemChanged.connect(self._on_current_changed)
        self.model().rowsMoved.connect(self._on_rows_moved)

    # -- population ------------------------------------------------------
    def set_units(self, units, hidden_ids: set[str], selected_id: str | None = None) -> None:
        """Rebuild the list; *units* is already in dataset order."""
        self._all_units = list(units)
        self._hidden = set(hidden_ids)
        self._reflow(selected_id)

    def _reflow(self, selected_id: str | None = None) -> None:
        """Repopulate the widget honoring the active search filter."""
        query = self._query
        # Remember which unit was current so a rebuild that re-selects the
        # same unit does not re-emit unit_activated (which reloads the unit,
        # rebuilds the form and regenerates the preview for nothing).
        previous = self.current_unit_id()
        if query:
            visible = [
                u
                for u in self._all_units
                if query in (u.label or u.type_name).lower() or query in u.type_name.lower()
            ]
        else:
            visible = self._all_units
        selected = selected_id
        if selected is not None:
            self._pending_selection = selected
        active_query = bool(query)
        self.setDragDropMode(
            QListWidget.DragDropMode.NoDragDrop
            if active_query
            else QListWidget.DragDropMode.InternalMove
        )
        self.blockSignals(True)
        self.clear()
        for unit in visible:
            item = QListWidgetItem(unit.label or unit.type_name)
            item.setData(UNIT_ID_ROLE, unit.unit_id)
            item.setData(UNIT_TYPE_ROLE, unit.type_name)
            item.setData(UNIT_COLOR_ROLE, unit.color)
            item.setData(UNIT_HIDDEN_ROLE, unit.unit_id in self._hidden)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
                | Qt.ItemFlag.ItemIsDropEnabled
            )
            item.setSizeHint(self._item_size())
            self.addItem(item)
        self.blockSignals(False)
        if selected is not None:
            self.blockSignals(True)
            self.select_unit(selected)
            self.blockSignals(False)
            if selected != previous:
                self.unit_activated.emit(selected)

    def set_filter(self, query: str) -> None:
        """Filter the list by label/type; a clear query restores all units."""
        query = (query or "").strip().lower()
        if query == self._query:
            return
        current = self._pending_selection or self.current_unit_id()
        self._query = query
        self._reflow(current)

    def clear_filter(self) -> None:
        if self._query:
            self._query = ""
            self._reflow(self._pending_selection or self.current_unit_id())

    def _item_size(self) -> QSize:
        return QSize(0, ROW_HEIGHT)

    def select_unit(self, unit_id: str) -> bool:
        item = self.item_for_unit(unit_id)
        if item is None:
            return False
        self._pending_selection = unit_id
        self.setCurrentItem(item)
        return True

    def item_for_unit(self, unit_id: str) -> QListWidgetItem | None:
        for row in range(self.count()):
            item = self.item(row)
            if item.data(UNIT_ID_ROLE) == unit_id:
                return item
        return None

    def ordered_ids(self) -> list[str]:
        return [str(self.item(r).data(UNIT_ID_ROLE)) for r in range(self.count())]

    def set_hidden(self, unit_id: str, hidden: bool) -> None:
        if hidden:
            self._hidden.add(unit_id)
        else:
            self._hidden.discard(unit_id)
        item = self.item_for_unit(unit_id)
        if item is None:
            return
        item.setData(UNIT_HIDDEN_ROLE, hidden)
        self.update(self.indexFromItem(item))

    def current_unit_id(self) -> str | None:
        item = self.currentItem()
        return str(item.data(UNIT_ID_ROLE)) if item is not None else None

    # -- signals ---------------------------------------------------------
    def _on_current_changed(self, current, _previous) -> None:
        if current is not None:
            unit_id = str(current.data(UNIT_ID_ROLE))
            self._pending_selection = unit_id
            self.unit_activated.emit(unit_id)

    def _on_rows_moved(self, *_args) -> None:
        # The list order *is* the iTOL dataset order — push it to the project.
        self.reordered.emit(self.ordered_ids())


class RailWidget(QWidget):
    """The whole left rail: tree card, section header, unit list."""

    collapse_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("rail")
        self._collapsed = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card_host = QWidget()
        card_host.setObjectName("railCardHost")
        card_layout = QVBoxLayout(card_host)
        card_layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_3)
        self.tree_card = TreeCard()
        card_layout.addWidget(self.tree_card)
        layout.addWidget(card_host)

        section = QWidget()
        section.setObjectName("railSection")
        section_layout = QHBoxLayout(section)
        section_layout.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_2)
        section_layout.setSpacing(SPACE_3)
        self.section_label = QLabel(tr("nav.units_caption"))
        self.section_label.setObjectName("caption")
        self.count_label = QLabel("0")
        self.count_label.setObjectName("countChip")
        section_layout.addWidget(self.section_label)
        section_layout.addWidget(self.count_label)
        section_layout.addStretch(1)
        self._collapse_button = QToolButton()
        self._collapse_button.setObjectName("iconButton")
        self._collapse_button.setToolTip(tr("nav.collapse_panel"))
        self._collapse_button.clicked.connect(self.collapse_requested.emit)
        section_layout.addWidget(self._collapse_button)
        layout.addWidget(section)

        self.unit_list = UnitListWidget()
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText(tr("nav.search_placeholder"))
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self.unit_list.set_filter)
        # The search box sits in its own inset host so it aligns with the 12px
        # card / section gutter — previously it was added straight to the 0-
        # margin root layout and butted up against the rail edge (UI P1-2).
        search_host = QWidget()
        search_host.setObjectName("railSearchHost")
        search_layout = QVBoxLayout(search_host)
        search_layout.setContentsMargins(SPACE_4, 0, SPACE_4, SPACE_3)
        search_layout.setSpacing(0)
        search_layout.addWidget(self.search_box)
        layout.addWidget(search_host)
        layout.addWidget(self.unit_list, 1)

        # Bake the chevron icon now, not only when retheme/retranslate fire —
        # a standalone RailWidget used to render an empty 24px button (UI P2-8).
        self.set_collapsed(self._collapsed)
        self._collapse_button.setAccessibleName(tr("nav.collapse_panel"))

    def set_count(self, count: int) -> None:
        self.count_label.setText(str(count))

    def set_collapsed(self, collapsed: bool) -> None:
        """Mirror the rail's visibility into the chevron affordance."""
        self._collapsed = collapsed
        self._collapse_button.setIcon(
            icon("panel-left-open" if collapsed else "panel-left-close", 13, theme_color("text_tertiary"))
        )
        self._collapse_button.setToolTip(
            tr("nav.expand_panel") if collapsed else tr("nav.collapse_panel")
        )

    def retranslate_ui(self) -> None:
        self.section_label.setText(tr("nav.units_caption"))
        self.search_box.setPlaceholderText(tr("nav.search_placeholder"))
        self.tree_card.retranslate_ui()
        self.set_collapsed(self._collapsed)

    def retheme_ui(self) -> None:
        """Re-rasterise the rail's baked-in icon pixmaps after a theme switch."""
        self.tree_card.retheme_ui()
        self.set_collapsed(self._collapsed)
        self.unit_list.viewport().update()


__all__ = [
    "DEFAULT_TYPE_ICON",
    "ROW_HEIGHT",
    "RailWidget",
    "TreeCard",
    "TYPE_ICONS",
    "UNIT_COLOR_ROLE",
    "UNIT_HIDDEN_ROLE",
    "UNIT_ID_ROLE",
    "UNIT_TYPE_ROLE",
    "UnitListWidget",
    "UnitRowDelegate",
    "unit_type_icon",
]
