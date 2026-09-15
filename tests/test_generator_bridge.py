"""Separator matrix + official SEPARATOR-line rule (FR-2, plan §10.2)."""

from __future__ import annotations

import pytest

pyitol = pytest.importorskip("pyitol")

from pyitolstudio.adapter import UnitSpec, generate_template_text, validate_separator_line  # noqa: E402


def _spec(separator: str) -> UnitSpec:
    return UnitSpec(
        type_name="dataset_colorstrip",
        label="sep_test",
        color="#123456",
        separator=separator,
        columns=["id", "value", "color"],
        data_rows=[
            {"id": "A", "value": "one", "color": "#ff0000"},
            {"id": "B", "value": "two", "color": "#00ff00"},
        ],
        parameters={"STRIP_WIDTH": 25},
    )


@pytest.mark.parametrize("separator", ["TAB", "SPACE", "COMMA"])
def test_separator_matrix(separator):
    text = generate_template_text(_spec(separator))
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines[0] == "DATASET_COLORSTRIP"
    # Official rule: the SEPARATOR line itself always uses a plain space.
    assert lines[1] == f"SEPARATOR {separator}"
    assert validate_separator_line(text) == []
    data_lines = lines[lines.index("DATA") + 1:]
    joiner = {"TAB": "\t", "SPACE": " ", "COMMA": ","}[separator]
    assert data_lines[0] == joiner.join(["A", "one", "#ff0000"])


def test_comma_values_are_rejected_not_corrupted():
    spec = _spec("COMMA")
    spec.data_rows[0]["value"] = "a,b"
    with pytest.raises(ValueError, match="分隔符"):
        generate_template_text(spec)


def test_separator_line_validator_flags_corruption():
    bad = "DATASET_COLORSTRIP\nSEPARATOR\tTAB\n"
    assert validate_separator_line(bad) != []
    assert validate_separator_line("DATASET_COLORSTRIP\nSEPARATOR SPACE\n") == []
