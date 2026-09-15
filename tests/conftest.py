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
