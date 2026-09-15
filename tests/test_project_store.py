"""Project store round-trip (FR-10)."""

from __future__ import annotations

import pytest

from pyitolstudio.project import PyitolProject, Unit, load_project, save_project  # noqa: E402


def _sample_project() -> PyitolProject:
    project = PyitolProject(name="演示", tree_path="tree.nwk")
    project.add_unit(
        Unit(
            type_name="dataset_colorstrip",
            label="strip",
            color="#123456",
            separator="COMMA",
            columns=["id", "value", "color"],
            data_rows=[{"id": "A", "value": "1", "color": "#ff0000"}],
            parameters={"STRIP_WIDTH": "25"},
        )
    )
    return project


def test_save_load_roundtrip(tmp_path):
    src = _sample_project()
    path = save_project(src, tmp_path / "demo")
    assert path.name == "demo.pyitolproj"
    loaded = load_project(path)
    assert loaded.name == src.name
    assert len(loaded.units) == 1
    unit = loaded.units[0]
    assert unit.type_name == "dataset_colorstrip"
    assert unit.separator == "COMMA"
    assert unit.parameters == {"STRIP_WIDTH": "25"}
    assert unit.data_rows == [{"id": "A", "value": "1", "color": "#ff0000"}]
    assert unit.unit_id == src.units[0].unit_id


def test_load_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.pyitolproj"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON"):
        load_project(bad)
    empty = tmp_path / "empty.pyitolproj"
    empty.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="规范"):
        load_project(empty)


def test_future_version_rejected(tmp_path):
    path = tmp_path / "future.pyitolproj"
    path.write_text('{"pyitolproj_version": 99, "name": "x", "units": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="版本"):
        load_project(path)


def test_load_rejects_malformed_units(tmp_path):
    path = tmp_path / "badunits.pyitolproj"
    path.write_text('{"pyitolproj_version": 1, "name": "x", "units": ["not-a-dict"]}', encoding="utf-8")
    with pytest.raises(ValueError, match="对象"):
        load_project(path)
    path.write_text('{"pyitolproj_version": 1, "name": "x", "units": {"a": 1}}', encoding="utf-8")
    with pytest.raises(ValueError, match="列表"):
        load_project(path)
