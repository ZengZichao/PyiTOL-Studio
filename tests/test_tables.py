"""Pure helpers behind the data grid (design book §9.2 regression list).

Column resolution and clipboard parsing are deliberately Qt-free, so they are
tested here rather than through the widget layer.
"""

from __future__ import annotations

from pyitolstudio.tables import (
    MAX_EDIT_COLS,
    MAX_EDIT_ROWS,
    PASTE_COLUMNS,
    PASTE_EMPTY,
    PASTE_OK,
    column_labels,
    columns_acceptable,
    detect_separator,
    is_numeric_column,
    parse_pasted_table,
    resolve_columns,
    split_row,
    within_edit_envelope,
)

COLORSTRIP = ["id", "value", "color"]


# ---------------------------------------------------------------------------
# IDL → column definitions
# ---------------------------------------------------------------------------
def test_resolve_columns_follows_the_idl_order():
    frame = ["id", "value", "color"]
    assert resolve_columns(frame, COLORSTRIP, None) == COLORSTRIP


def test_resolve_columns_appends_columns_the_idl_does_not_know():
    """Learned data must never lose a column just because the IDL omits it."""
    frame = ["id", "value", "color", "note"]
    assert resolve_columns(frame, COLORSTRIP, None) == ["id", "value", "color", "note"]


def test_resolve_columns_keeps_the_dynamic_tail_together():
    frame = ["id", "value_1", "value_2", "value_3"]
    assert resolve_columns(frame, ["id", "value_1"], "value_N") == frame


def test_resolve_columns_without_an_idl_passes_the_frame_through():
    assert resolve_columns(["a", "b"], [], None) == ["a", "b"]


def test_column_labels_reuse_the_label_of_the_column_they_extend():
    labels = column_labels(["id", "value_7"], ["id", "value_1"], ["树 ID", "数值列 ×N"])
    assert labels == ["树 ID", "数值列 ×N"]


def test_column_labels_fall_back_to_the_key():
    assert column_labels(["mystery"], ["id"], ["树 ID"]) == ["mystery"]


# ---------------------------------------------------------------------------
# Clipboard parsing
# ---------------------------------------------------------------------------
def test_parse_accepts_a_tab_separated_block():
    parsed = parse_pasted_table("A\t1\t#ff0000\nB\t2\t#00aa55", COLORSTRIP, None)
    assert parsed.status == PASTE_OK
    assert parsed.rows == [["A", "1", "#ff0000"], ["B", "2", "#00aa55"]]


def test_parse_accepts_a_comma_separated_block():
    parsed = parse_pasted_table("A,1,#ff0000", COLORSTRIP, None)
    assert parsed.status == PASTE_OK
    assert parsed.rows == [["A", "1", "#ff0000"]]


def test_parse_uses_whitespace_runs_not_single_spaces():
    """An accidental double space must not become a phantom empty column."""
    parsed = parse_pasted_table("A 1 #ff0000\nB  2 #00aa55", COLORSTRIP, None)
    assert parsed.status == PASTE_OK
    assert parsed.rows[1] == ["B", "2", "#00aa55"]


def test_parse_rejects_a_column_count_mismatch():
    """Writing a mis-shaped block would corrupt every row after the first."""
    parsed = parse_pasted_table("A\t1", COLORSTRIP, None)
    assert parsed.status == PASTE_COLUMNS
    assert (parsed.expected_columns, parsed.received_columns) == (3, 2)


def test_parse_rejects_ragged_rows():
    parsed = parse_pasted_table("A\t1\t2\nB\t1", COLORSTRIP, None)
    assert parsed.status == PASTE_COLUMNS
    assert parsed.received_columns == 2


def test_parse_reports_an_empty_clipboard():
    assert parse_pasted_table("   \n  ", COLORSTRIP, None).status == PASTE_EMPTY
    assert parse_pasted_table("", COLORSTRIP, None).status == PASTE_EMPTY


def test_parse_allows_a_wider_block_for_dynamic_types():
    """Matrix types have an open-ended tail, so ``>=`` the fixed part is fine."""
    parsed = parse_pasted_table("A\t1\t2\t3", ["id", "value_1"], "value_N")
    assert parsed.status == PASTE_OK
    assert parsed.rows[0] == ["A", "1", "2", "3"]


def test_parse_still_rejects_a_block_narrower_than_the_fixed_part():
    parsed = parse_pasted_table("A", ["id", "value_1"], "value_N")
    assert parsed.status == PASTE_COLUMNS


def test_parse_without_an_idl_only_checks_rectangularity():
    parsed = parse_pasted_table("A\t1\nB\t2", None, None)
    assert parsed.status == PASTE_OK


def test_detect_separator_prefers_tab_then_comma_then_whitespace():
    assert detect_separator("a\tb") == "\t"
    assert detect_separator("a,b") == ","
    assert detect_separator("a b") == " "


def test_split_row_uses_whitespace_runs():
    assert split_row("a   b c", " ") == ["a", "b", "c"]
    assert split_row("a\t\tb", "\t") == ["a", "", "b"]


def test_columns_acceptable_matches_the_type_layout():
    assert columns_acceptable(3, COLORSTRIP, None)
    assert not columns_acceptable(5, COLORSTRIP, None)
    assert columns_acceptable(60, ["id", "value_1"], "value_N")
    assert not columns_acceptable(0, COLORSTRIP, None)


# ---------------------------------------------------------------------------
# Rendering / envelope
# ---------------------------------------------------------------------------
def test_is_numeric_column_drives_the_mono_face():
    assert is_numeric_column(["1", "2.5", "-3", "4e2"])
    assert not is_numeric_column(["1", "abc"])
    assert not is_numeric_column([])
    assert not is_numeric_column(["", "  "])


def test_edit_envelope_matches_the_design_budget():
    assert within_edit_envelope(MAX_EDIT_ROWS, MAX_EDIT_COLS)
    assert not within_edit_envelope(MAX_EDIT_ROWS + 1, 3)
    # heatmap60: 1 204 rows is fine, 60 columns is not — read-only channel.
    assert not within_edit_envelope(1204, 60)
