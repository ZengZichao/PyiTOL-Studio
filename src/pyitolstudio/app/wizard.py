"""Template wizard (FR-1) — design book §5.3.

Four steps bound to a left-rail stepper; each step is clickable (回退 is
always allowed, forward is allowed only up to the highest reached step).  The
type picker replaces its old single-column list with a searchable three-group
card grid; the parameter step reuses the central inspector and pairs it with
a short summary panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..adapter import (
    build_form_idl,
    defaults_for_idl,
    export_template_file,
    generate_template_text,
    list_template_types,
)
from ..i18n import tr, translator
from ..icons import icon, icon_pixmap
from ..tables import columns_acceptable
from ..theme import (
    FONT_SIZE_CAPTION,
    FONT_SIZE_MONO,
    MONO_FAMILIES,
    RADIUS_S,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)
from ..theme_mode import theme_color
from .inspector import ParameterForm
from .table_editor import build_data_grid, layout_grid_columns
from .unit_list import TYPE_ICONS, type_icon_name
from .widgets import LayoutSizeHintButton

PAGE_TYPE, PAGE_DATA, PAGE_PARAMS, PAGE_PREVIEW = range(4)

# Per step: (label_i18n_key, sub_i18n_key).  Step 1 has no subtitle.
STEP_PAIRS = (
    ("wizard.step1_label", ""),
    ("wizard.step2_label", "wizard.step2_sub"),
    ("wizard.step3_label", "wizard.step3_sub"),
    ("wizard.step4_label", "wizard.step4_sub"),
)


# ---------------------------------------------------------------------------
# Type grid: groups, descriptions, glyphs (design §5.3 step 1)
# ---------------------------------------------------------------------------

SUBGROUP_ORDER = ("basic", "matrix", "structure", "other")
SUBGROUP_LABEL_KEYS = {
    "basic": ("wizard.group_basic", "wizard.group_basic_desc"),
    "matrix": ("wizard.group_matrix", "wizard.group_matrix_desc"),
    "structure": ("wizard.group_structure", "wizard.group_structure_desc"),
    "other": ("wizard.group_other", "wizard.group_other_desc"),
}

_BASIC = {
    "dataset_colorstrip",
    "dataset_simple_bar",
    "dataset_symbols",
    "dataset_binary",
    "dataset_piechart",
}
_MATRIX = {
    "dataset_multibar",
    "dataset_heatmap",
    "dataset_linechart",
    "dataset_gradient",
    "dataset_boxplot",
    "dataset_timescale",
    "dataset_tanglegram",
}
_STRUCTURE = {
    "dataset_connections",
    "dataset_domains",
    "dataset_externalshape",
    "dataset_alignment",
    "dataset_image",
    "dataset_arrows",
    "dataset_text",
    "dataset_style",
    "dataset_range",
}

# Glyphs come from :data:`unit_list.TYPE_ICONS` (single source of truth), so a
# new template type only has to be added there — the wizard used to keep a
# byte-identical copy here that inevitably drifted (UI review P2-7).


def _subgroup(type_name: str) -> str:
    if type_name in _BASIC:
        return "basic"
    if type_name in _MATRIX:
        return "matrix"
    if type_name in _STRUCTURE:
        return "structure"
    return "other"


TYPE_DESCRIPTIONS = {
    "dataset_colorstrip": ("按分组为每个叶节点着色，最常用的分类注释", "Color leaves by category — the everyday classification"),
    "dataset_simple_bar": ("单值条形图，展示连续数值大小", "Single-value bars for continuous magnitudes"),
    "dataset_multibar": ("每个叶节点多列并列柱状图", "Stacked bars per leaf for grouped magnitudes"),
    "dataset_heatmap": ("多列数值矩阵，按色阶映射为热图", "Multi-column numeric matrix mapped to a colour ramp"),
    "dataset_binary": ("用形状开关标记二值状态", "Mark 0/1 state with per-column symbols"),
    "dataset_symbols": ("按类型绘制圆形、方形、星形等标记", "Round / square / star markers per category"),
    "dataset_piechart": ("每个叶节点绘制饼图展示组成比例", "Per-leaf pie showing compositional share"),
    "dataset_linechart": ("沿叶节点顺序的折线／曲线趋势", "Line / curve trend over leaf order"),
    "dataset_connections": ("连接任意两叶节点，展示关联关系", "Connect any two leaves to show relationships"),
    "dataset_domains": ("在枝上绘制结构域／区间矩形", "Domain / interval rectangles along branches"),
    "dataset_alignment": ("对齐树", "Tree alignment overlay"),
    "dataset_range": ("在树上标记范围／括号", "Range / bracket markers on the tree"),
    "dataset_timescale": ("时间轴缩放", "Time-axis scaling"),
    "dataset_gradient": ("沿枝渐变", "Gradient along branches"),
    "dataset_externalshape": ("外部形状", "External shape overlay"),
    "dataset_image": ("树旁图片", "Image overlay next to leaves"),
    "dataset_arrows": ("树旁箭头", "Arrow overlay next to leaves"),
    "dataset_boxplot": ("箱线图", "Boxplot overlay"),
    "dataset_style": ("样式覆盖", "Style overrides"),
    "dataset_text": ("树旁文本", "Text overlay next to leaves"),
    "dataset_tanglegram": ("两组分类系统对照", "Compare two taxonomy systems"),
}


# Human-facing name per template type.  The installed header is the
# template's technical identity (and the string the user will meet on iTOL),
# but it is not what anyone scans a picker for — 31 cards headed
# DATASET_COLORSTRIP, DATASET_SIMPLEBAR … all read as the same grey block
# (UI review §04 ⑩).  The name leads, the header moves to the tooltip.
# These are UI copy, not engine identity, so they are kept per-locale and the
# wizard picks by the active language (UI review P1-6 — the English UI used to
# render the Chinese table wholesale).
TYPE_NAMES = {
    "dataset_colorstrip": "颜色条",
    "dataset_simple_bar": "单值条形图",
    "dataset_multibar": "多列柱状图",
    "dataset_heatmap": "热图",
    "dataset_binary": "二值标记",
    "dataset_symbols": "形状标记",
    "dataset_piechart": "饼图",
    "dataset_linechart": "折线图",
    "dataset_connections": "连接线",
    "dataset_domains": "结构域",
    "dataset_alignment": "对齐",
    "dataset_range": "范围标记",
    "dataset_timescale": "时间轴",
    "dataset_gradient": "渐变",
    "dataset_externalshape": "外部形状",
    "dataset_image": "图片",
    "dataset_arrows": "箭头",
    "dataset_boxplot": "箱线图",
    "dataset_style": "样式覆盖",
    "dataset_text": "文本",
    "dataset_tanglegram": "分类对照",
    "dataset_labels": "标签",
    "dataset_tree_colors": "树着色",
    "dataset_spacing": "间距",
    "dataset_popup_info": "悬浮信息",
}

TYPE_NAMES_EN = {
    "dataset_colorstrip": "Colour strip",
    "dataset_simple_bar": "Simple bar",
    "dataset_multibar": "Multibar",
    "dataset_heatmap": "Heatmap",
    "dataset_binary": "Binary",
    "dataset_symbols": "Symbols",
    "dataset_piechart": "Pie chart",
    "dataset_linechart": "Line chart",
    "dataset_connections": "Connections",
    "dataset_domains": "Domains",
    "dataset_alignment": "Alignment",
    "dataset_range": "Range",
    "dataset_timescale": "Timescale",
    "dataset_gradient": "Gradient",
    "dataset_externalshape": "External shape",
    "dataset_image": "Image",
    "dataset_arrows": "Arrows",
    "dataset_boxplot": "Boxplot",
    "dataset_style": "Style",
    "dataset_text": "Text",
    "dataset_tanglegram": "Tanglegram",
    "dataset_labels": "Labels",
    "dataset_tree_colors": "Tree colours",
    "dataset_spacing": "Spacing",
    "dataset_popup_info": "Popup info",
}


def _type_name(type_name: str, header: str) -> str:
    """Locale-aware card name; falls back to the technical header."""
    table = TYPE_NAMES if translator().locale == "zh" else TYPE_NAMES_EN
    return table.get(type_name, header)


def _type_description(type_name: str, fallback: str) -> str:
    """Locale-aware card description; falls back to the group label."""
    pair = TYPE_DESCRIPTIONS.get(type_name)
    if pair is None:
        return fallback
    zh, en = pair
    return zh if translator().locale == "zh" else en


@dataclass
class _TypeInfo:
    type_name: str
    header: str
    name: str
    description: str
    icon_name: str
    subgroup: str


def _build_type_index() -> list[_TypeInfo]:
    out: list[_TypeInfo] = []
    for info in list_template_types():
        if not info.wizard_supported:
            continue
        if info.type_name not in TYPE_ICONS and _subgroup(info.type_name) == "other":
            continue
        out.append(
            _TypeInfo(
                type_name=info.type_name,
                header=info.header,
                name=_type_name(info.type_name, info.header),
                description=_type_description(info.type_name, info.group_label),
                icon_name=type_icon_name(info.type_name),
                subgroup=_subgroup(info.type_name),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Step rail — design §5.3 stepper
# ---------------------------------------------------------------------------


class _LayoutSizeHintButton(LayoutSizeHintButton):
    """Backwards-compatible alias of :class:`widgets.LayoutSizeHintButton`.

    The class moved to :mod:`.widgets` so the welcome page's action cards can
    share the same size-hint behaviour (UI review: container buttons must be
    sized by their content, never by their bare text).
    """


class StepButton(_LayoutSizeHintButton):
    """One numbered step; switches between pending, active and done states."""

    def __init__(self, title: str, subtitle: str, index: int, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("stepButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title = title
        self._subtitle = subtitle
        self._index = index

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        outer.setSpacing(0)
        top = QHBoxLayout()
        top.setSpacing(SPACE_3)
        self._badge = QLabel(str(index + 1))
        self._badge.setObjectName("stepBadge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setFixedSize(22, 22)
        top.addWidget(self._badge)
        text = QVBoxLayout()
        text.setSpacing(0)
        self._title_label = QLabel(title)
        self._title_label.setObjectName("stepTitle")
        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setObjectName("stepSubtitle")
        text.addWidget(self._title_label)
        text.addWidget(self._subtitle_label)
        text.addStretch(1)
        top.addLayout(text, 1)
        outer.addLayout(top)

    def set_state(self, state: str) -> None:
        """``pending`` / ``active`` / ``done`` (QSS attribute selector)."""
        self._badge.setProperty("state", state)
        self.setProperty("state", state)
        for widget in (self, self._badge):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        if state == "done":
            self._badge.setPixmap(icon_pixmap("check", 12, theme_color("accent")))
        else:
            self._badge.setPixmap(QPixmap())
            self._badge.setText(str(self._index + 1))


class WizardSteps(QWidget):
    """The four-step rail bound to the wizard's stacked pages."""

    step_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("wizardSteps")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_2, SPACE_4, SPACE_2, SPACE_4)
        layout.setSpacing(SPACE_2)
        self._buttons: list[StepButton] = []
        # Layout the labels as title / sub per the design's two-line step.
        for i, (label_key, sub_key) in enumerate(STEP_PAIRS):
            title = tr(label_key)
            subtitle = tr(sub_key) if sub_key else ""
            btn = StepButton(title, subtitle, i)
            btn.clicked.connect(lambda _checked=False, step=i: self.step_requested.emit(step))
            layout.addWidget(btn)
            self._buttons.append(btn)
        layout.addStretch(1)

    def sync(self, current: int, reached: int) -> None:
        for index, btn in enumerate(self._buttons):
            btn.setEnabled(index <= reached)
            if index < current:
                btn.set_state("done")
                btn.setChecked(False)
            elif index == current:
                btn.set_state("active")
                btn.setChecked(True)
            else:
                btn.set_state("pending")
                btn.setChecked(False)


# ---------------------------------------------------------------------------
# Step 1: searchable type grid
# ---------------------------------------------------------------------------


class TypeCard(_LayoutSizeHintButton):
    """One type's card: icon + Chinese name + description (design §5.3 step 1)."""

    def __init__(self, info: _TypeInfo, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("typeCard")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(92)
        # The description wraps, so the card must report height-for-width —
        # otherwise a two-line description clips at the 92px minimum
        # (UI review: button text must never truncate).
        from PySide6.QtWidgets import QSizePolicy

        policy = self.sizePolicy()
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setToolTip(f"{info.header} · {info.description}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)
        self._glyph_name = info.icon_name
        self._glyph = QLabel()
        self._glyph.setObjectName("typeCardIcon")
        self._glyph.setFixedSize(28, 28)
        self._glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._glyph)
        layout.addSpacing(SPACE_2)
        name = QLabel(info.name)
        name.setObjectName("typeCardName")
        layout.addWidget(name)
        desc = QLabel(info.description)
        desc.setObjectName("typeCardDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addStretch(1)
        self.toggled.connect(self._sync_glyph)
        self._sync_glyph()

    def _sync_glyph(self) -> None:
        """Repaint the glyph for the current check state.

        A checked card fills its icon container with solid ``accent``, but the
        glyph inside stayed ``text_dim`` regardless — grey on brand green is
        1.11:1, so the icon vanished exactly when the card got selected.  It
        flips to ``on_accent``, making a selected card read as a filled chip
        with a reversed glyph (UI review §04 ⑩).
        """
        checked = self.isChecked()
        token = "on_accent" if checked else "text_dim"
        self._glyph.setPixmap(icon_pixmap(self._glyph_name, 15, theme_color(token)))
        # Qt cannot select a descendant by an ancestor's :checked state, so the
        # container carries its own property for the stylesheet to match.
        self._glyph.setProperty("state", "checked" if checked else "normal")
        self._glyph.style().unpolish(self._glyph)
        self._glyph.style().polish(self._glyph)


class TypeGridPage(QWidget):
    """Card grid, grouped, with a search box that filters live."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._all = _build_type_index()
        self._cards: list[TypeCard] = []
        self._groups: dict[str, tuple[QLabel, QLabel, QWidget | None, list[TypeCard]]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_4)
        layout.setSpacing(SPACE_3)

        self.search = QLineEdit()
        self.search.setObjectName("typeSearch")
        self.search.setPlaceholderText(tr("wizard.type_search_hint"))
        self.search.setClearButtonEnabled(True)
        self.search.addAction(
            icon("search", 13, theme_color("text_tertiary")),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll = scroll
        self._scroll_holder = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_holder)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.setSpacing(SPACE_4)
        scroll.setWidget(self._scroll_holder)
        layout.addWidget(scroll, 1)

        self._build_grid()
        self._apply_filter("")

    def selected_type(self) -> str | None:
        for card in self._cards:
            if card.isChecked():
                return card.property("type_name")
        return None

    def select_type(self, type_name: str) -> bool:
        for card in self._cards:
            if card.property("type_name") == type_name:
                card.setChecked(True)
                self._scroll.ensureWidgetVisible(card)
                return True
        return False

    def _build_grid(self) -> None:
        # Tear down any previous layout contents (only happens on rebuild).
        while self._scroll_layout.count():
            item = self._scroll_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self._cards.clear()
        self._groups = {}

        for key in SUBGROUP_ORDER:
            label_key, desc_key = SUBGROUP_LABEL_KEYS[key]
            header = QLabel(tr(label_key))
            header.setObjectName("typeGroupHeader")
            self._scroll_layout.addWidget(header)
            sub_desc = QLabel(tr(desc_key))
            sub_desc.setObjectName("typeGroupDesc")
            self._scroll_layout.addWidget(sub_desc)

            cards_in_group: list[TypeCard] = []
            for info in self._all:
                if info.subgroup != key:
                    continue
                card = TypeCard(info)
                card.setProperty("type_name", info.type_name)
                card.clicked.connect(lambda _c=False, tn=info.type_name: self._on_card(tn))
                cards_in_group.append(card)
            container: QWidget | None = None
            if cards_in_group:
                grid = QGridLayout()
                grid.setContentsMargins(0, 0, 0, SPACE_3)
                grid.setSpacing(SPACE_3)
                for col in range(3):
                    grid.setColumnStretch(col, 1)
                for index, card in enumerate(cards_in_group):
                    grid.addWidget(card, index // 3, index % 3)
                container = QWidget()
                container.setLayout(grid)
                self._scroll_layout.addWidget(container)
                self._cards.extend(cards_in_group)
            # Remember the whole group (header + description + container + its
            # cards) so a filter pass can hide the header/description along with
            # the empty grid, not just the cards (UI review P1-1).
            self._groups[key] = (header, sub_desc, container, cards_in_group)
        self._scroll_layout.addStretch(1)

    def _apply_filter(self, query: str) -> None:
        needle = query.strip().lower()
        for _key, (header, sub_desc, container, cards) in self._groups.items():
            visible = 0
            for card in cards:
                type_name = str(card.property("type_name") or "")
                info = next((i for i in self._all if i.type_name == type_name), None)
                if info is not None:
                    haystack = f"{info.header} {info.description}".lower()
                    match = not needle or needle in haystack
                    card.setVisible(match)
                    visible += int(match)
            # Hide the whole group — header, description and grid — when no
            # card survives the filter; otherwise a search for "热图" leaves four
            # group titles stranded over one card (UI review P1-1).
            show_group = visible > 0
            header.setVisible(show_group)
            sub_desc.setVisible(show_group)
            if container is not None:
                container.setVisible(show_group)

    def _on_card(self, type_name: str) -> None:
        for card in self._cards:
            card.setChecked(card.property("type_name") == type_name)


# ---------------------------------------------------------------------------
# Step 2: data column pills + paste area
# ---------------------------------------------------------------------------


class ColumnPill(QFrame):
    """A `colpill` for the data column strip (design §5.3 step 2)."""

    def __init__(self, label: str, dynamic: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("colpill" + ("Dyn" if dynamic else ""))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_2, 1, SPACE_2, 1)
        layout.setSpacing(SPACE_2)
        dot = QLabel()
        dot.setObjectName("colpillDot")
        dot.setFixedSize(6, 6)
        layout.addWidget(dot)
        text = QLabel(label)
        text.setObjectName("colpillText")
        layout.addWidget(text)


class DataPage(QWidget):
    """Sample data area: a real grid, plus the column pills and import strip.

    This page used to be a plain TSV ``QTextEdit`` while the workbench showed a
    real grid — the same data with two different editors, and the wizard's had
    no column headers, no status chips, no paste validation and no ID checking.
    It now builds the grid from the same factory the workbench uses, so the two
    cannot drift apart (UI review §03 P0-3).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sample_columns: list[str] = []
        self._sample_dynamic: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_4)
        layout.setSpacing(SPACE_3)

        self.column_info = QLabel(tr("wizard.column_info_none"))
        self.column_info.setObjectName("dimLabel")
        layout.addWidget(self.column_info)

        self._pills_host = QWidget()
        self._pills_layout = QHBoxLayout(self._pills_host)
        self._pills_layout.setContentsMargins(0, 0, 0, 0)
        self._pills_layout.setSpacing(SPACE_2)
        self._pills_layout.addStretch(1)
        layout.addWidget(self._pills_host)

        bar = QHBoxLayout()
        bar.setSpacing(SPACE_2)
        self._sep_label = QLabel(tr("wizard.separator"))
        self.separator_combo = QComboBox()
        self.separator_combo.addItems(["TAB", "SPACE", "COMMA"])
        self.separator_combo.setToolTip(tr("wizard.sep_tooltip"))
        import_button = QPushButton(icon("import", 14), tr("wizard.import_csv"))
        paste_button = QPushButton(icon("clipboard-paste", 14), tr("wizard.paste_sample"))
        bar.addWidget(self._sep_label)
        bar.addWidget(self.separator_combo)
        bar.addStretch(1)
        bar.addWidget(import_button)
        bar.addWidget(paste_button)
        layout.addLayout(bar)

        parts = build_data_grid(self)
        self._parts = parts
        self.table = parts.table
        self.header = parts.header
        self.model = parts.model
        self.table.customContextMenuRequested.connect(self._show_grid_menu)
        self.table.paste_requested.connect(self._paste_from_clipboard)
        layout.addWidget(self.table, 1)

        import_button.clicked.connect(self._import)
        paste_button.clicked.connect(self._paste_sample)
        self.separator_combo.currentTextChanged.connect(self._on_separator_changed)

    # -- grid plumbing ---------------------------------------------------
    def _idl_stub(self) -> dict:
        """Column layout only — the wizard has no parameter IDL at this step."""
        return {
            "data_columns": self._sample_columns,
            "data_columns_dynamic": self._sample_dynamic,
        }

    def _set_error(self, message: str) -> None:
        """Surface an import problem where the column summary lives."""
        self.column_info.setText(message)
        self.column_info.setProperty("invalid", True)
        self.column_info.style().unpolish(self.column_info)
        self.column_info.style().polish(self.column_info)

    def _on_separator_changed(self, _separator: str) -> None:
        # The grid parses whatever it is handed; the separator now only shapes
        # the hint text, because the pill strip already names the columns.
        self.column_info.setProperty("invalid", False)
        self.column_info.style().unpolish(self.column_info)
        self.column_info.style().polish(self.column_info)

    def _paste_from_clipboard(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            self.set_sample_text(text)

    def _show_grid_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction(tr("table.paste_tsv"), self._paste_from_clipboard)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def showEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().showEvent(event)
        # Same reason as the workbench grid: the viewport has no width until
        # the page is on screen, so columns fitted while hidden fall back to
        # their default and leave a scroll bar behind.
        layout_grid_columns(self._parts)

    @staticmethod
    def _read_separator(suffix: str, selected: str) -> str:
        if suffix == ".csv":
            return ","
        if suffix == ".tsv":
            return "\t"
        return {"TAB": "\t", "SPACE": " ", "COMMA": ","}[selected]

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("fd.import_data"), "", tr("fd.filter_table"))
        if not path:
            return
        sep = self._read_separator(Path(path).suffix.lower(), self.separator_combo.currentText())
        try:
            frame = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False, engine="python")
        except Exception as exc:  # noqa: BLE001
            self._set_error(tr("wizard.read_failed", exc))
            return
        joiner = self._sep_char
        if any(joiner in str(v) for v in frame.astype(str).to_numpy().flat):
            self._set_error(tr("wizard.sep_conflict", joiner))
            return
        rows = [[str(v) for v in record] for record in frame.itertuples(index=False, name=None)]
        self._load_rows(rows)

    def _load_rows(self, rows: list[list[str]]) -> None:
        """Hand a block of rows to the grid and refit the columns.

        Column-count validation was entirely missing here — the wizard could
        export a template with an illegal ``col_3``/``col_0`` header while the
        step-4 preview looked fine (code review P0-3).  Gate the block with the
        same criteria the workbench uses before touching the model.
        """
        if not rows:
            return
        expected = len(self._sample_columns)
        widths = {len(r) for r in rows}
        received = len(rows[0])
        ragged = len(widths) > 1
        fits = columns_acceptable(received, self._sample_columns, self._sample_dynamic)
        if not self._sample_columns or ragged or not fits:
            self._set_error(
                tr("table.paste_col_mismatch", expected, min(widths) if ragged else received)
            )
            return
        self.model.set_idl(self._idl_stub())
        self.model.apply_rows(rows)
        layout_grid_columns(self._parts)
        self.column_info.setProperty("invalid", False)
        self.column_info.style().unpolish(self.column_info)
        self.column_info.style().polish(self.column_info)

    @property
    def _sep_char(self) -> str:
        return {"TAB": "\t", "SPACE": " ", "COMMA": ","}[self.separator_combo.currentText()]

    def set_sample_columns(self, data_columns: list[str], dynamic: str | None) -> None:
        """Update the colpill strip and remember the layout for sample generation."""
        self._sample_columns = list(data_columns)
        self._sample_dynamic = dynamic
        while self._pills_layout.count() > 1:
            item = self._pills_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        for column in data_columns:
            self._pills_layout.insertWidget(
                self._pills_layout.count() - 1, ColumnPill(column)
            )
        if dynamic:
            placeholder = QLabel(tr("wizard.dynamic_hint", dynamic))
            placeholder.setObjectName("dimLabel")
            self._pills_layout.insertWidget(
                self._pills_layout.count() - 1, placeholder
            )
        labels = "、".join(data_columns)
        self.column_info.setText(tr("wizard.column_info", labels))

    @staticmethod
    def generate_sample_text(
        columns: list[str], dynamic: str | None, sep: str
    ) -> str:
        """Build three sample rows shaped like *columns* (with a *dynamic* tail)."""
        # Two extra dynamic columns when the type is open-ended — enough to
        # show the pattern without making the sample unwieldy.
        n_cols = len(columns) + (2 if dynamic else 0)
        # Example *data* colours, not UI tokens — they are generated rows pasted
        # into the user's file, so they intentionally bypass theme palette.
        palettes = ("#ff0000", "#00aa55", "#3b5b92")
        rows = []
        for k in range(1, 4):
            row = []
            for i in range(n_cols):
                name = columns[i] if i < len(columns) else f"{dynamic.split('_')[0]}_{i}"
                lowered = name.lower()
                if i == 0:
                    row.append(f"sample_{k}")
                elif "color" in lowered or lowered == "colour":
                    row.append(palettes[k - 1])
                elif lowered in ("label", "text", "title", "content", "name"):
                    row.append(f"标签{k}")
                elif lowered in ("type", "shape", "style"):
                    row.append("circle" if k == 1 else ("square" if k == 2 else "star"))
                else:
                    row.append(str(k))
            rows.append(sep.join(row))
        return "\n".join(rows)

    def _paste_sample(self) -> None:
        # The page owns the sample so it is usable on its own (tests, or the
        # wizard not yet wired). The wizard additionally calls set_sample_text
        # from step 1 → step 2 if a custom shape is desired.
        if not self._sample_columns:
            return
        self.set_sample_text(
            self.generate_sample_text(
                self._sample_columns, self._sample_dynamic, self._sep_char
            )
        )

    def set_sample_text(self, text: str) -> None:
        """Load delimited text into the grid (the old text-box signature)."""
        self._load_rows(self.parse_text(text))

    def parse_text(self, text: str) -> list[list[str]]:
        """Split a delimited block into rows of cells."""
        rows: list[list[str]] = []
        sep = self._sep_char
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split() if sep == " " else line.split(sep)
            rows.append([part.strip() for part in parts])
        return rows

    def to_rows(self) -> list[dict[str, str]]:
        """Current grid contents as row dicts for the engine.

        The column names come from the model (which was validated on load), so
        the earlier ``data_columns`` / ``dynamic`` parameters were dead and were
        removed (code review P3-2).
        """
        if not self.model.columns:
            return []
        return self.model.to_rows()


# ---------------------------------------------------------------------------
# Step 3: inspector + summary
# ---------------------------------------------------------------------------


class ParamsPage(QWidget):
    """The parameter form on the left, a short summary panel on the right.

    Takes a :class:`ParameterForm`, not an ``InspectorPanel``: the wizard needs
    the fields, not the rail.  Embedding the whole rail pulled in the unit
    selector, the "no unit selected" guide and a second primary button that
    offered to open the wizard the user was already inside (UI review §03).
    """

    def __init__(self, inspector: ParameterForm, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        splitter = QSplitter()
        splitter.addWidget(inspector)
        summary = QWidget()
        summary.setObjectName("paramsSummary")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        summary_layout.setSpacing(SPACE_3)
        title = QLabel(tr("wizard.params_summary_title"))
        title.setObjectName("paramsSummaryTitle")
        summary_layout.addWidget(title)
        body = QLabel(tr("wizard.params_summary_body"))
        body.setObjectName("dimLabel")
        body.setWordWrap(True)
        summary_layout.addWidget(body)
        summary_layout.addStretch(1)
        splitter.addWidget(summary)
        splitter.setSizes([600, 360])
        layout.addWidget(splitter)


# ---------------------------------------------------------------------------
# TemplateWizard — wires the steps + QStackedWidget + foot buttons
# ---------------------------------------------------------------------------


class TemplateWizard(QDialog):
    def __init__(self, parent=None, initial_type: str | None = None,
                 project_name: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("wizard.title"))
        self.resize(1000, 660)
        self.type_name: str | None = None
        self.idl: dict | None = None
        self._reached = 0
        # TEMPLATE_NAME for the exported file — kept identical to the workbench
        # export path so the two never disagree (code review P2-5).
        self._project_name = project_name
        # Inject the IDL defaults into the parameter form only the first time
        # the step is entered; re-entering it (back from preview) must not
        # wipe what the user already configured (code review P2-2).
        self._params_ready = False
        # Set on a successful export so the host window can add the result to
        # the project instead of making the user re-import it (code review P2-3).
        self.result_spec = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.steps = WizardSteps()
        self.steps.setFixedWidth(212)
        body.addWidget(self.steps)

        self.pages = QStackedWidget()
        self.type_page = TypeGridPage()
        self.data_page = DataPage()
        self.inspector = ParameterForm()
        self.params_page = ParamsPage(self.inspector)
        self.preview = QTextEdit()
        self.preview.setObjectName("wizardPreview")
        mono = QFont()
        mono.setFamilies(list(MONO_FAMILIES))
        mono.setPixelSize(FONT_SIZE_MONO)
        self.preview.setFont(mono)
        self.preview.setReadOnly(True)
        for widget in (self.type_page, self.data_page, self.params_page, self.preview):
            self.pages.addWidget(widget)
        body.addWidget(self.pages, 1)
        layout.addLayout(body)

        self.error_label = QLabel("")
        self.error_label.setObjectName("inlineError")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.steps.step_requested.connect(self._goto)
        self.pages.currentChanged.connect(lambda _: self._sync_rail())

        self.back_button = QPushButton(icon("chevron-left", 14), tr("wizard.back"))
        self.next_button = QPushButton(tr("wizard.next"))
        self.next_button.setObjectName("primary")
        self.export_button = QPushButton(icon("file-output", 14), tr("wizard.export"))
        self.export_button.setObjectName("primary")
        self.export_button.setVisible(False)

        foot = QHBoxLayout()
        foot.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_3)
        foot.setSpacing(SPACE_3)
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("dimLabel")
        foot.addWidget(self.hint_label)
        foot.addStretch(1)
        foot.addWidget(self.back_button)
        foot.addWidget(self.next_button)
        foot.addWidget(self.export_button)
        layout.addLayout(foot)

        self.back_button.clicked.connect(self._go_back)
        self.next_button.clicked.connect(self._go_next)
        self.export_button.clicked.connect(self._export)
        self._sync_rail()

        if initial_type:
            self.type_page.select_type(initial_type)
            self._goto(0)

    # -- flow -------------------------------------------------------------
    def _goto(self, page: int) -> None:
        if page == PAGE_TYPE and self.type_page.selected_type() is None:
            self.hint_label.setText(tr("wizard.hint_select"))
            return
        if page >= PAGE_DATA and self.type_name is None:
            self.hint_label.setText(tr("wizard.hint_select"))
            self.pages.setCurrentIndex(PAGE_TYPE)
            return
        self.pages.setCurrentIndex(page)
        self._reached = max(self._reached, page)
        self._sync_rail()

    def _sync_rail(self) -> None:
        self.steps.sync(self.pages.currentIndex(), self._reached)
        page = self.pages.currentIndex()
        self.back_button.setEnabled(page > PAGE_TYPE)
        is_last = page == PAGE_PREVIEW
        self.next_button.setVisible(page != PAGE_PREVIEW)
        self.export_button.setVisible(is_last)
        if page == PAGE_TYPE:
            self.hint_label.setText(
                tr("wizard.hint_select") if self.type_page.selected_type() is None else ""
            )
        elif page == PAGE_DATA:
            self.hint_label.setText("")
        elif page == PAGE_PARAMS:
            self.hint_label.setText(tr("wizard.params_hint"))
        else:
            self.hint_label.setText("")

    def _go_back(self) -> None:
        current = self.pages.currentIndex()
        if current > PAGE_TYPE:
            self.pages.setCurrentIndex(current - 1)

    def _go_next(self) -> None:
        current = self.pages.currentIndex()
        if current == PAGE_TYPE:
            self.type_name = self.type_page.selected_type()
            if not self.type_name:
                self.hint_label.setText(tr("wizard.hint_select"))
                return
            self.hint_label.setText("")
            self.idl = build_form_idl(self.type_name)
            self.data_page.set_sample_columns(
                self.idl["data_columns"], self.idl.get("data_columns_dynamic")
            )
            self._goto(PAGE_DATA)
        elif current == PAGE_DATA:
            if not self._params_ready:
                self.inspector.set_idl(self.idl, defaults_for_idl(self.idl))
                self._params_ready = True
            else:
                # Re-entering the parameter step must not discard edits the user
                # already made — rebuild only preserves the current values
                # (code review P2-2).
                self.inspector.set_idl(self.idl, self.inspector.values())
            self._goto(PAGE_PARAMS)
        elif current == PAGE_PARAMS:
            self._refresh_preview()
            self._goto(PAGE_PREVIEW)

    def select_type(self, type_name: str) -> bool:
        """Preselect a type and commit it to the wizard (used by ⌘K / tests)."""
        if not self.type_page.select_type(type_name):
            return False
        if self.type_name is None:
            self.type_name = type_name
            self.idl = build_form_idl(type_name)
            self.data_page.set_sample_columns(
                self.idl["data_columns"], self.idl.get("data_columns_dynamic")
            )
        return True

    # -- unit kwargs / preview / export ---------------------------------------
    def _unit_kwargs(self) -> dict:
        values = self.inspector.values()
        extras = values.pop("__extra_params__", {})
        label = str(values.pop("DATASET_LABEL", "") or "")
        color = str(values.pop("COLOR", "") or "#dd4477")
        params = {k: v for k, v in values.items() if not k.startswith("LEGEND_") and not k.startswith("__") and v != ""}
        legend = {k: str(v) for k, v in values.items() if k.startswith("LEGEND_") and v != ""}
        params.update({k: v for k, v in extras.items() if str(v) != ""})
        return {
            "type_name": self.type_name,
            "label": label,
            "color": color,
            "separator": self.data_page.separator_combo.currentText(),
            "columns": self._last_columns(),
            "data_rows": self.data_page.to_rows(),
            "parameters": params,
            "legend": legend,
            "template_name": self._project_name,
        }

    def _last_columns(self) -> list[str]:
        rows = self.data_page.to_rows()
        if not rows:
            return self.idl["data_columns"]
        seen: list[str] = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.append(key)
        return seen

    def _preview_blocked(self, spec) -> bool:
        """Last gate before generation: no synthesised ``col_N`` headers.

        A non-dynamic type must carry exactly its IDL column names; a ``col_``
        header can only mean the data step let a mis-shaped block through —
        surface it rather than export an iTOL-invalid file (code review P0-3).
        """
        if self.idl.get("data_columns_dynamic"):
            return False
        if any(c.startswith("col_") for c in spec.columns):
            self.error_label.setText(tr("wizard.bad_columns"))
            self.error_label.show()
            return True
        self.error_label.hide()
        return False

    def _refresh_preview(self) -> None:
        from ..adapter.generator_bridge import UnitSpec

        spec = UnitSpec(**self._unit_kwargs())
        if self._preview_blocked(spec):
            return
        try:
            self.preview.setPlainText(generate_template_text(spec))
        except Exception as exc:  # noqa: BLE001
            self.preview.setPlainText(tr("preview.generate_failed", exc))

    def _export(self) -> None:
        from ..adapter.generator_bridge import UnitSpec
        from ..paths import writable_target

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("wizard.export_title"),
            f"{self.type_name}.txt",
            tr("fd.filter_template"),
        )
        if not path:
            return
        target = writable_target(path)
        if target is None:
            self.error_label.setText(tr("wizard.bad_path"))
            self.error_label.show()
            return
        # The write is synchronous — a double-click must not fire it twice.
        self.export_button.setEnabled(False)
        spec = UnitSpec(**self._unit_kwargs())
        if self._preview_blocked(spec):
            self.export_button.setEnabled(True)
            return
        try:
            export_template_file(spec, target)
        except Exception as exc:  # noqa: BLE001
            # Reported inline — a modal would interrupt the review step.
            self.error_label.setText(tr("wizard.export_failed_msg", exc))
            self.error_label.show()
            self.export_button.setEnabled(True)
            return
        # Hand the produced spec to the host so it can be added to the project
        # without the user re-importing the file they just generated (P2-3).
        self.result_spec = spec
        self.accept()

    # -- keyboard shortcuts -----------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt API)
        if event.matches(QKeySequence.StandardKey.Cancel):
            self.reject()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.next_button.isVisible():
            self._go_next()
            event.accept()
            return
        super().keyPressEvent(event)
