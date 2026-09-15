"""Template preview pane with iTOL syntax highlighting (FR-2)."""

from __future__ import annotations

import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit

from ..theme import FONT_SIZE_MONO, MONO_FAMILIES, palette
from ..theme_mode import colour_is_light, current_dark

_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\b")
_TYPE_HEADER = re.compile(r"^(DATASET_[A-Z_]+|TREE_COLORS|LABELS|METADATA|POPUP_INFO|SPACING|COLLAPSE|PRUNE)\s*$")
_PARAM_KEY = re.compile(r"^[A-Z][A-Z0-9_]*(?=\s|,|$)")

# Text drawn *on* a user-supplied colour chip.  These two are mode-independent
# by design: the chip's fill can be any hex, so the label on it has to be
# picked by that fill's luminance, not by the app's current mode.
_CHIP_ON_LIGHT = QColor(palette(True)["on_accent"])  # near-black
_CHIP_ON_DARK = QColor(palette(True)["text"])  # near-white


class TemplateHighlighter(QSyntaxHighlighter):
    """Highlights type headers, the SEPARATOR line, comments, parameter
    keys, and renders hex colours as swatch chips.

    All colors come from the theme tokens — the two modes carry different
    values, so the palette is re-read whenever ``dark`` changes.

    Colour values used to be drawn *in their own colour* as text, which is
    unreadable whenever the value is bright: ``#ffff00`` as a foreground on a
    white ground measures 1.07:1.  They are now chips — the colour is the
    background, the label is chosen for contrast — so the swatch still carries
    the hue while the value stays legible in both modes.
    """

    def __init__(self, document, dark: bool = False) -> None:
        super().__init__(document)
        self._rules: list = []
        self.set_dark(dark)

    def set_dark(self, dark: bool) -> None:
        """Re-point the rule colors at the given mode's tokens."""
        self._dark = dark
        p = palette(dark)
        header_fmt = QTextCharFormat()
        header_fmt.setFontWeight(QFont.Weight.Medium)
        # Type headers are small body text on the panel: accent is only 3.28:1
        # in light mode, below AA — accent_link is the AA-safe variant (UI P0-3).
        header_fmt.setForeground(QColor(p["accent_link"]))
        sep_fmt = QTextCharFormat()
        sep_fmt.setFontWeight(QFont.Weight.Medium)
        sep_fmt.setForeground(QColor(p["warn"]))
        comment_fmt = QTextCharFormat()
        # Comments are content, not a disabled state: text_disabled measured
        # 2.07–2.25:1 and the preview placeholder / failure notice are '#'
        # lines, so they nearly vanished (UI review P1-8).
        comment_fmt.setForeground(QColor(p["text_tertiary"]))
        comment_fmt.setFontItalic(True)
        key_fmt = QTextCharFormat()
        key_fmt.setForeground(QColor(p["dv1"]))
        key_fmt.setFontWeight(QFont.Weight.Medium)
        # Order is precedence: later setFormat wins.  _PARAM_KEY is the widest
        # match (it also matches SEPARATOR and the DATASET_* type headers), so it
        # must be written FIRST; the narrow rules go last so they override it —
        # otherwise type headers and SEPARATOR collapse into the parameter-key
        # colour (UI review P0-4).
        self._rules = [
            (_PARAM_KEY, key_fmt),
            (re.compile(r"^#.*$"), comment_fmt),
            (re.compile(r"^SEPARATOR\s+\S+$"), sep_fmt),
            (_TYPE_HEADER, header_fmt),
        ]

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt API)
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)
        for match in _HEX_COLOR.finditer(text):
            color = QColor(match.group(0))
            if not color.isValid():
                continue
            start = match.start()
            length = len(match.group(0))
            # Borrow one space on either side when the line has them, so the
            # chip has padding instead of being a bare coloured word.
            lead = 1 if start > 0 and text[start - 1] == " " else 0
            trail = 1 if start + length < len(text) and text[start + length] == " " else 0
            chip = QTextCharFormat()
            chip.setBackground(color)
            chip.setForeground(_CHIP_ON_LIGHT if colour_is_light(color) else _CHIP_ON_DARK)
            self.setFormat(start - lead, length + lead + trail, chip)


class TemplatePreview(QPlainTextEdit):
    """Read-only template text preview."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        mono = QFont()
        mono.setFamilies(list(MONO_FAMILIES))
        mono.setPixelSize(FONT_SIZE_MONO)
        self.setFont(mono)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._highlighter = TemplateHighlighter(self.document(), current_dark())

    def set_dark(self, dark: bool) -> None:
        """Re-highlight with the other mode's tokens."""
        self._highlighter.set_dark(dark)
        self._highlighter.rehighlight()

    def set_text(self, text: str) -> None:
        self.setPlainText(text)
