"""Form IDL generation over the whole engine registry (M0 core hypothesis)."""

from __future__ import annotations

import pytest

pyitol = pytest.importorskip("pyitol")

from pyitolstudio.adapter import build_form_idl, list_template_types  # noqa: E402
from pyitolstudio.adapter.form_idl import (  # noqa: E402
    GROUP_ORDER,
    SEPARATOR_CHOICES,
    defaults_for_idl,
    group_for,
    load_catalog,
)


def test_registry_types_all_produce_idl():
    infos = list_template_types()
    assert len(infos) >= 30, "引擎注册表类型数量异常"
    for info in infos:
        idl = build_form_idl(info.type_name)
        assert idl["header"] == info.header
        assert idl["data_columns"], info.type_name
        for field in idl["fields"]:
            assert field["widget"] in {"text", "int", "float", "color", "bool", "choice", "color_list", "text_list"}


def test_separator_choices_are_official():
    idl = build_form_idl("dataset_colorstrip")
    assert idl["separator_choices"] == list(SEPARATOR_CHOICES) == ["TAB", "SPACE", "COMMA"]


def test_colorstrip_has_expected_controls():
    idl = build_form_idl("dataset_colorstrip")
    keys = [f["key"] for f in idl["fields"]]
    assert keys[:2] == ["DATASET_LABEL", "COLOR"]
    assert "STRIP_WIDTH" in keys
    assert any(f["key"] == "STRIP_WIDTH" and f["minimum"] == 1 and f["maximum"] == 100 for f in idl["fields"])


def test_tree_ops_have_no_label_color_controls():
    idl = build_form_idl("dataset_collapse")
    keys = [f["key"] for f in idl["fields"]]
    assert "DATASET_LABEL" not in keys
    assert "COLOR" not in keys
    assert idl["data_columns"] == ["id"]


def test_defaults_extractable():
    idl = build_form_idl("dataset_colorstrip")
    defaults = defaults_for_idl(idl)
    assert defaults["STRIP_WIDTH"] == 25


# ---------------------------------------------------------------------------
# Parameter grouping (design book §5.1) — the inspector renders these buckets
# ---------------------------------------------------------------------------
def test_every_field_a_type_references_exists_in_the_catalog():
    """A type listing a key the catalog never defines loses that parameter.

    ``build_form_idl`` skips unknown keys silently, so the form would quietly
    drop the control and the value could never be edited — caught here instead.
    """
    catalog = load_catalog()
    known = set(catalog["fields"]) | set(catalog["legend_fields"])
    for type_name, entry in catalog["types"].items():
        for key in entry.get("fields", []):
            assert key in known, f"{type_name} references unknown field {key}"


def test_every_catalog_field_belongs_to_a_known_group():
    """A new catalog entry must not silently fall outside the four groups."""
    catalog = load_catalog()
    keys = list(catalog["fields"]) + list(catalog["legend_fields"])
    assert keys, "catalog is empty"
    for key in keys:
        assert group_for(key) in GROUP_ORDER, key
    # The grouping is a partition, not a sample: nothing is left unmapped.
    assert group_for("DATASET_LABEL") == "basic"
    assert group_for("COLOR") == "basic"
    assert group_for("LEGEND_TITLE") == "legend"


def test_idl_groups_cover_every_field_exactly_once():
    for info in list_template_types():
        idl = build_form_idl(info.type_name)
        grouped = [f["key"] for g in idl["groups"] for f in g["fields"]]
        # Grouping reorders (basic first, legend last) but must not drop or
        # duplicate a field.
        assert sorted(grouped) == sorted(f["key"] for f in idl["fields"]), info.type_name
        assert len(grouped) == len(set(grouped)), info.type_name
        assert [g["key"] for g in idl["groups"]] == [
            k for k in GROUP_ORDER if any(f["group"] == k for f in idl["fields"])
        ]


def test_basic_and_mapping_groups_start_expanded():
    idl = build_form_idl("dataset_heatmap")
    expanded = {g["key"]: g["expanded"] for g in idl["groups"]}
    assert expanded["basic"] is True
    assert expanded["mapping"] is True
    assert expanded["legend"] is False


def test_range_hint_is_derived_from_bounds_and_unit():
    idl = build_form_idl("dataset_colorstrip")
    fields = {f["key"]: f for f in idl["fields"]}
    assert fields["STRIP_WIDTH"]["range"] == "1–100"
    assert fields["STRIP_WIDTH"]["unit"] == "px"
    # A curated hint wins over the numeric range (prototype §5.1).
    assert fields["BORDER_WIDTH"]["hint"] == "0 表示无边框"


def test_single_sided_bounds_render_with_an_inequality():
    idl = build_form_idl("dataset_symbols")
    fields = {f["key"]: f for f in idl["fields"]}
    assert fields["MAXIMUM_SIZE"]["range"] == "≥ 0"
