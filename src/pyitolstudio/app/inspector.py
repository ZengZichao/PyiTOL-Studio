"""Parameter inspector: a searchable, grouped, collapsible form rendered from
the declarative IDL (FR-4, design book §5.1).

Layout, top to bottom:

* header — type icon + unit name + type badge + ``重置为默认`` + ``更多``
* search box — filters fields by label or parameter key
* body — one collapsible container per IDL group (基本信息 / 数据映射 /
  外观 / 图例), the first two expanded by default
* footer — pinned validation banner + the ``生成模板`` primary button

Every control is built from the IDL, so adding a template type to the engine
still needs zero GUI code.
"""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..icons import icon, icon_pixmap
from ..theme import (
    CONTROL_HEIGHT,
    ICON_BUTTON,
    RADIUS_S,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    SPACE_7,
)
from ..theme_mode import theme_color

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

_ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

# Swatch beside a colour input.  28px matched the input height and read as a
# block welded to the field; 20px reads as an adornment inside it (0.5.0).
COLOUR_SWATCH = 20

# Fallback for a colour field whose value is unset/garbage (the engine's own
# default for COLOR); data, not a UI token.
_FALLBACK_COLOR = "#dd4477"

_BANNER_STATES = ("ok", "warn", "muted")

# UI-only preference: compact field density (design review P2#7).
_COMPACT_KEY = "ui/inspector_compact"

# Inspector width (px) at which fields flow into two columns (P2#7).
_TWO_COL_WIDTH = 360


class ColorSwatch(QFrame):
    """Colour preview that doubles as the picker trigger.

    The fill is painted in ``paintEvent`` rather than pushed through a
    ``setStyleSheet`` on every keystroke: the old stylesheet path re-polished
    the whole control subtree on each ``textChanged`` (UI review P2-6).  QSS
    still owns the border / corner radius; we only paint the colour inside it.
    """

    clicked = Signal()

    def __init__(self, value: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("colorSwatch")
        self.setFixedSize(COLOUR_SWATCH, COLOUR_SWATCH)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fill = QColor(0, 0, 0, 0)
        self.set_value(value)

    def set_value(self, value: str) -> None:
        # The swatch paints *data* (the user's hex), not a UI token.
        self._fill = QColor(value) if _HEX.match(value or "") else QColor(0, 0, 0, 0)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().paintEvent(event)  # QSS border + corner radius
        if not self._fill.isValid() or self._fill.alpha() == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, RADIUS_S, RADIUS_S)
        painter.fillPath(path, self._fill)
        painter.end()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ColorPicker(QWidget):
    """Swatch + ``#hex`` field (design book §5.1)."""

    changed = Signal(str)

    def __init__(self, initial: str = "", parent=None) -> None:
        super().__init__(parent)
        start = initial or _FALLBACK_COLOR
        self.swatch = ColorSwatch(start)
        self.edit = QLineEdit(start)
        self.edit.setObjectName("monoInput")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_3)
        layout.addWidget(self.swatch)
        layout.addWidget(self.edit, 1)
        self.swatch.clicked.connect(self._pick)
        self.edit.textChanged.connect(self._on_text)

    def _on_text(self, text: str) -> None:
        self.swatch.set_value(text.strip())
        self.changed.emit(text)

    def _pick(self) -> None:
        from PySide6.QtGui import QColor

        current = QColor(self.edit.text()) if _HEX.match(self.edit.text() or "") else QColor(_FALLBACK_COLOR)
        color = QColorDialog.getColor(current, self, tr("color.pick"))
        if color.isValid():
            self.edit.setText(color.name())

    def value(self) -> str:
        return self.edit.text().strip()

    def set_value(self, value: Any) -> None:
        self.edit.setText(str(value))


class ListEditor(QWidget):
    """Growable token editor for ``color_list`` / ``text_list`` parameters.

    The IDL marks 13 parameters (``FIELD_COLORS`` / ``LEGEND_LABELS`` …) with
    list semantics, but ``_make_widget`` had no branch for them, so they
    silently fell back to a bare mono text box — the user typed ``#ff0000
    #00ff00`` with no swatch and no way to tell a wrong digit (UI review P2-9).
    This gives them a real editor: one add/remove-able token per row, colour
    tokens through the same ``ColorPicker`` the single-value ``color`` field
    uses, and a canonical space-separated serialisation matching iTOL's format
    and the engine's ``_split_list``.
    """

    changed = Signal()

    def __init__(self, kind: str, value: Any = "", parent=None) -> None:
        super().__init__(parent)
        if kind not in ("color_list", "text_list"):
            raise ValueError(f"ListEditor kind must be color_list/text_list, got {kind!r}")
        self._kind = kind
        self._rows: list[tuple[QWidget, QWidget]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(SPACE_2)
        self._host = QWidget()
        self._host_layout = QVBoxLayout(self._host)
        self._host_layout.setContentsMargins(0, 0, 0, 0)
        self._host_layout.setSpacing(SPACE_2)
        outer.addWidget(self._host)

        add_button = QPushButton(icon("plus", 13), tr("inspector.list_add"))
        add_button.setObjectName("smallButton")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.setAccessibleName(tr("inspector.list_add"))
        add_button.clicked.connect(lambda _checked=False: self._append(""))
        outer.addWidget(add_button)

        self._split_and_build(str(value or ""))

    # -- (de)serialisation ------------------------------------------------
    @staticmethod
    def _split(text: str) -> list[str]:
        return [tok for tok in text.split() if tok != ""]

    def value(self) -> str:
        return " ".join(
            (editor.value() if isinstance(editor, ColorPicker) else editor.text().strip())
            for _host_row, editor in self._rows
            if (editor.value() if isinstance(editor, ColorPicker) else editor.text().strip())
        )

    def set_value(self, value: Any) -> None:
        self._split_and_build(str(value or ""))
        self.changed.emit()

    # -- build / mutate ---------------------------------------------------
    def _split_and_build(self, text: str) -> None:
        self._clear_rows()
        tokens = self._split(text) or [""]
        for token in tokens:
            self._append(token)

    def _clear_rows(self) -> None:
        for row, _editor in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows = []

    def _append(self, token: str) -> None:
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(SPACE_2)
        if self._kind == "color_list":
            editor: QWidget = ColorPicker(token)
            editor.changed.connect(lambda _t: self.changed.emit())
        else:
            editor = QLineEdit(token)
            editor.setObjectName("monoInput")
            editor.textChanged.connect(lambda _t: self.changed.emit())
        line.addWidget(editor, 1)
        remove = QToolButton()
        remove.setObjectName("iconButton")
        remove.setFixedSize(ICON_BUTTON, ICON_BUTTON)
        remove.setIcon(icon("trash", 13, theme_color("text_tertiary")))
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.setAccessibleName(tr("inspector.list_remove"))
        remove.clicked.connect(lambda _checked=False, r=row: self._remove_row(r))
        line.addWidget(remove)
        self._host_layout.addWidget(row)
        self._rows.append((row, editor))
        self.changed.emit()

    def _remove_row(self, row: QWidget) -> None:
        self._rows = [entry for entry in self._rows if entry[0] is not row]
        row.setParent(None)
        row.deleteLater()
        self.changed.emit()

    def retheme_ui(self) -> None:
        for row, _editor in self._rows:
            button = row.findChild(QToolButton)
            if button is not None:
                button.setIcon(icon("trash", 13, theme_color("text_tertiary")))


class LinkLabel(QLabel):
    """Small underlined text-link control.

    A QLabel hugs its text, so the design's ``text-decoration: underline``
    renders exactly under the two characters; a QPushButton keeps the native
    style's minimum width and would underline the whole empty rect.
    """

    clicked = Signal()

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class GroupHeader(QWidget):
    """Custom fold header: title + parameter count + chevron."""

    clicked = Signal()

    def __init__(self, title: str, count: int, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("groupHeader")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title = QLabel(title)
        self.title.setObjectName("groupTitle")
        self.count = QLabel(str(count))
        self.count.setObjectName("groupCount")
        self.chevron = QLabel()
        self._expanded = True
        row = QHBoxLayout(self)
        row.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        row.setSpacing(SPACE_3)
        row.addWidget(self.title)
        row.addStretch(1)
        row.addWidget(self.count)
        row.addWidget(self.chevron)

    def set_expanded(self, expanded: bool) -> None:
        name = "chevron-down" if expanded else "chevron-right"
        self.chevron.setPixmap(icon_pixmap(name, 12, theme_color("text_tertiary")))
        self._expanded = expanded

    def retheme_ui(self) -> None:
        self.set_expanded(self._expanded)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class CollapsibleSection(QWidget):
    """One IDL group: fold header + body holding the field rows.

    The body is a ``QGridLayout`` so ``set_columns`` can flow the same field
    widgets into one or two columns without rebuilding them (density switch).
    Folding animates the body height over 140 ms (design review P2 — "分组折叠"
    micro-interaction), matching the Instrument tone: quick, quiet, no bounce.
    """

    # Qt's default maximum height — reset target after an expand animation so
    # the layout can size the body freely again.
    _MAX_H = 16777215

    def __init__(self, title: str, count: int, expanded: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("groupSection")
        self._expanded = expanded
        self._body_anim: QPropertyAnimation | None = None
        self.header = GroupHeader(title, count)
        self.header.clicked.connect(self.toggle)
        self.body = QWidget()
        self.body.setObjectName("groupBody")
        self.body_layout = QGridLayout(self.body)
        self.body_layout.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_4)
        self.body_layout.setHorizontalSpacing(SPACE_7)
        # 16px between fields: at 12px a two-line field (label + input) looked
        # like one block and the group read as a single smear (UI review §06).
        self.body_layout.setVerticalSpacing(SPACE_5)
        self._fields: list[QWidget] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.header)
        root.addWidget(self.body)
        self.set_expanded(expanded)

    @property
    def expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self.header.set_expanded(expanded)
        if not animate or not self.isVisible():
            # Not on screen yet (construction) or a fast filter pass — jump.
            self.body.setVisible(expanded)
            self.body.setMaximumHeight(self._MAX_H)
            return
        self._animate_body(expanded)

    def _animate_body(self, expand: bool) -> None:
        if self._body_anim is not None:
            self._body_anim.stop()
        body = self.body
        anim = QPropertyAnimation(body, b"maximumHeight", self)
        anim.setDuration(140)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if expand:
            body.setVisible(True)
            anim.setStartValue(0)
            anim.setEndValue(body.sizeHint().height())
            anim.finished.connect(lambda: body.setMaximumHeight(self._MAX_H))
        else:
            anim.setStartValue(body.height() or body.sizeHint().height())
            anim.setEndValue(0)
            anim.finished.connect(lambda: body.setVisible(False))
        self._body_anim = anim
        anim.start()

    def add_field(self, widget: QWidget) -> None:
        """Append a field row and place it in the current column flow."""
        self._fields.append(widget)
        self.body_layout.addWidget(widget, len(self._fields) - 1, 0)

    def set_columns(self, cols: int) -> None:
        """Re-flow the (already present) field widgets into *cols* columns."""
        cols = max(1, cols)
        for widget in self._fields:
            self.body_layout.removeWidget(widget)
        for i, widget in enumerate(self._fields):
            self.body_layout.addWidget(widget, i // cols, i % cols)


class ValidationBanner(QFrame):
    """Inline validation strip: accent_link when valid, warn when IDs are missing."""

    _ICONS = {
        "ok": ("circle-check", "accent_link"),
        "warn": ("triangle-alert", "warn"),
        "muted": ("info", "text_tertiary"),
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("validationBanner")
        self.icon_label = QLabel()
        self.label = QLabel()
        self.label.setWordWrap(True)
        row = QHBoxLayout(self)
        row.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        row.setSpacing(SPACE_3)
        row.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self.label, 1)
        self.set_state("muted", tr("inspector.banner_unchecked"))

    def set_state(self, state: str, message: str) -> None:
        state = state if state in _BANNER_STATES else "muted"
        self._state = state
        self._message = message
        icon_name, token = self._ICONS[state]
        self.icon_label.setPixmap(icon_pixmap(icon_name, 14, theme_color(token)))
        self.label.setText(message)
        self.setProperty("state", state)
        # Re-polish so the [state="…"] QSS rule takes effect.
        self.style().unpolish(self)
        self.style().polish(self)

    def retheme_ui(self) -> None:
        self.set_state(self._state, self._message)


class ParameterForm(QWidget):
    """The parameter form itself: groups, fields, filtering, validation.

    Split out of :class:`InspectorPanel` in 0.5.0.  The wizard's parameter step
    used to embed a whole ``InspectorPanel``, which dragged the unit selector,
    the search box, the "no unit selected" guide and the pinned *Generate*
    button into a dialog where none of them apply — the user is already inside
    the wizard, and the wizard owns the primary action on that page.  A dialog
    that offers to start a wizard from inside itself is the kind of detail that
    makes an otherwise careful UI feel unfinished.

    So: everything that belongs to the form lives here, everything that
    belongs to the rail lives in the subclass, and the wizard instantiates
    this class directly with no chrome at all.
    """

    values_changed = Signal()

    #: Whether an empty IDL renders the "no unit selected" guide.  Off for the
    #: wizard, which never reaches that state and has no unit to speak of.
    shows_empty_state = False

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("paramForm")
        self._idl: dict[str, Any] | None = None
        self._widgets: dict[str, QWidget] = {}
        # (section, default_expanded, [(field, row, searchable text), …])
        self._sections: list[tuple[CollapsibleSection, bool, list[tuple[dict[str, Any], QWidget, str]]]] = []
        # Density preference (design review P2#7); UI-only, so it lives in
        # QSettings next to theme/language, never in the .pyitolproj schema.
        self._compact = bool(QSettings().value(_COMPACT_KEY, False, type=bool))
        self._field_errors: dict[str, str] = {}
        # Cache of the last column count applied to the sections (UI P2-5):
        # ``_reflow_columns`` runs on every resizeEvent, and re-adding every
        # field even when the count is unchanged churns the whole layout.
        self._last_cols: int | None = None
        # key -> (reset button, field) for the per-field "back to default" icon,
        # which only appears once a value differs from its default.
        self._reset_buttons: dict[str, tuple[QToolButton, dict[str, Any]]] = {}

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("inspectorScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._body_host = QWidget()
        self._body = QVBoxLayout(self._body_host)
        self._body.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_4)
        self._body.setSpacing(SPACE_4)
        self._scroll.setWidget(self._body_host)
        self._root.addWidget(self._scroll, 1)

        self.set_idl(None, None)
        # Parameter-level validation re-runs on every real edit (blocked during
        # rebuilds, so a set_idl round-trip never double-counts).
        self.values_changed.connect(self._update_all_field_errors)

    # -- hooks the subclass fills in ------------------------------------
    def _on_idl_changed(self, has_idl: bool) -> None:
        """Called after every rebuild; the rail updates its chrome here."""

    # -- public API -----------------------------------------------------
    def set_idl(self, idl: dict[str, Any] | None, values: dict[str, Any] | None = None) -> None:
        """(Re)build the form for a template type IDL."""
        # Constructing widgets emits their change signals (combo addItems,
        # spin box setValue, …); block them so a rebuild does not spam
        # ``values_changed`` and regenerate the preview once per control.
        self.blockSignals(True)
        try:
            self._set_idl_inner(idl, values)
        finally:
            self.blockSignals(False)
        # The rebuild cleared _field_errors / _reset_buttons, and blocking the
        # signals also suppressed the only subscriber that recomputes them.
        # Recompute once now, or a freshly loaded unit shows no "N parameters
        # need fixing" banner and no per-field reset icons (UI P0-2 / code P1-4).
        if self._idl is not None:
            self._update_all_field_errors()

    def clear(self) -> None:
        self._set_idl_inner(None, None)

    # -- group / fold helpers -------------------------------------------
    def expand_all(self) -> None:
        for section, _, _ in self._sections:
            section.set_expanded(True)

    def collapse_all(self) -> None:
        for section, _, _ in self._sections:
            section.set_expanded(False)

    def copy_values(self) -> None:
        """Copy the current key/value pairs as TSV."""
        rows = [f"{key}\t{value}" for key, value in self.values().items() if not key.startswith("__")]
        if rows:
            QApplication.clipboard().setText("\n".join(rows))

    def reset_to_defaults(self) -> None:
        """Restore every *parameter* to its IDL default.

        This is a parameter reset, not a unit reset: the unit identity
        (``DATASET_LABEL`` / ``COLOR``) and any learner-discovered out-of-catalog
        parameters (``__extra_params__``, kept per plan R7) are preserved, so a
        single click cannot silently drop data or rewrite the rail name/colour
        (code review P1-3).
        """
        if self._idl is None:
            return
        current = self.values()
        defaults = {f["key"]: f.get("default", "") for f in self._idl["fields"]}
        for identity_key in ("DATASET_LABEL", "COLOR"):
            if identity_key in defaults and current.get(identity_key, "") != "":
                defaults[identity_key] = current[identity_key]
        defaults["__extra_params__"] = current.get("__extra_params__", {})
        self.set_idl(self._idl, defaults)
        self.values_changed.emit()

    # -- density switch (design review P2#7) -----------------------------
    def set_compact(self, compact: bool) -> None:
        """Apply the compact-density preference and rebuild the form."""
        self._compact = compact
        if self._idl is not None:
            values = self.values()
            self.set_idl(self._idl, values)

    def _columns_for_width(self) -> int:
        """Two columns once the inspector is wide enough (P2#7)."""
        return 2 if self.width() >= _TWO_COL_WIDTH else 1

    def _reflow_columns(self) -> None:
        """Re-flow existing sections after a resize crossed the threshold."""
        cols = 1 if self._compact else self._columns_for_width()
        if cols == self._last_cols:
            return  # column count unchanged — re-adding every field is churn
        self._last_cols = cols
        for section, _default_expanded, _rows in self._sections:
            section.set_columns(cols)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self._reflow_columns()

    @staticmethod
    def _range_text(minimum: Any, maximum: Any) -> str:
        """Human range for a validation message — never leaks ``None``.

        A one-sided bound renders only the bound that exists (``≤ 100`` /
        ``≥ 1``); the old code printed ``"None–100"`` (UI review P1-3).
        """
        if minimum is None:
            return f"≤ {maximum}"
        if maximum is None:
            return f"≥ {minimum}"
        return f"{minimum}–{maximum}"

    # -- parameter-level validation (design review P2#12) -----------------
    @staticmethod
    def _validate_field(field: dict[str, Any], value: str) -> str:
        """Return an error message for one field value ("" when valid)."""
        if field.get("required") and not value:
            return tr("inspector.field_required", field["key"])
        widget_kind = field["widget"]
        if widget_kind in ("int", "float"):
            if not value:
                return ""  # optional and empty — nothing to check
            try:
                number = float(value)
            except (TypeError, ValueError):
                return tr("inspector.field_number", field["key"], value)
            minimum = field.get("minimum")
            maximum = field.get("maximum")
            if minimum is not None and number < float(minimum):
                return tr("inspector.field_range", field["key"],
                          ParameterForm._range_text(minimum, maximum))
            if maximum is not None and number > float(maximum):
                return tr("inspector.field_range", field["key"],
                          ParameterForm._range_text(minimum, maximum))
        if widget_kind == "color" and value and not _HEX.match(value):
            return tr("inspector.field_color", field["key"])
        if widget_kind == "color_list" and value:
            bad = [tok for tok in value.split() if tok and not _HEX.match(tok)]
            if bad:
                return tr("inspector.field_color_list", field["key"], " ".join(bad))
        return ""

    def _set_field_error(self, key: str, message: str) -> None:
        """Flip a field row's label to warn (and back) without a rebuild."""
        widget = self._widgets.get(key)
        label = widget.findChild(QLabel, "fieldLabel") if widget is not None else None
        if label is None:
            return
        if message:
            label.setProperty("invalid", True)
            label.setToolTip(message)
        else:
            label.setProperty("invalid", False)
            label.setToolTip("")
        label.style().unpolish(label)
        label.style().polish(label)

    def field_error_count(self) -> int:
        """How many parameters currently fail validation (P2#12)."""
        return sum(1 for message in self._field_errors.values() if message)

    def _update_all_field_errors(self) -> None:
        """Re-validate every field and flip inline labels to warn where
        a value breaks its constraints.  The footer banner is owned by the
        main window (it also knows tree matching), so this only records the
        verdicts; ``field_error_count`` feeds the banner aggregation."""
        if self._idl is None:
            return
        vals = self.values()  # once — values() walks every widget
        for field in self._idl["fields"]:
            key = field["key"]
            value = str(vals.get(key, ""))
            error = self._validate_field(field, value)
            self._field_errors[key] = error
            self._set_field_error(key, error)
        self._refresh_reset_buttons(vals)

    @staticmethod
    def _same_as_default(field: dict[str, Any], value: str) -> bool:
        """Whether *value* equals the field default.

        Numeric fields compare by value: a ``QDoubleSpinBox`` (decimals=3)
        reads back ``"10.000"`` for an IDL default of ``"10"``, so a plain
        string comparison would mark every float field "off default" and leave
        its reset icon permanently visible (UI review P0-2).
        """
        default = str(field.get("default", "") or "").strip()
        value = (value or "").strip()
        kind = field.get("widget")
        if kind in ("int", "float"):
            try:
                return float(value) == float(default)
            except (TypeError, ValueError):
                return value == default
        if kind == "bool":
            # values() yields "1"/"0"; the catalog default is JSON true/false.
            def _truthy(text: str) -> bool:
                return text.strip().lower() in ("1", "true", "yes", "on")
            return _truthy(value) == _truthy(default)
        return value == default

    def _refresh_reset_buttons(self, current: dict[str, Any] | None = None) -> None:
        '''Show each field's reset icon only where the value left its default.'''
        if not self._reset_buttons:
            return
        values = self.values() if current is None else current
        for key, (button, field) in self._reset_buttons.items():
            button.setVisible(
                not self._same_as_default(field, str(values.get(key, "") or ""))
            )

    # -- internals ------------------------------------------------------
    def _set_idl_inner(self, idl: dict[str, Any] | None, values: dict[str, Any] | None) -> None:
        self._idl = idl
        self._widgets = {}
        self._sections = []
        self._field_errors = {}
        self._reset_buttons = {}
        self._last_cols = None  # sections rebuilt; let the next reflow re-apply
        # QScrollArea takes ownership: setWidget() deletes the previous host,
        # so it must not be freed again here.
        self._body_host = QWidget()
        self._body = QVBoxLayout(self._body_host)
        self._body.setContentsMargins(SPACE_3, 0, SPACE_3, SPACE_4)
        self._body.setSpacing(SPACE_3)
        self._scroll.setWidget(self._body_host)

        if idl is None:
            if self.shows_empty_state:
                self._body.addWidget(self._build_empty_guide(), 1)
            self._on_idl_changed(False)
            return
        self._on_idl_changed(True)

        supplied = values or {}
        for group in idl.get("groups") or self._fallback_groups(idl):
            self._add_section(
                tr(group["label_key"]),
                group["fields"],
                bool(group.get("expanded")),
                supplied,
            )

        extras = supplied.get("__extra_params__") or {}
        if extras:
            extra_fields = [
                {"key": key, "label": key, "widget": "text", "default": "", "value": value}
                for key, value in extras.items()
            ]
            self._add_section(tr("inspector.extra_params"), extra_fields, True, {}, extra=True)

        self._body.addStretch(1)

    def retheme_ui(self) -> None:
        """Re-rasterise the form's baked-in icon pixmaps after a theme switch."""
        for section, _, _ in self._sections:
            section.header.retheme_ui()
        # Per-field reset icons bake text_tertiary at build time; without this
        # they keep the previous mode's colour after a switch (code P3-6).
        for reset, _field in self._reset_buttons.values():
            reset.setIcon(icon("rotate-ccw", 13, theme_color("text_tertiary")))
        # List editors carry their own baked delete-icon (UI P2-9).
        for widget in self._widgets.values():
            if isinstance(widget, ListEditor):
                widget.retheme_ui()

    def _add_section(
        self,
        title: str,
        fields: list[dict[str, Any]],
        expanded: bool,
        supplied: dict[str, Any],
        extra: bool = False,
    ) -> None:
        section = CollapsibleSection(title, len(fields), expanded)
        rows: list[tuple[dict[str, Any], QWidget, str]] = []
        for field in fields:
            if extra:
                row = self._build_extra_row(field["key"], field["value"])
                haystack = field["key"].lower()
            else:
                row = self._build_field_row(field, supplied.get(field["key"], field.get("default", "")))
                haystack = f"{field['key']} {field['label']}".lower()
            section.add_field(row)
            rows.append((field, row, haystack))
        section.set_columns(1 if self._compact else self._columns_for_width())
        self._body.addWidget(section)
        self._sections.append((section, expanded, rows))

    @staticmethod
    def _fallback_groups(idl: dict[str, Any]) -> list[dict[str, Any]]:
        """Group bucket for IDLs built before the ``groups`` key existed."""
        return [
            {
                "key": "all",
                "label_key": "inspector.group.appearance",
                "expanded": True,
                "fields": idl["fields"],
            }
        ]

    def _build_field_row(self, field: dict[str, Any], value: Any) -> QWidget:
        key = field["key"]
        widget = self._make_widget(field, value)
        self._widgets[key] = widget
        help_text = field.get("help", "")
        # The note used to own a line of its own under every field, which is
        # what turned the rail into a wall of grey captions.  It now rides in
        # the tooltip: same information, one hover away, no vertical cost and
        # no layout shift (UI review §06).
        note = self._note_for(field)
        tip = help_text or note
        if tip:
            widget.setToolTip(tip)

        row = QWidget()
        row.setObjectName("fieldRow")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)
        layout.addWidget(self._build_label_line(field, widget))
        layout.addWidget(widget)
        if tip:
            row.setToolTip(tip)
        return row

    def _build_label_line(self, field: dict[str, Any], control: QWidget) -> QWidget:
        """One line per field: the human label, plus an on-demand reset.

        Three things used to share this line — the Chinese label, the Latin
        parameter key, and a 10px underlined "默认" link — which made every
        field a four-storey stack inside a 280px rail and gave all of them
        equal visual weight.  The key is not lost: it moves into the tooltip
        and stays searchable.  The reset becomes a 24px icon button that shows
        up only once the value leaves its default, so an untouched field
        carries no affordance at all (UI review §06).
        """
        host = QWidget()
        line = QHBoxLayout(host)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(SPACE_2)
        name = QLabel(field["label"])
        name.setObjectName("fieldLabel")
        help_text = field.get("help", "")
        name.setToolTip(
            " · ".join(part for part in (field["key"], help_text) if part)
        )
        line.addWidget(name)
        line.addStretch(1)
        reset = QToolButton()
        reset.setObjectName("fieldReset")
        reset.setFixedSize(ICON_BUTTON, ICON_BUTTON)
        reset.setIcon(icon("rotate-ccw", 13, theme_color("text_tertiary")))
        reset.setToolTip(tr("inspector.field_default_tip", field["key"]))
        reset.setAccessibleName(tr("inspector.field_default_tip", field["key"]))
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(lambda _checked=False, f=field: self._reset_field(f))
        reset.setVisible(False)
        self._reset_buttons[field["key"]] = (reset, field)
        line.addWidget(reset)
        return host

    def _build_extra_row(self, key: str, value: Any) -> QWidget:
        row = QWidget()
        row.setObjectName("fieldRow")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)
        name = QLabel(key)
        name.setObjectName("fieldKey")
        layout.addWidget(name)
        widget = QLineEdit(str(value))
        widget.setObjectName("monoInput")
        widget.editingFinished.connect(self.values_changed.emit)
        self._widgets[f"__extra__:{key}"] = widget
        layout.addWidget(widget)
        return row

    @staticmethod
    def _note_for(field: dict[str, Any]) -> str:
        """Field note: curated hint, else "unit · min–max", else the help text."""
        if field.get("hint"):
            return str(field["hint"])
        unit = field.get("unit")
        span = field.get("range")
        if unit and span:
            return f"{tr(f'inspector.unit.{unit}')} · {span}"
        if span:
            return str(span)
        if unit:
            return tr(f"inspector.unit.{unit}")
        return str(field.get("help", ""))

    def _reset_field(self, field: dict[str, Any]) -> None:
        widget = self._widgets.get(field["key"])
        if widget is None:
            return
        self._set_widget_value(widget, field.get("default", ""))
        self.values_changed.emit()

    def _apply_filter(self, query: str) -> None:
        needle = query.strip().lower()
        for section, default_expanded, rows in self._sections:
            visible = 0
            for _field, row, haystack in rows:
                match = not needle or needle in haystack
                row.setVisible(match)
                visible += int(match)
            section.setVisible(visible > 0)
            # While filtering, unfold every group that has a match — a hit
            # inside a folded group would otherwise stay invisible.
            section.set_expanded(visible > 0 if needle else default_expanded)

    # -- widget factory --------------------------------------------------
    @staticmethod
    def _coerce_int(value: Any) -> int:
        """Best-effort int coercion; "2.0" style learner values stay 2
        instead of collapsing to 0."""
        text = str(value).strip()
        try:
            number = float(text)
        except (TypeError, ValueError):
            return 0
        return int(number)

    def _make_widget(self, field: dict[str, Any], value: Any) -> QWidget:
        widget_kind = field["widget"]
        if widget_kind == "color":
            control = ColorPicker(str(value or ""))
            control.changed.connect(lambda _text: self.values_changed.emit())
            return control
        if widget_kind == "bool":
            control = QCheckBox()
            control.setChecked(str(value) in ("1", "True", "true"))
            control.toggled.connect(lambda _on: self.values_changed.emit())
            return control
        if widget_kind == "choice":
            control = QComboBox()
            items = [str(i) for i in (field.get("choices") or [])]
            # A learned value outside the catalog choices must stay visible,
            # otherwise re-selecting the unit silently rewrites it.
            text = str(value)
            if text and text not in items:
                items.append(text)
            control.addItems(items)
            if text in items:
                control.setCurrentText(text)
            control.currentTextChanged.connect(lambda _text: self.values_changed.emit())
            return control
        if widget_kind == "int":
            control = QSpinBox()
            # A deliberately wide envelope: the catalog's own min/max is enforced
            # by _validate_field (red label + tooltip), NOT clamped here — so a
            # learned out-of-range value is shown, not silently rewritten to the
            # boundary (code review P1-4).
            control.setRange(-10**9, 10**9)
            control.setValue(self._coerce_int(value))
            control.valueChanged.connect(lambda _v: self.values_changed.emit())
            return control
        if widget_kind == "float":
            control = QDoubleSpinBox()
            control.setRange(-1e9, 1e9)  # wide; range check lives in _validate_field
            control.setDecimals(3)
            try:
                control.setValue(float(value))
            except (TypeError, ValueError):
                control.setValue(0.0)
            control.valueChanged.connect(lambda _v: self.values_changed.emit())
            return control
        if widget_kind in ("color_list", "text_list"):
            control = ListEditor(widget_kind, "" if value is None else str(value))
            control.changed.connect(self.values_changed.emit)
            return control
        control = QLineEdit("" if value is None else str(value))
        # Template text, key lists and paths are data — render them in mono.
        control.setObjectName("monoInput")
        control.editingFinished.connect(self.values_changed.emit)
        return control

    def _set_widget_value(self, widget: QWidget, value: Any) -> None:
        """Push a value back into a control without re-entering the factory."""
        if isinstance(widget, ColorPicker):
            widget.set_value(value)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(str(value) in ("1", "True", "true"))
        elif isinstance(widget, QComboBox):
            text = str(value)
            if text and text not in [widget.itemText(i) for i in range(widget.count())]:
                widget.addItem(text)
            widget.setCurrentText(text)
        elif isinstance(widget, QSpinBox):
            widget.setValue(self._coerce_int(value))
        elif isinstance(widget, QDoubleSpinBox):
            try:
                widget.setValue(float(value))
            except (TypeError, ValueError):
                widget.setValue(0.0)
        elif isinstance(widget, ListEditor):
            widget.set_value("" if value is None else str(value))
        elif hasattr(widget, "setText"):
            widget.setText("" if value is None else str(value))

    # -- value collection ------------------------------------------------
    def values(self) -> dict[str, Any]:
        """Collect current form values keyed by parameter name."""
        if self._idl is None:
            return {}
        collected: dict[str, Any] = {}
        extras: dict[str, str] = {}
        for key, widget in self._widgets.items():
            if key.startswith("__extra__:"):
                extras[key.split(":", 1)[1]] = widget.text().strip()
                continue
            if isinstance(widget, ColorPicker):
                collected[key] = widget.value()
            elif isinstance(widget, ListEditor):
                collected[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                collected[key] = "1" if widget.isChecked() else "0"
            elif isinstance(widget, QComboBox):
                collected[key] = widget.currentText().strip()
            else:
                collected[key] = widget.text().strip() if hasattr(widget, "text") else ""
        if extras:
            collected["__extra_params__"] = extras
        return collected


class InspectorPanel(ParameterForm):
    """The right-hand rail: the parameter form plus its chrome.

    The chrome is everything a standalone form does not need — the unit label
    and type badge, the search box, the "no unit selected" guide, and the
    pinned primary action.  Keeping the two apart is what lets the wizard show
    a parameter form without also showing a button that offers to open the
    wizard you are already in.
    """

    generate_requested = Signal()
    wizard_requested = Signal()
    collapse_requested = Signal()

    shows_empty_state = True

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("inspectorPanel")
        self._unit_label = ""
        self._type_name = ""
        self._collapsed = False

        # The form built its own root layout in __init__; the chrome slots in
        # around it (header and search above the scroll area, footer below).
        self._root.insertWidget(0, self._build_header())
        self._root.insertWidget(1, self._build_search())
        self._root.addWidget(self._build_footer())
        self.set_unit("", "")
        self._on_idl_changed(self._idl is not None)
        # Bake the collapse chevron now, not only on retheme — a standalone
        # InspectorPanel used to show an empty 24px button (UI P2-8).
        self.set_collapsed(self._collapsed)

    # -- construction ---------------------------------------------------
    def _build_header(self) -> QWidget:
        host = QWidget()
        host.setObjectName("inspectorHead")
        outer = QVBoxLayout(host)
        outer.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_3)
        outer.setSpacing(SPACE_2)

        top = QHBoxLayout()
        top.setSpacing(SPACE_3)
        self._type_icon = QLabel()
        self._name_label = QLabel("")
        self._name_label.setObjectName("unitName")
        self._reset_button = QToolButton()
        self._reset_button.setObjectName("iconButton")
        self._reset_button.setIcon(icon("rotate-ccw", 13, theme_color("text_tertiary")))
        self._reset_button.setToolTip(tr("inspector.reset_all"))
        self._reset_button.setAccessibleName(tr("inspector.reset_all"))
        self._reset_button.clicked.connect(self.reset_to_defaults)
        self._more_button = QToolButton()
        self._more_button.setObjectName("iconButton")
        self._more_button.setIcon(icon("ellipsis", 13, theme_color("text_tertiary")))
        self._more_button.setToolTip(tr("inspector.more"))
        self._more_button.setAccessibleName(tr("inspector.more"))
        self._more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._more_menu = QMenu(self._more_button)
        self._more_menu.addAction(tr("inspector.expand_all"), self.expand_all)
        self._more_menu.addAction(tr("inspector.collapse_all"), self.collapse_all)
        self._more_menu.addSeparator()
        self._more_menu.addAction(tr("inspector.copy_params"), self.copy_values)
        self._more_button.setMenu(self._more_menu)
        top.addWidget(self._type_icon)
        top.addWidget(self._name_label, 1)
        self._collapse_button = QToolButton()
        self._collapse_button.setObjectName("iconButton")
        self._collapse_button.setToolTip(tr("inspector.collapse_panel"))
        self._collapse_button.setAccessibleName(tr("inspector.collapse_panel"))
        self._collapse_button.clicked.connect(self.collapse_requested.emit)
        top.addWidget(self._collapse_button)
        self._compact_button = QToolButton()
        self._compact_button.setObjectName("iconButton")
        self._compact_button.setCheckable(True)
        self._compact_button.setChecked(self._compact)
        self._compact_button.setIcon(icon("rows-3", 13, theme_color("text_tertiary")))
        self._compact_button.setToolTip(tr("inspector.compact_tip"))
        self._compact_button.setAccessibleName(tr("inspector.compact_tip"))
        self._compact_button.clicked.connect(self.toggle_compact)
        top.addWidget(self._compact_button)
        top.addWidget(self._reset_button)
        top.addWidget(self._more_button)
        outer.addLayout(top)

        self._badge = QLabel("")
        self._badge.setObjectName("typeBadge")
        outer.addWidget(self._badge)
        return host

    def _build_search(self) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(SPACE_4, 0, SPACE_4, SPACE_3)
        self._search = QLineEdit()
        self._search.setObjectName("searchBox")
        self._search.setClearButtonEnabled(True)
        self._search.addAction(
            icon("search", 13, theme_color("text_tertiary")), QLineEdit.ActionPosition.LeadingPosition
        )
        self._search.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search)
        return host

    def _build_footer(self) -> QWidget:
        host = QWidget()
        host.setObjectName("inspectorFoot")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_4)
        layout.setSpacing(SPACE_3)
        self.banner = ValidationBanner()
        self.generate_button = QPushButton(icon("circle-check", 14, theme_color("on_accent")), tr("inspector.generate"))
        self.generate_button.setObjectName("primary")
        self.generate_button.setFixedHeight(CONTROL_HEIGHT + 6)
        self.generate_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.generate_button.setShortcut(QKeySequence("Ctrl+Return"))
        self.generate_button.clicked.connect(self.generate_requested.emit)
        layout.addWidget(self.banner)
        layout.addWidget(self.generate_button)
        return host

    def _build_empty_guide(self) -> QWidget:
        """Centered guide shown while no unit is selected (design review P1#4)."""
        host = QWidget()
        host.setObjectName("emptyState")
        stack = QVBoxLayout(host)
        stack.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stack.setSpacing(SPACE_3)
        title = QLabel(tr("inspector.empty_title"))
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(tr("inspector.empty_body"))
        body.setObjectName("emptyBody")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)
        cta = QPushButton(icon("wand", 14, theme_color("on_accent")), tr("inspector.empty_cta"))
        cta.setObjectName("emptyCta")
        cta.setCursor(Qt.CursorShape.PointingHandCursor)
        cta.clicked.connect(self.wizard_requested.emit)
        stack.addStretch(1)
        stack.addWidget(title)
        stack.addWidget(body)
        stack.addWidget(cta, 0, Qt.AlignmentFlag.AlignHCenter)
        stack.addStretch(2)
        return host

    # -- public API -----------------------------------------------------
    def set_unit(self, label: str, type_name: str) -> None:
        """Header context for the selected unit (called by the main window)."""
        self._unit_label = label or ""
        self._type_name = type_name or ""
        self._refresh_header()

    def set_validation(self, state: str, message: str = "") -> None:
        """Validation strip state: ``ok`` / ``warn`` / ``muted``."""
        self.banner.set_state(state, message)

    def set_collapsed(self, collapsed: bool) -> None:
        """Mirror the panel's visibility into the chevron affordance."""
        self._collapsed = collapsed
        self._collapse_button.setIcon(
            icon("panel-right-open" if collapsed else "panel-right-close", 13, theme_color("text_tertiary"))
        )
        self._collapse_button.setToolTip(
            tr("inspector.expand_panel") if collapsed else tr("inspector.collapse_panel")
        )

    def retranslate_ui(self) -> None:
        """Re-apply translatable labels after a locale switch."""
        self._collapse_button.setToolTip(
            tr("inspector.expand_panel") if self._collapsed else tr("inspector.collapse_panel")
        )
        self._reset_button.setToolTip(tr("inspector.reset_all"))
        self._more_button.setToolTip(tr("inspector.more"))
        actions = self._more_menu.actions()
        if len(actions) >= 4:
            actions[0].setText(tr("inspector.expand_all"))
            actions[1].setText(tr("inspector.collapse_all"))
            actions[3].setText(tr("inspector.copy_params"))
        self._search.setPlaceholderText(tr("inspector.search"))
        self.generate_button.setText(tr("inspector.generate"))
        self._refresh_header()
        # Rebuild the form so field labels and group titles pick up the locale.
        if self._idl is not None:
            values = self.values()
            self.set_idl(self._idl, values)

    # -- density switch (design review P2#7) -----------------------------
    def toggle_compact(self) -> None:
        """Flip the compact-density preference and rebuild the form."""
        compact = not self._compact
        QSettings().setValue(_COMPACT_KEY, compact)
        self._compact_button.setChecked(compact)
        self.set_compact(compact)

    # -- chrome upkeep ---------------------------------------------------
    def _on_idl_changed(self, has_idl: bool) -> None:
        # ParameterForm.__init__ calls set_idl() before this subclass has built
        # its chrome, so the hook has to tolerate a not-yet-constructed header.
        # The subclass calls it again once everything exists.
        if not hasattr(self, "_name_label"):
            return
        self._refresh_header()
        self._search.setEnabled(has_idl)
        self.generate_button.setEnabled(has_idl)
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)

    def _refresh_header(self) -> None:
        if not self._idl:
            self._name_label.setText(tr("inspector.no_unit"))
            self._type_icon.clear()
            self._badge.setText("")
            return
        self._type_icon.setPixmap(icon_pixmap("sliders-horizontal", 15, theme_color("accent")))
        self._name_label.setText(self._unit_label or self._idl["header"])
        self._badge.setText(f"{self._idl['header']} · {tr('inspector.param_count', len(self._idl['fields']))}")

    def retheme_ui(self) -> None:
        """Re-rasterise the chrome's baked-in icon pixmaps after a theme switch."""
        super().retheme_ui()
        self._reset_button.setIcon(icon("rotate-ccw", 13, theme_color("text_tertiary")))
        self._more_button.setIcon(icon("ellipsis", 13, theme_color("text_tertiary")))
        self._compact_button.setIcon(icon("rows-3", 13, theme_color("text_tertiary")))
        self.generate_button.setIcon(icon("circle-check", 14, theme_color("on_accent")))
        self.set_collapsed(self._collapsed)
        self.banner.retheme_ui()
        self._refresh_header()
        leading = self._search.actions()
        if leading:
            self._search.removeAction(leading[0])
            self._search.addAction(
                icon("search", 13, theme_color("text_tertiary")),
                QLineEdit.ActionPosition.LeadingPosition,
            )
