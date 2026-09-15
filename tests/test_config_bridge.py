"""Config bridge: field parity with engine config.example.yaml (FR-7)."""

from __future__ import annotations

import pytest

pyitol = pytest.importorskip("pyitol")
yaml = pytest.importorskip("yaml")

from pyitolstudio.adapter.config_bridge import (  # noqa: E402
    build_config_yaml,
    config_idl,
    validate_config_values,
)


def test_config_yaml_parses_and_roundtrips():
    values = {f["key"]: f["default"] for f in config_idl()}
    values["default_format"] = "pdf"
    payload = yaml.safe_load(build_config_yaml(values))
    assert payload["default_format"] == "pdf"
    assert payload["api_key_file"] == ".itolapi.key"
    assert payload["taxonomy_delimiter_mode"] == "segment"


def test_engine_config_example_keys_covered():
    """Every key in the engine's config.example.yaml must exist in the GUI
    editor (development plan FR-7: 对齐全字段)."""
    import os
    from pathlib import Path

    candidates: list[Path] = []
    env_src = os.environ.get("PYITOL_ENGINE_SRC")
    if env_src:
        candidates.append(Path(env_src) / "config.example.yaml")
        candidates.append(Path(env_src).parent / "config.example.yaml")
    # Walk up from the imported pyitol package: …/<engine>/src/pyitol/__init__.py
    engine_root = Path(pyitol.__file__).resolve().parent.parent.parent
    candidates.append(engine_root / "config.example.yaml")
    candidates.append(engine_root.parent / "config.example.yaml")

    example = next((c for c in candidates if c.exists()), None)
    if example is None:  # truly absent (e.g. pyitol installed as a wheel)
        pytest.skip("未找到引擎 config.example.yaml（可设 PYITOL_ENGINE_SRC 指向引擎仓库）")
    keys = set(yaml.safe_load(example.read_text(encoding="utf-8")))
    gui_keys = {f["key"] for f in config_idl()}
    missing = keys - gui_keys
    assert not missing, f"GUI 配置编辑器缺少字段：{missing}"


def test_validation_rejects_bad_format():
    errors = validate_config_values({"default_format": "jpeg", "log_level": "INFO", "multi_tree_mode": "ask"})
    assert any("default_format" in e for e in errors)
    assert validate_config_values({"default_format": "svg"}) == []


def test_config_yaml_quotes_special_characters():
    """Regression: paths containing YAML-special characters used to be written
    unquoted, producing a config file that fails to parse or misparses."""
    values = {f["key"]: f["default"] for f in config_idl()}
    values["log_file"] = "/tmp/logs: 2026 #run.log"  # colon, spaces, hash
    values["api_key_file"] = ""  # must stay an explicit empty string, not null
    payload = yaml.safe_load(build_config_yaml(values))
    assert payload["log_file"] == "/tmp/logs: 2026 #run.log"
    assert payload["api_key_file"] == ""
    # empty string is written quoted so it parses as "" instead of null
    assert build_config_yaml(values).count('api_key_file: ""') == 1


def test_validation_rejects_bad_naming_and_delimiter():
    errors = validate_config_values({"name_format": "bogus", "taxonomy_delimiter_mode": "bogus"})
    assert any("name_format" in e for e in errors)
    assert any("taxonomy_delimiter_mode" in e for e in errors)


def test_directory_fields_use_dir_widget():
    """Directory fields must be browsable as directories, not files."""
    widgets = {f["key"]: f["widget"] for f in config_idl()}
    assert widgets["output_directory"] == "dir"
    assert widgets["template_directory"] == "dir"
    assert widgets["tree_directory"] == "dir"
    assert widgets["api_key_file"] == "path"
