"""Non-modal toast notifications (design review P1#5).

A lightweight frameless overlay anchored to a parent widget, styled by the
``QFrame#toast`` / ``QLabel#toastText`` QSS rules.  Failure feedback that
previously only flashed in the status bar now stays visible for a few
seconds, and is dismissed on click.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from ..icons import icon_pixmap
from ..theme import SPACE_3
from ..theme_mode import theme_color

_DEFAULT_MS = 5000
_TOAST_GAP = SPACE_3


class Toast(QFrame):
    """One auto-dismissing notification anchored to a corner of *parent*."""

    def __init__(self, parent: QWidget, message: str, state: str = "danger",
                 duration_ms: int = _DEFAULT_MS) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        icon_name = {"danger": "triangle-alert", "warn": "triangle-alert"}.get(state, "circle-check")
        self._icon = QLabel()
        self._icon.setPixmap(icon_pixmap(icon_name, 14, theme_color("danger" if state == "danger" else "accent")))
        self._text = QLabel(message)
        self._text.setObjectName("toastText")
        if state == "danger":
            self._text.setProperty("state", "danger")

        row = QHBoxLayout(self)
        row.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        row.setSpacing(SPACE_3)
        row.addWidget(self._icon)
        row.addWidget(self._text)

        self.adjustSize()
        # Stack above any already-visible toasts in the same parent so a burst
        # of notifications no longer lands exactly on top of the previous one
        # (UI review P2-8).
        self._stack_offset = sum(
            other.height() + _TOAST_GAP
            for other in parent.findChildren(Toast)
            if other is not self and other.isVisible()
        )
        self._reposition()
        self.show()
        self.raise_()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)
        self._timer.start(duration_ms)
        # Follow the parent on resize — otherwise the toast strands mid-window
        # (or outside the visible area) when the window shrinks under it.
        parent = self.parentWidget()
        if parent is not None:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt API)
        if obj is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._reposition()
        return False

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = SPACE_3
        self.move(
            parent.width() - self.width() - margin,
            parent.height() - self.height() - margin - getattr(self, "_stack_offset", 0),
        )

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._timer.stop()
        self.close()
        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._reposition()
        super().resizeEvent(event)


def show_toast(parent: QWidget, message: str, state: str = "danger",
               duration_ms: int = _DEFAULT_MS) -> Toast:
    """Anchor a toast to *parent*'s bottom-right corner."""
    return Toast(parent, message, state, duration_ms)
