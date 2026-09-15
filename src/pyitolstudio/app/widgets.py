"""Small shared Qt widget subclasses used by more than one pane.

Keeping them here (rather than private to one module) is what lets the
wizard's step buttons and the welcome page's action cards share the same
size-hint behaviour without one importing the other.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton


class LayoutSizeHintButton(QPushButton):
    """A QPushButton whose size hints come from its embedded layout.

    ``QPushButton::sizeHint`` measures only the button's own text; when the
    button's content is a layout of child labels (step rows, type cards,
    welcome action cards), that hint collapses to a single bare line and the
    labels spill outside the button rect — Qt does not clip children, so rows
    stack on top of each other.  Delegating the hints to the layout keeps
    every container button sized by what it actually holds, which is also
    what lets a word-wrapped description grow the card instead of being
    clipped by a fixed height.
    """

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt API)
        layout = self.layout()
        return layout.totalSizeHint() if layout is not None else super().sizeHint()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt API)
        layout = self.layout()
        return layout.totalMinimumSize() if layout is not None else super().minimumSizeHint()
