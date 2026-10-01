"""Qt-free helpers for the data grid (design book §9.2).

Column resolution and clipboard parsing are pure functions so they can be
unit-tested without a QApplication — the design book calls both out as
regression-test targets.  ``app/table_editor.py`` is the only consumer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Editing envelope (design book §9.2): beyond this the unit is shown through
# the read-only preview channel instead of the editable model.
MAX_EDIT_ROWS = 2000
MAX_EDIT_COLS = 20

# Paste outcome codes — the GUI turns these into i18n messages.
PASTE_OK = "ok"
PASTE_EMPTY = "empty"
PASTE_COLUMNS = "columns"

_NUMERIC = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


@dataclass(frozen=True)
class ParsedTable:
    """Result of parsing pasted Excel/TSV text."""

    status: str = PASTE_OK
    rows: list[list[str]] = field(default_factory=list)
    received_columns: int = 0
    expected_columns: int = 0

    @property
    def ok(self) -> bool:
        return self.status == PASTE_OK


def resolve_columns(
    frame_columns: list[str],
    idl_columns: list[str] | None,
    dynamic: str | None = None,
) -> list[str]:
    """Order the data columns: the IDL's fixed columns first, then extras.

    The IDL decides the leading columns (``id``, ``value``, ``color`` …) and,
    for matrix types, declares a dynamic tail (``value_N``).  Anything the
    learned data carries beyond that is appended in its original order so no
    column is silently dropped.
    """
    if not idl_columns:
        return list(frame_columns)
    known = [c for c in idl_columns if c in frame_columns]
    if dynamic:
        # Dynamic tail: keep every value_*/field_* column the data actually has.
        prefix = dynamic.split("_")[0]
        tail = [c for c in frame_columns if c not in known and c.split("_")[0] == prefix]
        rest = [c for c in frame_columns if c not in known and c not in tail]
        return known + tail + rest
    return known + [c for c in frame_columns if c not in known]


def column_labels(columns: list[str], idl_columns: list[str], idl_labels: list[str]) -> list[str]:
    """Display labels for *columns*, falling back to the key itself.

    Dynamic columns reuse the label of the IDL column they extend
    (``value_7`` → the label of ``value_1``).
    """
    mapping = dict(zip(idl_columns, idl_labels, strict=False))
    labels: list[str] = []
    for column in columns:
        if column in mapping:
            labels.append(mapping[column])
            continue
        prefix = column.split("_")[0]
        fallback = next(
            (lab for key, lab in mapping.items() if key.split("_")[0] == prefix),
            column,
        )
        labels.append(fallback)
    return labels


def expected_columns(idl_columns: list[str], dynamic: str | None) -> int:
    """How many columns a pasted block must carry.

    Fixed-layout types must match exactly; matrix types accept any width
    ``>=`` the fixed part, because the tail is open-ended.
    """
    return len(idl_columns)


def columns_acceptable(count: int, idl_columns: list[str], dynamic: str | None) -> bool:
    want = expected_columns(idl_columns, dynamic)
    if count <= 0:
        return False
    return count >= want if dynamic else count == want


def detect_separator(first_line: str) -> str:
    """Pick the field separator the way a paste from Excel/TSV behaves."""
    if "\t" in first_line:
        return "\t"
    if "," in first_line:
        return ","
    return " "  # whitespace runs


def split_row(line: str, separator: str) -> list[str]:
    """Split one pasted line.

    Whitespace-separated pastes use runs (not single spaces): iTOL tokenises
    by whitespace, so an accidental double space would otherwise become a
    phantom empty column and shift every field left.
    """
    return line.split() if separator == " " else line.split(separator)


def parse_pasted_table(
    text: str,
    idl_columns: list[str] | None = None,
    dynamic: str | None = None,
) -> ParsedTable:
    """Parse clipboard text into a rectangular block of string cells.

    Rejects the block wholesale when the column count does not fit the IDL —
    writing a mis-shaped table would corrupt every row after the first.
    """
    lines = [ln for ln in (text or "").splitlines() if ln.strip() != ""]
    if not lines:
        return ParsedTable(status=PASTE_EMPTY)

    separator = detect_separator(lines[0])
    rows = [split_row(ln, separator) for ln in lines]
    received = len(rows[0])
    if idl_columns:
        want = expected_columns(idl_columns, dynamic)
        if not columns_acceptable(received, idl_columns, dynamic):
            return ParsedTable(
                status=PASTE_COLUMNS,
                received_columns=received,
                expected_columns=want,
            )
    for row in rows:
        if len(row) != received:
            return ParsedTable(
                status=PASTE_COLUMNS,
                received_columns=len(row),
                expected_columns=received,
            )
    return ParsedTable(rows=rows, received_columns=received, expected_columns=received)


def is_numeric_column(values: list[str]) -> bool:
    """Whether every non-empty cell looks like a number.

    Numeric columns are rendered in the mono face, matching the first
    (tree-ID) column — the design book's "数据可辨" rule.
    """
    seen = [v.strip() for v in values if v is not None and str(v).strip() != ""]
    if not seen:
        return False
    return all(_NUMERIC.match(v) for v in seen)


def within_edit_envelope(rows: int, columns: int) -> bool:
    """Whether a unit fits the editable grid (design book §9.2)."""
    return rows <= MAX_EDIT_ROWS and columns <= MAX_EDIT_COLS
