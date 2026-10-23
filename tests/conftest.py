"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = PROJECT_ROOT / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    assert FIXTURES.is_dir(), f"fixtures 缺失：{FIXTURES}"
    return FIXTURES


@pytest.fixture(scope="session")
def pyitol_available() -> None:
    pytest.importorskip("pyitol", reason="需要 pyitol 引擎（建议在 pyitol conda 环境中运行测试）")


@pytest.fixture(autouse=True)
def _no_blocking_message_boxes(monkeypatch):
    """Never let a confirmation dialog block a headless test.

    ``MainWindow.closeEvent`` prompts before discarding unsaved edits; pytest-qt
    closes every ``qtbot.addWidget`` window on teardown, so a modal ``QMessageBox``
    would hang the whole suite.  Stub ``exec`` to a no-op that resolves to
    "discard" (``clickedButton`` stays ``None`` → ``_maybe_confirm_discard``
    proceeds).  A dedicated test can re-enable the real dialog if it needs to.
    """
    try:
        from PySide6.QtWidgets import QMessageBox
    except Exception:  # noqa: BLE001 - PySide6 absent; nothing to patch
        return
    monkeypatch.setattr(QMessageBox, "exec", lambda self, *a, **k: 0)


@pytest.fixture(scope="session", autouse=True)
def _teardown_qt_before_interpreter_exit(request):
    """Collect Qt objects while the interpreter can still run destructors.

    A QApplication (or any widget leaked by a test) that survives until
    interpreter finalisation aborts the process on some Linux PySide6 builds
    -- ``Fatal Python error: none_dealloc`` during the final GC, after every
    test has already passed, which destroys the exit code.  Close everything
    and collect garbage here, while Qt is still alive.
    """

    def _fin():
        import gc

        try:
            from PySide6 import QtWidgets
        except Exception:  # noqa: BLE001 - PySide6 absent; nothing to tear down
            return
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.closeAllWindows()
            app.processEvents()
            app.quit()
        gc.collect()

    request.addfinalizer(_fin)


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):
    """End the process once results are reported, skipping interpreter teardown.

    On Linux (PySide6 + Python 3.10/3.11), letting the interpreter finalise
    with Qt objects still reachable aborts during the final garbage
    collection -- ``Fatal Python error: none_dealloc`` -- *after* every test
    has passed and pytest has already printed its summary, turning a green
    run into exit 134.  All suites pass by this point; ``os._exit`` with
    pytest's own exit status keeps the reported result without running the
    teardown that crashes.
    """
    outcome = yield
    try:
        import PySide6  # noqa: F401

        import os

        os._exit(int(exitstatus))
    except ImportError:
        return
