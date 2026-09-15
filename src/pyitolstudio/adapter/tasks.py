"""Background task runner: every engine call goes through a QThread worker
(thread discipline from development plan §5.6)."""

from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal


class EngineTask(QThread):
    """Run ``fn(*args, **kwargs)`` off the UI thread.

    Emits ``finished_with(result)`` on success or ``failed(message)`` with a
    friendly error string. ``progress(message)`` may be emitted by the job
    via the optional ``progress_cb`` keyword.
    """

    finished_with = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, parent=None, **kwargs: Any) -> None:
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:  # noqa: D102
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001 - boundary converts to UI signal
            detail = f"{exc}" or exc.__class__.__name__
            if isinstance(exc, (RuntimeError, ValueError)):
                message = detail
            else:
                message = f"{exc.__class__.__name__}: {detail}"
            traceback.print_exc()
            self.failed.emit(message)
            return
        self.finished_with.emit(result)
