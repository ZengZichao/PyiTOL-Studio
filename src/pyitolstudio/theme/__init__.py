"""Visual tokens for the v2.0 "Instrument Dark" design system.

Values are translated 1:1 from the locked prototype
(``PyiTOL-Studio-界面原型-v2.html``) and the design book
(``PyiTOL-Studio-设计方案-v2.md`` §4). Translating the tokens into QSS is not
allowed to invent values (development plan §5.7).

Dark and light are **both first-class modes**: every token exists in both
dictionaries and the two sets are maintained side by side — there is no
"dark first, light later" fallback.  Two consequences worth repeating:

* the brand colour is two different hex values (dark ``#35e0a1`` /
  light ``#0e9c68``) — one value cannot be right on both grounds;
* the semantic and data-visualisation colours are a full step darker in
  light mode, because the dark set was brightened for a dark ground.

No widget may hard-code a colour: read it from :func:`palette` or rely on
:func:`build_stylesheet`.

Qt stylesheet limits honoured here
----------------------------------
``box-shadow`` and ``letter-spacing`` do not exist in Qt's stylesheet
engine, and font sizes are integer pixels.  Therefore:

* the design's focus ring (``0 0 0 3px accent-soft`` + brand stroke) is
  approximated by a brand-coloured 1px border — never ``outline: none``;
* the caption style (uppercase, ``.09em`` tracking) is applied per widget
  with :class:`~PySide6.QtGui.QFont` where it matters;
* the ``11.5px`` / ``10.5px`` steps of the type scale are rounded to whole
  pixels (Qt cannot render fractional pixel sizes).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Spacing scale (px) — design book §4.5: 2 / 4 / 8 / 12 / 16 / 20 / 24 / 32
# The design book writes this scale as bare numbers, so the canonical names
# are numeric; the v1.0 letter names are kept below as aliases.
# ---------------------------------------------------------------------------
SPACE_1 = 2
SPACE_2 = 4
SPACE_3 = 8
SPACE_4 = 12
SPACE_5 = 16
SPACE_6 = 20
SPACE_7 = 24
SPACE_8 = 32

# v1.0 names — kept so existing call sites keep their meaning.
SPACE_XXS = SPACE_1
SPACE_XS = SPACE_2
SPACE_S = SPACE_3
SPACE_M = SPACE_4
SPACE_L = SPACE_5
SPACE_XL = SPACE_7
SPACE_XXL = SPACE_8

# ---------------------------------------------------------------------------
# Radii (px) — design book §4.5/§4.6: 4 / 6 / 8 / 12 / 16
# ---------------------------------------------------------------------------
RADIUS_S = 4  # chips, small controls
RADIUS_M = 6  # inputs, buttons
RADIUS_L = 8  # cards, panels
RADIUS_XL = 12  # window
RADIUS_XXL = 16  # large cards

# ---------------------------------------------------------------------------
# Typography — design book §4.4
# ---------------------------------------------------------------------------
# "-apple-system" is a CSS-only alias Qt cannot resolve (font-population
# warning on every first paint); name real families instead.  The Windows and
# Linux CJK fallbacks keep Chinese rendering on-brand off macOS (design
# review P2 — the last two entries only ever match on those platforms).
FONT_FAMILY = (
    "'SF Pro Text', 'PingFang SC', 'Helvetica Neue', "
    "'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif"
)
FONT_MONO = (
    "'SF Mono', 'JetBrains Mono', Menlo, "
    "'Microsoft YaHei', 'Noto Sans CJK SC', monospace"
)
# The same stack as a family list, for widgets that build a QFont in code
# (QSS takes the CSS string above; QFont needs real family names).
MONO_FAMILIES = (
    "SF Mono",
    "JetBrains Mono",
    "Menlo",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Monospace",
)

FONT_SIZE = 13  # body / heading
FONT_SIZE_SMALL = 11
FONT_SIZE_DISPLAY = 25  # welcome title (700, -.025em)
FONT_SIZE_TITLE = 16  # wizard step title (700)
FONT_SIZE_HEADING = 13  # panel title, unit name (700)
FONT_SIZE_LABEL = 12  # form label — design value 11.5px, rounded to whole px
FONT_SIZE_CAPTION = 11  # group caption — design value 10.5px, rounded to whole px
FONT_SIZE_MONO = 12  # data: tree IDs, parameter keys, template text, paths

FONT_WEIGHT_REGULAR = 400
FONT_WEIGHT_MEDIUM = 500
FONT_WEIGHT_BOLD = 700

# Emphasis inside UI chrome.  CJK glyphs rendered at 11–13px with a fake bold
# (Qt synthesises 700 for PingFang SC, which ships no bold master at these
# sizes) smear into each other — the strokes collide and the text reads as
# blur rather than as emphasis.  Since 0.5.0 every style rule at or below
# FONT_SIZE_HEADING uses this weight instead, and hierarchy is carried by
# size and colour (text / text_dim / text_tertiary) rather than by weight.
# Only display-scale text (>= 16px) still uses FONT_WEIGHT_BOLD.
FONT_WEIGHT_STRONG = FONT_WEIGHT_MEDIUM

# ---------------------------------------------------------------------------
# Control metrics — one height for every interactive control (UI review 0.5.0)
# ---------------------------------------------------------------------------
# Before 0.5.0 the app shipped 25 / 26 / 28 / 30 px controls side by side
# (a spin box's inner line edit measured 25 px, a search box 26 px, a text
# input 28 px).  Neighbours that differ by 2–3 px read as "slightly broken"
# even when nobody can name why.  Everything now resolves to one of two
# heights, and the QSS below enforces it.
CONTROL_HEIGHT = 28  # inputs, buttons, combo boxes — the default
CONTROL_HEIGHT_COMPACT = 24  # dense contexts (grid footer buttons, chips)
ICON_BUTTON = 24  # square icon-only button (inspector header, field reset)
TOOLBAR_BUTTON = 32  # square toolbar button
TOOLBAR_ICON = 18  # toolbar glyph size (was 16 — too small next to 13px text)

# ---------------------------------------------------------------------------
# Brand colour — two values, one per mode.  Do not merge them.
# ---------------------------------------------------------------------------
ACCENT_LIGHT = "#0e9c68"
ACCENT_DARK = "#35e0a1"

# ---------------------------------------------------------------------------
# Dark mode (default) — design book §4.1–§4.2
# ---------------------------------------------------------------------------
_DARK = {
    # — surfaces: elevation + 1px translucent stroke instead of shadows —
    "canvas": "#080b10",
    "bg": "#0f131a",  # surface-1 · content area
    "panel": "#151a22",  # surface-2 · toolbar / rails / inspector / status bar
    "panel_alt": "#1b212b",  # surface-3 · cards / inputs / code blocks
    "hover": "#232a36",
    "active": "#2c3543",
    "overlay": "rgba(5,8,12,.66)",
    # — strokes: three translucent levels, stackable on any surface —
    "line": "rgba(255,255,255,.07)",
    "line2": "rgba(255,255,255,.11)",
    "line3": "rgba(255,255,255,.18)",
    "border": "rgba(255,255,255,.11)",  # v1.0 alias of line2
    # — text: four levels, all checked against 4.5:1 —
    "text": "#e9edf3",
    "text_dim": "#9aa5b4",
    "text_tertiary": "#7b8794",  # WCAG AA: 5.08:1 on bg / 4.77:1 on panel
    "text_disabled": "#4a5361",
    # — brand —
    "accent": ACCENT_DARK,
    "accent_hi": "#4ff0b1",
    "accent_lo": "#22c98c",
    "accent_soft": "rgba(53,224,161,.12)",
    "accent_line": "rgba(53,224,161,.34)",
    "on_accent": "#04160e",
    "accent_text": "#04160e",  # v1.0 alias of on_accent
    "accent_link": ACCENT_DARK,  # accent used as small text/link (≥4.5:1 on bg)
    "sel_bg": "rgba(53,224,161,.12)",  # v1.0 alias of accent_soft
    # — semantic —
    "info": "#58a6ff",
    "info_soft": "rgba(88,166,255,.13)",
    "warn": "#f0b429",
    "warn_soft": "rgba(240,180,41,.13)",
    "danger": "#ff6b6b",
    "danger_soft": "rgba(255,107,107,.13)",
    "ok": "#35e0a1",
    "error": "#ff6b6b",  # v1.0 alias of danger
    # — data visualisation: Okabe–Ito, brightened for a dark ground —
    "dv1": "#6ec1f0",
    "dv2": "#f2b24a",
    "dv3": "#2fbf95",
    "dv4": "#f5ec6b",
    "dv5": "#4c9ee0",
    "dv6": "#f07a2e",
    "dv7": "#e08fc0",
    "dv8": "#a8b0ba",
}

# ---------------------------------------------------------------------------
# Light mode — first-class, maintained token-for-token with the dark set.
# ---------------------------------------------------------------------------
_LIGHT = {
    "canvas": "#e6e9ee",
    "bg": "#ffffff",
    "panel": "#f6f7f9",
    "panel_alt": "#ffffff",
    "hover": "rgba(13,18,25,.045)",
    "active": "rgba(13,18,25,.075)",
    "overlay": "rgba(255,255,255,.7)",
    "line": "rgba(13,18,25,.09)",
    "line2": "rgba(13,18,25,.13)",
    "line3": "rgba(13,18,25,.22)",
    "border": "rgba(13,18,25,.13)",
    "text": "#0f141b",
    "text_dim": "#5a6472",
    "text_tertiary": "#66727f",  # WCAG AA: 4.91:1 on white / 4.58:1 on panel
    "text_disabled": "#a7afb9",
    "accent": ACCENT_LIGHT,
    "accent_hi": "#12b378",
    "accent_lo": "#0b7d54",
    "accent_soft": "rgba(14,156,104,.10)",
    "accent_line": "rgba(14,156,104,.35)",
    "on_accent": "#04160e",  # was #ffffff (3.52:1 on accent) → 5.3:1 on accent
    "accent_text": "#04160e",
    "accent_link": "#0b7d54",  # accent as small text/link: 5.15:1 on white
    "sel_bg": "rgba(14,156,104,.10)",
    # semantic + data-viz colours sit one full step darker than the dark set
    "info": "#2b6fd4",
    "info_soft": "rgba(43,111,212,.10)",
    "warn": "#9a6700",  # was #b47c00 (3.61:1) → 4.87:1 on white
    "warn_soft": "rgba(154,103,0,.12)",
    "danger": "#d33b3b",
    "danger_soft": "rgba(211,59,59,.10)",
    "ok": "#0e9c68",
    "error": "#d33b3b",
    "dv1": "#1c7fb8",
    "dv2": "#c07a00",
    "dv3": "#0e8a6a",
    "dv4": "#a89000",
    "dv5": "#2b6fd4",
    "dv6": "#c2521a",
    "dv7": "#a8548c",
    "dv8": "#6b7480",
}


def palette(dark: bool) -> dict[str, str]:
    """Return the token mapping for one mode."""
    return _DARK if dark else _LIGHT


# Every text-entry-ish widget shares one rule block.  The list has to be
# stamped per selector: ``A, B, C:focus`` applies the pseudo-state to ``C``
# alone and silently applies the *plain* rule to A and B, which is how every
# input in the app ended up wearing the 2px brand focus ring all the time.
_INPUT_WIDGETS = (
    "QTreeView",
    "QListView",
    "QTableView",
    "QPlainTextEdit",
    "QTextEdit",
    "QLineEdit",
    "QComboBox",
    "QSpinBox",
    "QDoubleSpinBox",
)


def _input_selectors(pseudo: str = "") -> str:
    """The shared input selector list, with *pseudo* on each selector."""
    return ", ".join(widget + pseudo for widget in _INPUT_WIDGETS)


def build_stylesheet(dark: bool = False) -> str:
    """Render the QSS from tokens (no hard-coded colors in widgets)."""
    p = palette(dark)
    inputs = _input_selectors()
    inputs_hover = _input_selectors(":hover")
    inputs_focus = _input_selectors(":focus")
    inputs_disabled = _input_selectors(":disabled")
    return f"""
* {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}px;
}}
QMainWindow, QDialog {{
    background: {p['bg']};
}}
QWidget {{
    color: {p['text']};
}}
QLabel#dimLabel {{
    color: {p['text_dim']};
    font-size: {FONT_SIZE_SMALL}px;
}}
QLabel#dimLabel[invalid="true"] {{
    /* Import / read failure is surfaced here by wizard.py::DataPage._set_error;
       without this rule the error reads the same as the normal column note
       (UI review P1-7). */
    color: {p['danger']};
}}
QLabel#caption {{
    color: {p['text_tertiary']};
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QLabel#monoData {{
    font-family: {FONT_MONO};
    font-size: {FONT_SIZE_MONO}px;
}}
QLabel#inlineError {{
    color: {p['danger']};
}}
QToolBar {{
    background: {p['panel']};
    border: none;
    border-bottom: 1px solid {p['line']};
    padding: {SPACE_2}px {SPACE_4}px;
    spacing: {SPACE_3}px;
}}
QToolButton {{
    min-width: {TOOLBAR_BUTTON}px;
    min-height: {TOOLBAR_BUTTON}px;
    padding: 0;
    border-radius: {RADIUS_S}px;
    color: {p['text']};
}}
QToolButton:hover {{
    background: {p['hover']};
    color: {p['text']};
}}
QToolButton:pressed, QToolButton:checked {{
    background: {p['active']};
}}
QToolButton#primaryTool {{
    /* The one accent-filled toolbar action (review P1 — keep `accent`
       unmistakable for the primary operation; all other toolbar buttons
       stay neutral until hover).  Base uses `accent`, not `accent_lo`:
       on_accent on accent_lo is only 3.62:1 in light mode (UI P0-3). */
    background: {p['accent']};
    color: {p['on_accent']};
    border-radius: {RADIUS_S}px;
    padding: {SPACE_2}px {SPACE_4}px;
}}
QToolButton#primaryTool:hover {{
    background: {p['accent_hi']};
}}
QToolButton#primaryTool:pressed {{
    background: {p['accent_lo']};
}}
QStatusBar {{
    background: {p['panel']};
    color: {p['text_tertiary']};
    border-top: 1px solid {p['line']};
}}
QStatusBar::item {{
    border: none;
}}
{inputs} {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_M}px;
    padding: {SPACE_2}px {SPACE_3}px;
    min-height: {CONTROL_HEIGHT}px;
    selection-background-color: {p['accent_soft']};
    selection-color: {p['text']};
}}
{inputs_hover} {{
    border-color: {p['line3']};
}}
{inputs_focus} {{
    /* WCAG keyboard focus: 2px brand ring + 12% brand fill (design review P0). */
    border: 2px solid {p['accent']};
    background: {p['accent_soft']};
    padding: {SPACE_2 - 1}px {SPACE_3 - 1}px;
}}
{inputs_disabled} {{
    color: {p['text_disabled']};
    border-color: {p['line']};
}}
QTreeView::item, QListView::item {{
    padding: {SPACE_2}px {SPACE_3}px;
}}
QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{
    background: {p['accent_soft']};
    color: {p['text']};
}}
QHeaderView::section {{
    background: {p['panel']};
    border: none;
    border-bottom: 1px solid {p['line2']};
    color: {p['text_tertiary']};
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: {FONT_WEIGHT_STRONG};
    padding: {SPACE_2}px {SPACE_3}px;
}}
QPushButton {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_M}px;
    padding: {SPACE_2}px {SPACE_5}px;
    min-height: {CONTROL_HEIGHT}px;
}}
QPushButton:hover {{
    background: {p['hover']};
    border-color: {p['line3']};
}}
QPushButton:pressed {{
    background: {p['active']};
}}
QPushButton:focus {{
    border: 2px solid {p['accent']};
    padding: {SPACE_2 - 1}px {SPACE_5 - 1}px;
}}
QPushButton#primary:focus {{
    border: 2px solid {p['on_accent']};
    padding: {SPACE_2 - 1}px {SPACE_5 - 1}px;
}}
QPushButton#primary {{
    background: {p['accent']};
    color: {p['on_accent']};
    border: 1px solid transparent;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QPushButton#primary:hover {{
    background: {p['accent_hi']};
    border-color: transparent;
}}
QPushButton#primary:pressed {{
    background: {p['accent_lo']};
    border-color: transparent;
}}
QPushButton#primary:disabled {{
    background: {p['accent_soft']};
    color: {p['text_disabled']};
}}
QPushButton:disabled {{
    color: {p['text_disabled']};
    border-color: {p['line']};
}}
QProgressBar {{
    background: {p['active']};
    border: none;
    border-radius: {RADIUS_S}px;
    text-align: center;
    color: {p['text_dim']};
}}
QProgressBar::chunk {{
    background: {p['accent']};
    border-radius: {RADIUS_S}px;
}}
/* --- inspector: header / search / groups / fields / footer (design §5.1) --- */
QWidget#inspectorPanel {{
    background: {p['panel']};
}}
QWidget#inspectorHead {{
    background: {p['panel']};
    border-bottom: 1px solid {p['line']};
}}
QLabel#unitName {{
    font-size: {FONT_SIZE_HEADING}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QLabel#typeBadge {{
    font-family: {FONT_MONO};
    font-size: {FONT_SIZE_CAPTION}px;
    color: {p['text_tertiary']};
    background: {p['panel_alt']};
    border: 1px solid {p['line']};
    border-radius: {RADIUS_S}px;
    padding: {SPACE_1}px {SPACE_3}px;
}}
QToolButton#iconButton {{
    width: 24px;
    height: 24px;
    border: none;
    border-radius: {RADIUS_S}px;
    background: transparent;
}}
QToolButton#iconButton:hover {{
    background: {p['hover']};
}}
QToolButton#iconButton:pressed {{
    background: {p['active']};
}}
QLineEdit#searchBox {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_M}px;
    font-size: {FONT_SIZE}px;
    padding: {SPACE_1}px {SPACE_2}px;
}}
QLineEdit#searchBox:hover {{
    border-color: {p['line3']};
}}
QLineEdit#searchBox:focus {{
    border: 2px solid {p['accent']};
    background: {p['accent_soft']};
    padding: {SPACE_1 - 1}px {SPACE_2 - 1}px;
}}
QLineEdit#monoInput {{
    font-family: {FONT_MONO};
    font-size: {FONT_SIZE_MONO}px;
}}
QScrollArea#inspectorScroll {{
    background: transparent;
    border: none;
}}
/* Qt draws the scroll viewport with a child widget, so it needs its own rule. */
QScrollArea#inspectorScroll > QWidget > QWidget {{
    background: transparent;
}}
QWidget#groupSection {{
    background: {p['bg']};
    border: 1px solid {p['line']};
    border-radius: {RADIUS_L}px;
}}
QWidget#groupHeader {{
    background: {p['panel_alt']};
    border-top-left-radius: {RADIUS_L}px;
    border-top-right-radius: {RADIUS_L}px;
}}
QWidget#groupHeader:hover {{
    background: {p['hover']};
}}
QLabel#groupTitle {{
    font-size: {FONT_SIZE_LABEL}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QLabel#groupCount {{
    font-family: {FONT_MONO};
    font-size: {FONT_SIZE_CAPTION}px;
    color: {p['text_tertiary']};
}}
QLabel#fieldLabel {{
    font-size: {FONT_SIZE_LABEL}px;
    color: {p['text_dim']};
}}
QLabel#fieldLabel[invalid="true"] {{
    /* Parameter-level validation (design review P2 — state, not decorative:
       a field that breaks required/range/colour rules is flagged in place). */
    color: {p['danger']};
}}
QLabel#fieldKey {{
    font-family: {FONT_MONO};
    font-size: {FONT_SIZE_CAPTION}px;
    color: {p['text_tertiary']};
}}
QWidget#inspectorFoot {{
    background: {p['panel']};
    border-top: 1px solid {p['line']};
}}
QFrame#validationBanner {{
    border-radius: {RADIUS_M}px;
}}
QFrame#validationBanner[state="ok"] {{
    background: {p['accent_soft']};
    border: 1px solid {p['accent_line']};
}}
QFrame#validationBanner[state="ok"] QLabel {{
    color: {p['accent_link']};
}}
QFrame#validationBanner[state="warn"] {{
    background: {p['warn_soft']};
    border: 1px solid {p['warn']};
}}
QFrame#validationBanner[state="warn"] QLabel {{
    color: {p['warn']};
}}
QFrame#validationBanner[state="muted"] {{
    background: {p['panel_alt']};
    border: 1px solid {p['line']};
}}
QFrame#validationBanner[state="muted"] QLabel {{
    color: {p['text_tertiary']};
}}
QFrame#validationBanner QLabel {{
    font-size: {FONT_SIZE_SMALL}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QSplitter::handle {{
    background: {p['line']};
    width: 1px;
}}
QMenu {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_M}px;
    padding: {SPACE_1}px;
}}
QMenu::item {{
    padding: {SPACE_2}px {SPACE_5}px;
    border-radius: {RADIUS_S}px;
}}
QMenu::item:selected {{
    background: {p['accent_soft']};
    color: {p['text']};
}}
QMenu::separator {{
    height: 1px;
    background: {p['line']};
    margin: {SPACE_1}px {SPACE_2}px;
}}
/* --- welcome page (design §5.2) --- */
QLabel#welcomeLogo {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {p['accent']}, stop: 1 {p['accent_lo']}
    );
    border-radius: 20px;
}}
QLabel#welcomeTitle {{
    font-size: {FONT_SIZE_DISPLAY}px;
    font-weight: {FONT_WEIGHT_BOLD};
}}
QLabel#welcomeSubtitle {{
    font-family: {FONT_MONO};
    font-size: {FONT_SIZE_MONO}px;
    color: {p['text_tertiary']};
}}
QPushButton#actionCard {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_XL}px;
    padding: 0;
    text-align: left;
    /* Restate the design floor: the global QPushButton min-height (28px)
       otherwise overwrites the widget's setMinimumSize(196, 104) when the
       stylesheet is applied.  The card still grows with its content via
       height-for-width (UI review: button text must never truncate). */
    min-width: 196px;
    min-height: 104px;
}}
QPushButton#actionCard:hover {{
    background: {p['accent_soft']};
    border-color: {p['accent_line']};
}}
QPushButton#actionCard:pressed {{
    background: {p['hover']};
}}
QPushButton#actionCard:focus {{
    /* Keyboard focus ring on the welcome cards (design review P0#2). */
    border: 2px solid {p['accent']};
}}
QLabel#cardIcon {{
    background: {p['accent_soft']};
    border-radius: {RADIUS_L}px;
}}
QLabel#cardName {{
    font-size: {FONT_SIZE}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QLabel#kbd {{
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: {FONT_WEIGHT_MEDIUM};
    color: {p['text_tertiary']};
    background: {p['bg']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_S}px;
    padding: 1px {SPACE_2}px;
}}
QLabel#cardDesc {{
    font-size: {FONT_SIZE_SMALL}px;
    color: {p['text_tertiary']};
}}
QListWidget#recentList {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget#recentList::item {{
    background: transparent;
    border: none;
    border-radius: {RADIUS_M}px;
}}
QListWidget#recentList::item:focus, QListWidget#commandList::item:focus {{
    /* Restore a visible keyboard focus ring (design review P0#2) without
       re-adding the outline the list's own paint needs to suppress. */
    border: 1px solid {p['accent']};
    border-radius: {RADIUS_M}px;
    background: {p['accent_soft']};
}}
QWidget#dropzone {{
    border: 1px dashed {p['line3']};
    border-radius: {RADIUS_M}px;
    background: transparent;
}}
QLabel#dropText {{
    font-size: {FONT_SIZE_SMALL}px;
    color: {p['text_tertiary']};
}}
QLabel#dropEmph {{
    font-size: {FONT_SIZE_SMALL}px;
    font-weight: {FONT_WEIGHT_STRONG};
    color: {p['text_dim']};
}}
/* --- left rail: tree card + unit list (design §5.1) --- */
QWidget#rail {{
    background: {p['panel']};
    border-right: 1px solid {p['line']};
}}
QWidget#railCardHost, QWidget#railSection {{
    background: {p['panel']};
}}
QWidget#treeCard {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_L}px;
}}
QLabel#treeCardIcon {{
    background: {p['accent_soft']};
    border-radius: {RADIUS_M}px;
}}
QLabel#treeCardName {{
    font-family: {FONT_MONO};
    font-size: {FONT_SIZE_MONO}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QLabel#treeCardMeta {{
    font-size: {FONT_SIZE_SMALL}px;
    color: {p['text_tertiary']};
}}
QLabel#treeCardMatch {{
    font-size: {FONT_SIZE_SMALL}px;
    font-weight: {FONT_WEIGHT_STRONG};
    color: {p['accent_link']};
}}
QProgressBar#treeProgress {{
    background: {p['active']};
    border: none;
    border-radius: 2px;
}}
QProgressBar#treeProgress::chunk {{
    background: {p['accent']};
    border-radius: 2px;
}}
QPushButton#linkButton {{
    background: transparent;
    border: none;
    padding: 0;
    font-size: {FONT_SIZE_SMALL}px;
    color: {p['text_tertiary']};
}}
QPushButton#linkButton:hover {{
    background: transparent;
    color: {p['accent_link']};
}}
QLabel#countChip {{
    background: {p['panel_alt']};
    border-radius: 99px;
    padding: 1px {SPACE_2}px;
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: {FONT_WEIGHT_STRONG};
    color: {p['text_tertiary']};
}}
QListWidget#unitList {{
    background: transparent;
    border: none;
    padding: 0 {SPACE_2}px {SPACE_2}px {SPACE_2}px;
    outline: none;
}}
QListWidget#unitList::item {{
    background: transparent;
    border: none;
}}
/* --- template wizard (design §5.3) --- */
QWidget#wizardSteps {{
    background: {p['panel']};
    border-right: 1px solid {p['line']};
}}
QPushButton#stepButton {{
    background: transparent;
    border: none;
    border-radius: {RADIUS_M}px;
    text-align: left;
    padding: 0;
}}
QPushButton#stepButton:hover {{
    background: {p['hover']};
}}
QPushButton#stepButton[state="active"] {{
    background: {p['accent_soft']};
}}
QPushButton#stepButton:disabled {{
    background: transparent;
}}
QLabel#stepBadge {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: 11px;
    color: {p['text_tertiary']};
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QPushButton#stepButton[state="active"] QLabel#stepBadge {{
    background: {p['accent']};
    color: {p['on_accent']};
    border: 1px solid transparent;
}}
QPushButton#stepButton[state="done"] QLabel#stepBadge {{
    background: {p['accent_soft']};
    color: {p['accent_link']};
    border: 1px solid {p['accent_line']};
}}
QLabel#stepTitle {{
    font-size: {FONT_SIZE}px;
    font-weight: {FONT_WEIGHT_STRONG};
    color: {p['text_dim']};
}}
QPushButton#stepButton[state="active"] QLabel#stepTitle {{
    color: {p['accent_link']};
}}
QPushButton#stepButton[state="done"] QLabel#stepTitle {{
    color: {p['text']};
}}
QLabel#stepSubtitle {{
    font-size: {FONT_SIZE_CAPTION}px;  /* design 10.5px → whole-px token */
    color: {p['text_tertiary']};
}}
QLineEdit#typeSearch {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_M}px;
    padding: {SPACE_2}px {SPACE_3}px;
}}
QLineEdit#typeSearch:focus {{
    border: 2px solid {p['accent']};
    background: {p['accent_soft']};
    padding: {SPACE_2 - 1}px {SPACE_3 - 1}px;
}}
QLabel#typeGroupHeader {{
    font-size: {FONT_SIZE_CAPTION}px;  /* design 10.5px → whole-px token */
    font-weight: {FONT_WEIGHT_STRONG};
    color: {p['text_tertiary']};
    letter-spacing: 0.09em;
    padding-top: {SPACE_4}px;
}}
QLabel#typeGroupDesc {{
    font-size: {FONT_SIZE_SMALL}px;
    color: {p['text_tertiary']};
    margin-bottom: {SPACE_2}px;
}}
QPushButton#typeCard {{
    background: {p['panel']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_M}px;
    padding: {SPACE_3}px;
    text-align: left;
}}
QPushButton#typeCard:hover {{
    border-color: {p['line3']};
    background: {p['panel_alt']};
}}
QPushButton#typeCard:checked {{
    border-color: {p['accent']};
    background: {p['accent_soft']};
}}
QLabel#typeCardIcon {{
    background: {p['panel_alt']};
    border-radius: {RADIUS_M}px;
}}
/* NB: Qt cannot match a descendant by an ancestor's pseudo-state, so the old
   rule that reached from a checked typeCard into its icon silently applied to
   *every* card — all 31 icons sat on solid brand green.  The card sets a
   property on its own glyph instead, which the selector below can match. */
QLabel#typeCardIcon[state="checked"] {{
    background: {p['accent']};
}}
QLabel#typeCardName {{
    font-size: {FONT_SIZE}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QLabel#typeCardDesc {{
    font-size: {FONT_SIZE_CAPTION}px;  /* design 10.5px → whole-px token */
    color: {p['text_tertiary']};
}}
QFrame#colpill, QFrame#colpillDyn {{
    background: {p['panel_alt']};
    border: 1px solid {p['line']};
    border-radius: 99px;
}}
QFrame#colpillDyn {{
    border: 1px solid {p['line2']};
}}
QLabel#colpillDot {{
    background: {p['accent']};
    border-radius: 3px;
}}
QFrame#colpillDyn QLabel#colpillDot {{
    background: {p['dv2']};
}}
QTextEdit#wizardPreview {{
    background: {p['panel']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_M}px;
    font-family: {FONT_MONO};
    font-size: {FONT_SIZE_MONO}px;
}}
QWidget#paramsSummary {{
    background: {p['panel']};
    border-left: 1px solid {p['line']};
}}
QLabel#paramsSummaryTitle {{
    font-size: {FONT_SIZE_HEADING}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
/* --- command palette (⌘K, design §5.1/§6) --- */
QDialog#commandPalette {{
    background: {p['panel_alt']};
}}
QLineEdit#commandSearch {{
    background: {p['panel']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_M}px;
    padding: {SPACE_3}px {SPACE_3}px;
    font-size: {FONT_SIZE}px;
}}
QLineEdit#commandSearch:hover {{
    border-color: {p['line3']};
}}
QLineEdit#commandSearch:focus {{
    border: 2px solid {p['accent']};
    background: {p['accent_soft']};
    padding: {SPACE_3 - 1}px {SPACE_3 - 1}px;
}}
QListWidget#commandList {{
    background: transparent;
    border: none;
    padding: 0 {SPACE_2}px {SPACE_2}px {SPACE_2}px;
    outline: none;
}}
QListWidget#commandList::item {{
    background: transparent;
    border: none;
}}
/* --- center pane: data grid + footer (design §9.2) --- */
QWidget#dataPane {{
    background: {p['bg']};
}}
QTableView#dataGrid {{
    background: {p['bg']};
    border: none;
    gridline-color: transparent;
    selection-background-color: {p['accent_soft']};
    selection-color: {p['text']};
}}
/* Gridlines off, a 1px bottom rule per row instead (design §9.2). */
QTableView#dataGrid::item {{
    border-bottom: 1px solid {p['line']};
    padding: 0 {SPACE_3}px;
}}
QTableView#dataGrid::item:hover {{
    background: {p['panel_alt']};
}}
QTableView#dataGrid::item:selected {{
    background: {p['accent_soft']};
    color: {p['text']};
}}
QWidget#gridFooter {{
    background: {p['panel']};
    border-top: 1px solid {p['line']};
}}
QPushButton#smallButton {{
    font-size: {FONT_SIZE}px;
    padding: {SPACE_1}px {SPACE_3}px;
}}
/* Inline "browse" buttons next to path fields: 28px square, so the global
   16px side padding would leave a negative content rect and clip the
   "…"/icon (UI review: button text must never truncate). */
QPushButton#browseButton {{
    padding: 0;
    min-width: 0;
}}
QLabel#noticeChip {{
    font-size: {FONT_SIZE_SMALL}px;
    font-weight: {FONT_WEIGHT_STRONG};
    border-radius: {RADIUS_S}px;
    padding: {SPACE_1}px {SPACE_3}px;
}}
QLabel#noticeChip[state="danger"] {{
    color: {p['danger']};
    background: {p['danger_soft']};
    border: 1px solid {p['danger']};
}}
QLabel#noticeChip[state="warn"] {{
    color: {p['warn']};
    background: {p['warn_soft']};
    border: 1px solid {p['warn']};
}}
QLabel#noticeChip[state="accent"] {{
    color: {p['accent_link']};
    background: {p['accent_soft']};
    border: 1px solid {p['accent_line']};
}}
/* --- toast (non-modal feedback, design review P1#5) --- */
QFrame#toast {{
    background: {p['panel_alt']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_L}px;
}}
QLabel#toastText {{
    color: {p['text']};
    font-size: {FONT_SIZE_SMALL}px;
}}
QLabel#toastText[state="danger"] {{
    color: {p['danger']};
}}
/* --- empty-state guide overlay (design review P1#4) --- */
QWidget#emptyState {{
    background: {p['bg']};
}}
QLabel#emptyTitle {{
    font-size: {FONT_SIZE_TITLE}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QLabel#emptyBody {{
    font-size: {FONT_SIZE_SMALL}px;
    color: {p['text_tertiary']};
}}
QPushButton#emptyCta {{
    background: {p['accent']};
    color: {p['on_accent']};
    border: 1px solid transparent;
    border-radius: {RADIUS_M}px;
    padding: {SPACE_2}px {SPACE_5}px;
    font-weight: {FONT_WEIGHT_STRONG};
}}
QPushButton#emptyCta:hover {{
    background: {p['accent_hi']};
}}
/* --- tree card loading state (design review P1#3) --- */
QLabel#treeCardLoading {{
    font-size: {FONT_SIZE_SMALL}px;
    color: {p['text_tertiary']};
}}
/* --- 0.5.0 control metrics: every interactive control shares one height --- */
QPushButton#smallButton, QPushButton#linkButton, QToolButton#fieldReset {{
    min-height: {CONTROL_HEIGHT_COMPACT}px;
}}
/* The welcome page sits on `canvas` so its `panel_alt` cards separate from the
   ground in light mode, where bg and panel_alt are both white (UI review §05). */
QWidget#welcome {{
    background: {p['canvas']};
}}
/* Group separator in the toolbar: 1px x 20px next to 8px of air either side,
   so the five groups read as groups (UI review §04 ②). */
QToolBar::separator {{
    background: {p['line2']};
    width: 1px;
    margin: {SPACE_3}px {SPACE_4}px;
}}
/* Per-field reset affordance: a 24px icon button that only appears once the
   value differs from its default (UI review §06). */
QToolButton#fieldReset {{
    border: none;
    background: transparent;
    border-radius: {RADIUS_S}px;
    padding: 0;
}}
QToolButton#fieldReset:hover {{
    background: {p['hover']};
}}
/* Swatch beside a colour input: 20px so it reads as an input adornment rather
   than a block welded to the field (UI review §04 ⑧). */
QFrame#colorSwatch {{
    border: 1px solid {p['line3']};
    border-radius: {RADIUS_S}px;
}}
/* The global QToolButton minima above must not inflate the small square icon
   buttons: restate their real size here. */
QToolButton#iconButton {{
    min-width: {ICON_BUTTON}px;
    min-height: {ICON_BUTTON}px;
}}
QToolButton#fieldReset {{
    min-width: {ICON_BUTTON}px;
}}
QToolTip {{
    background: {p['panel_alt']};
    color: {p['text']};
    border: 1px solid {p['line2']};
    border-radius: {RADIUS_S}px;
    padding: {SPACE_2}px {SPACE_3}px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p['active']};
    border-radius: {RADIUS_S}px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p['line3']};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {p['active']};
    border-radius: {RADIUS_S}px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {p['line3']};
}}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
    border: none;
    height: 0;
    width: 0;
}}
"""
