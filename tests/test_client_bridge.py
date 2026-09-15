"""API-key resolution order (FR-8 security rule: env var beats key file)."""

from __future__ import annotations

from pyitolstudio.adapter.client_bridge import resolve_api_key


def test_env_var_takes_precedence(monkeypatch, tmp_path):
    key_file = tmp_path / "itol.key"
    key_file.write_text("file-key\n", encoding="utf-8")
    monkeypatch.setenv("ITOL_API_KEY", " env-key ")
    assert resolve_api_key(str(key_file)) == "env-key"


def test_key_file_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("ITOL_API_KEY", raising=False)
    key_file = tmp_path / "itol.key"
    key_file.write_text("file-key\n", encoding="utf-8")
    assert resolve_api_key(str(key_file)) == "file-key"


def test_missing_everywhere_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("ITOL_API_KEY", raising=False)
    assert resolve_api_key(str(tmp_path / "missing.key")) is None
    assert resolve_api_key(None) is None
    assert resolve_api_key("") is None
