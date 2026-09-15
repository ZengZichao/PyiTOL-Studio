"""Single source of truth for "which theme mode is active".

The mode is derived from the platform appearance (``QStyleHints.colorScheme``),
which is also what ``app.main.apply_theme`` feeds to ``build_stylesheet``.
Keeping the resolution in one place matters because two other consumers need
it too: icons are rendered to pixmaps (a concrete colour, not a stylesheet
reference) and the preview highlighter holds ``QTextCharFormat`` colours.
Three independent copies of this check would drift.

``build_stylesheet(dark)`` stays a pure function of a boolean — this module
only decides what that boolean is.

QSS **and** palette
-------------------
Qt resolves a widget's appearance through two independent channels: the
stylesheet (what the QSS spells out) and the palette (the fallback a widget
consults for anything the stylesheet never mentioned).  Until 0.5.0 the app
set only the stylesheet, so with a light-appearance OS a dark-theme window
kept ``Window = #efefef``, ``Base = #ffffff`` and ``Text = #000000`` from the
system.  Every region the QSS did not paint — the remainder of a
self-painted header, a scroll area's viewport, a card's own background —
showed through as a light hole punched in a dark UI.  :func:`build_palette`
closes that channel from the same tokens, so both paths agree by construction.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette

from .theme import palette

# QColor cannot parse the CSS ``rgba(...)`` form the tokens use for
# translucent strokes and fills, so it needs translating.
_RGBA = re.compile(
    r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)"
)


# An explicit override, set by the app's 外观 menu or PYITOLSTUDIO_THEME.
# ``None`` means "follow the platform appearance".
_override: bool | None = None


def set_override(dark: bool | None) -> None:
    """Force a mode (``True``/``False``) or follow the OS again (``None``)."""
    global _override
    _override = dark


def override() -> bool | None:
    """The current forced mode, or ``None`` when following the platform."""
    return _override


def follows_system() -> bool:
    return _override is None


def current_dark() -> bool:
    """Whether the app should render dark.

    Honours the override first; otherwise follows the platform appearance and
    defaults to light when there is no application instance or the platform
    reports ``Unknown`` (offscreen/headless, or an OS without the notion).
    """
    if _override is not None:
        return _override
    app = QGuiApplication.instance()
    if app is None:
        return False
    return app.styleHints().colorScheme() == Qt.ColorScheme.Dark


def theme_color(token: str, dark: bool | None = None) -> str:
    """Resolve one palette token to a concrete colour string for the active mode.

    Needed wherever a value cannot come from QSS — icon pixmaps and syntax
    highlighter formats.
    """
    mode = current_dark() if dark is None else dark
    return palette(mode)[token]


def qcolor(value: str) -> QColor:
    """Build a QColor from a token value (``#rrggbb`` or ``rgba(r,g,b,a)``)."""
    match = _RGBA.match((value or "").strip())
    if match:
        red, green, blue = (int(round(float(match.group(i)))) for i in (1, 2, 3))
        alpha = float(match.group(4)) if match.group(4) is not None else 1.0
        return QColor(red, green, blue, int(round(alpha * 255)))
    return QColor(value)


def theme_qcolor(token: str, dark: bool | None = None) -> QColor:
    """Resolve a palette token to a QColor for the active mode.

    Models and delegates return QColor from ``Qt.BackgroundRole`` /
    ``Qt.ForegroundRole`` and therefore cannot use the QSS path.
    """
    mode = current_dark() if dark is None else dark
    return qcolor(palette(mode)[token])


def build_palette(dark: bool) -> QPalette:
    """Build the application palette from the same tokens the QSS uses.

    Call this wherever :func:`~pyitolstudio.theme.build_stylesheet` is called —
    the two together are what "applying a theme" means in this app.  Applying
    only the stylesheet leaves every unpainted surface on the *system*
    palette, which is how a dark window ends up with light rectangles in it.
    """
    p = palette(dark)
    text = qcolor(p["text"])
    base = qcolor(p["panel_alt"])

    pal = QPalette()
    # surfaces
    pal.setColor(QPalette.ColorRole.Window, qcolor(p["bg"]))
    pal.setColor(QPalette.ColorRole.Base, base)
    pal.setColor(QPalette.ColorRole.AlternateBase, qcolor(p["panel"]))
    pal.setColor(QPalette.ColorRole.Button, qcolor(p["panel"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, base)
    # text
    pal.setColor(QPalette.ColorRole.WindowText, text)
    pal.setColor(QPalette.ColorRole.Text, text)
    pal.setColor(QPalette.ColorRole.ButtonText, text)
    pal.setColor(QPalette.ColorRole.ToolTipText, text)
    pal.setColor(QPalette.ColorRole.PlaceholderText, qcolor(p["text_dim"]))
    pal.setColor(QPalette.ColorRole.BrightText, qcolor(p["danger"]))
    # bevel trio — kept on-theme so native-drawn frames do not flash grey
    pal.setColor(QPalette.ColorRole.Light, qcolor(p["line2"]))
    pal.setColor(QPalette.ColorRole.Midlight, qcolor(p["line"]))
    pal.setColor(QPalette.ColorRole.Mid, qcolor(p["line2"]))
    pal.setColor(QPalette.ColorRole.Dark, qcolor(p["line3"]))
    pal.setColor(QPalette.ColorRole.Shadow, qcolor(p["canvas"]))
    # selection + links
    pal.setColor(QPalette.ColorRole.Highlight, qcolor(p["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, qcolor(p["on_accent"]))
    pal.setColor(QPalette.ColorRole.Link, qcolor(p["accent_link"]))
    pal.setColor(QPalette.ColorRole.LinkVisited, qcolor(p["accent_lo"]))
    # disabled group
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.ButtonText,
    ):
        pal.setColor(QPalette.ColorGroup.Disabled, role, qcolor(p["text_disabled"]))
    return pal


def colour_is_light(value: QColor) -> bool:
    """Whether *value* needs dark text on top of it.

    Used by the preview's colour chips and by the colour swatches: a fill can
    be any hex the user typed, so the label drawn on it has to be chosen by
    luminance rather than fixed.  Threshold from WCAG relative luminance —
    either side of it gives at least 4.5:1 against one of the two text tokens.
    """
    r, g, b, _ = value.getRgb()
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance > 150
