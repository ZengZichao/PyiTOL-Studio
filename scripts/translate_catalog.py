#!/usr/bin/env python3
"""Inject English translations into the bundled parameter catalog.

``resources/param_ranges.json`` shipped Chinese-only field labels. With
English as the default UI language the inspector and the data-grid headers
must speak English too, so this script adds parallel ``label_en`` /
``help_en`` / ``data_column_labels_en`` entries; :mod:`form_idl` picks the
string for the active locale at IDL-build time.

Idempotent: re-running overwrites the ``*_en`` keys with these tables.

Run from the project root::

    python scripts/translate_catalog.py
"""

from __future__ import annotations

import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / "src" / "pyitolstudio" / "resources" / "param_ranges.json"

# key → (label_en, help_en)
FIELDS: dict[str, tuple[str, str]] = {
    "DATASET_LABEL": ("Dataset label", "Name shown next to the tree"),
    "COLOR": ("Colour", "Dataset base colour (#hex)"),
    "COLOR_MAX": ("Max colour", "Colour for the upper value limit"),
    "COLOR_MID": ("Mid colour", "Colour for the middle value (requires USE_MID_COLOR)"),
    "COLOR_MIN": ("Min colour", "Colour for the lower value limit"),
    "USE_MID_COLOR": ("Use mid colour", "0/1: three-colour gradient"),
    "STRIP_WIDTH": ("Strip width (px)", "Strip/heatmap width in pixels, 1–100"),
    "MARGIN": ("Margin (px)", "Spacing to the neighbouring dataset"),
    "BORDER_WIDTH": ("Border width", "0 means no border"),
    "BORDER_COLOR": ("Border colour", "#hex"),
    "SHOW_INTERNAL": ("Show internal nodes", "0/1"),
    "COLOR_BRANCHES": ("Colour target", "0 = colour leaves, 1 = colour branches"),
    "HEIGHT_FACTOR": ("Height factor", "Relative height multiplier"),
    "WIDTH": ("Width (px)", "Plot area width"),
    "SIZE_FACTOR": ("Size factor", "Relative size multiplier"),
    "MAXIMUM_SIZE": ("Maximum size", "Largest symbol/pie radius"),
    "MAXIMUM_SYMBOL_SIZE": ("Max symbol size", "Largest external symbol in pixels (iTOL v7 default 35)"),
    "FIELD_COLORS": ("Field colours", "Space-separated #hex list, one per data column"),
    "FIELD_LABELS": ("Field labels", "Space-separated, one per data column"),
    "FIELD_SHAPES": ("Field shapes", "Space-separated shape names (e.g. circle square)"),
    "SYMBOL_SPACING": ("Symbol spacing", "Spacing factor between symbols"),
    "BAR_SHIFT": ("Bar shift", "Global horizontal offset"),
    "BAR_ZERO": ("Zero position", "Baseline value of the bar chart"),
    "ALIGN_FIELDS": ("Align fields", "0/1: share one baseline across bars"),
    "DATASET_SCALE": ("Value scale", "List of tick labels; empty = automatic"),
    "SHOW_TREE": ("Show column tree", "0/1: heatmap column clustering tree"),
    "FIELD_TREE": ("Column tree Newick", "Newick string describing the column structure"),
    "TREE_HEIGHT": ("Column tree height", "Pixels"),
    "ALIGN_TO_TREE": ("Align to tree", "0/1"),
    "LABEL_ROTATION": ("Label rotation", "Angle"),
    "SHAPE_TYPE": ("Shape type", "External shape type"),
    "COLOR_FILL": ("Fill colour", "#hex"),
    "TRANSPARENT_FILL": ("Transparent fill", "0/1"),
    "HORIZONTAL_GRID": ("Horizontal grid", "0/1"),
    "VERTICAL_GRID": ("Vertical grid", "0/1"),
    "SHOW_VALUES": ("Show values", "0/1"),
    "SHAPE_SPACING": ("Shape spacing", "Spacing between neighbouring shapes"),
    "DRAW_ARROWS": ("Draw arrows", "0/1: arrowheads on connection lines"),
    "ARROW_SIZE": ("Arrow size", "Pixels"),
    "CENTER_CURVES": ("Centre curves", "0/1: Bézier curves"),
    "CURVE_ANGLE": ("Curve angle", "Corner angle of connection curves"),
    "MAXIMUM_LINE_WIDTH": ("Max line width", "Upper bound after normalising by the data"),
    "BACKBONE_COLOR": ("Backbone colour", "Colour of the protein-domain backbone"),
    "SHOW_DOMAIN_LABELS": ("Show domain labels", "0/1"),
    "LABELS_ON_TOP": ("Labels on top", "0/1"),
    "DEFAULT_LINE_COLOR": ("Default line colour", "#hex"),
    "DEFAULT_DOT_COLOR": ("Default dot colour", "#hex"),
    "DEFAULT_CONNECTION_COLOR": ("Default connection colour",
                                 "Default connection line colour (#hex / RGB / RGBA; iTOL v7 default #aabbcc)"),
    "DOT_SIZE": ("Dot size", "Pixels"),
    "LINE_WIDTH": ("Line width", "Pixels"),
    "SHOW_DOTS": ("Show dots", "0/1"),
    "SHOW_LINE": ("Show line", "0/1"),
    "VERTICAL_CHART": ("Vertical chart", "0/1"),
    "CHART_SHIFT": ("Chart shift", "Global horizontal offset"),
    "AXIS_X": ("X axis", "min step max or a tick list"),
    "AXIS_Y": ("Y axis", "Tick list"),
    "LINE_COLORS": ("Line colours", "Space-separated #hex list"),
    "HIGHLIGHT_TYPE": ("Highlight type", "e.g. box"),
    "HIGHLIGHT_REFERENCES": ("Highlight references", "List of reference-sequence numbers"),
    "MARK_REFERENCES": ("Mark references", "0/1"),
    "REFERENCE_BOX_BORDER_COLOR": ("Reference box border", "#hex"),
    "REFERENCE_BOX_BORDER_WIDTH": ("Reference box border width", "Pixels"),
    "REFERENCE_BOX_FILL_COLOR": ("Reference box fill", "#hex"),
    "CUSTOM_COLOR_SCHEME": ("Custom colour scheme", "Per-column colouring scheme"),
    "IMAGE_ROTATION": ("Image rotation", "Angle"),
    "IMAGE_SHIFT_H": ("Horizontal shift", "Pixels"),
    "IMAGE_SHIFT_V": ("Vertical shift", "Pixels"),
    "LABEL_POSITION": ("Label position", "e.g. top/middle/bottom"),
    "LABEL_ROTATION_X": ("Label rotation", "Angle"),
    "SHOW_LABELS": ("Show labels", "0/1"),
    "SHOW_COLUMN_LABELS": ("Show column labels", "0/1: label row above matrix columns"),
    "LABELS_VERTICAL": ("Vertical labels", "0/1"),
    "FIT_LABELS": ("Fit labels", "0/1"),
    "STRAIGHT_LABELS": ("Straight labels", "0/1"),
    "LABEL_OUTLINE_COLOR": ("Label outline colour", "#hex"),
    "LABEL_OUTLINE_WIDTH": ("Label outline width", "Pixels"),
    "LABEL_SHIFT_X": ("Label horizontal shift", "Pixels"),
    "LABEL_SHIFT_Y": ("Label vertical shift", "Pixels"),
    "LABEL_SIZE_FACTOR": ("Label size factor", "Relative font size"),
    "RANGE_TYPE": ("Range type", "box/brace/…"),
    "RANGE_COVER": ("Range coverage", "What the range covers"),
    "COVER_DATASETS": ("Cover datasets", "0/1"),
    "COVER_LABELS": ("Cover labels", "0/1"),
    "BRACKET_STYLE": ("Bracket style", "box/bracket"),
    "BRACKET_SIZE": ("Bracket size", "Pixels"),
    "BRACKET_SHIFT": ("Bracket shift", "Pixels"),
    "BRACKET_BEHIND_DATASETS": ("Bracket behind datasets", "0/1"),
    "AUTO_SCALE": ("Auto scale", "0/1"),
    "SCALING_FACTOR": ("Scaling factor", "Timeline scaling"),
    "POSITION_ABOVE": ("Above the tree", "0/1"),
    "SHOW_RANGE_LABELS": ("Show range labels", "0/1"),
    "SHOW_VALUE_LABELS": ("Show value labels", "0/1"),
    "RANGE_LABEL_COLOR": ("Range label colour", "#hex"),
    "RANGE_LABEL_AUTO_COLOR": ("Auto range label colour", "0/1"),
    "RANGE_LABEL_POSITION": ("Range label position", "e.g. center"),
    "RANGE_LABEL_ROTATION": ("Range label rotation", "Angle"),
    "RANGE_LABEL_SHIFT_X": ("Range label horizontal shift", "Pixels"),
    "RANGE_LABEL_SHIFT_Y": ("Range label vertical shift", "Pixels"),
    "RANGE_LABEL_SIZE": ("Range label size", "Pixels"),
    "VALUE_LABEL_ROTATION": ("Value label rotation", "Angle"),
    "VALUE_LABEL_SHIFT": ("Value label shift", "Pixels"),
    "VALUE_LABEL_SIZE_FACTOR": ("Value label size factor", "Relative font size"),
    "STRIP_WIDTH_LEGACY": ("Strip width", "Pixels"),
}

LEGEND: dict[str, tuple[str, str]] = {
    "LEGEND_TITLE": ("Legend title", "Heading of the legend block"),
    "LEGEND_POSITION_X": ("Legend X (%)", "0–100, percentage of the canvas"),
    "LEGEND_POSITION_Y": ("Legend Y (%)", "0–100, percentage of the canvas"),
    "LEGEND_HORIZONTAL": ("Horizontal legend", "0/1"),
    "LEGEND_SHAPES": ("Legend shapes", "Space-separated (circle/square/star …)"),
    "LEGEND_COLORS": ("Legend colours", "Space-separated #hex list"),
    "LEGEND_LABELS": ("Legend labels", "Space-separated"),
    "LEGEND_SHAPE_SCALES": ("Legend shape scales", "Space-separated numbers"),
}

# Enumerated fields whose option labels are UI copy too.
CHOICE_LABELS: dict[str, list[str]] = {
    "COLOR_BRANCHES": ["Leaves", "Branches"],
}

COLUMNS: dict[str, list[str]] = {
    "dataset_colorstrip": ["Tree ID", "Strip label", "Colour #hex (COL prefix allowed)"],
    "dataset_simple_bar": ["Tree ID", "Value"],
    "dataset_multibar": ["Tree ID", "Value columns ×N"],
    "dataset_heatmap": ["Tree ID", "Value columns ×N"],
    "dataset_binary": ["Tree ID", "0/1 columns ×N"],
    "dataset_tree_colors": ["Tree ID", "range/branch/clade/label", "Colour #hex",
                            "Style (normal/dashed …)", "Size (optional)"],
    "dataset_labels": ["Tree ID", "New label"],
    "dataset_gradient": ["Tree ID", "Value", "Colour scale (optional)"],
    "dataset_symbols": ["Tree ID", "Shape", "Size", "Colour", "Label (optional)"],
    "dataset_piechart": ["Tree ID", "Share columns ×N"],
    "dataset_boxplot": ["Tree ID", "Five-number columns ×N"],
    "dataset_text": ["Tree ID", "Text"],
    "dataset_externalshape": ["Tree ID", "Shape", "Size", "Colour", "Label (optional)"],
    "dataset_connections": ["Source ID", "Target ID", "Colour (optional)",
                            "Width (optional)", "Style (optional)"],
    "dataset_domains": ["Tree ID", "Start", "End", "Shape", "Label", "Colour (optional)"],
    "dataset_alignment": ["Tree ID", "Sequence"],
    "dataset_image": ["Tree ID", "Image path", "Width (optional)"],
    "dataset_linechart": ["Tree ID", "Position", "Value"],
    "dataset_tanglegram": ["Tree A ID", "Tree B ID", "Colour (optional)", "Width (optional)"],
    "dataset_arrows": ["Tree ID", "Position", "Value"],
    "dataset_style": ["Tree ID", "Type", "Colour", "Style"],
    "dataset_range": ["Tree ID", "Label", "Colour"],
    "dataset_timescale": ["Time point", "Label (optional)"],
    "dataset_spacing": ["Tree ID", "Spacing factor"],
    "dataset_popup_info": ["Tree ID", "Popup title", "Popup content (HTML)"],
    "dataset_collapse": ["Node ID"],
    "dataset_prune": ["Node ID (keep list)"],
    "dataset_meme": ["Tree ID", "Start", "End", "Motif name"],
    "dataset_placement": ["Tree ID", "Position", "Count", "Label (optional)", "Colour (optional)"],
}


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    missing = [k for k in catalog["fields"] if k not in FIELDS]
    extra = [k for k in FIELDS if k not in catalog["fields"]]
    if missing or extra:
        raise SystemExit(
            f"field tables out of sync with the catalog — missing: {missing}, extra: {extra}"
        )
    missing = [k for k in catalog.get("legend_fields", {}) if k not in LEGEND]
    if missing:
        raise SystemExit(f"legend fields missing from LEGEND: {missing}")
    missing = [k for k in catalog.get("types", {}) if k not in COLUMNS]
    if missing:
        raise SystemExit(f"types missing from COLUMNS: {missing}")

    for key, entry in catalog["fields"].items():
        label_en, help_en = FIELDS[key]
        entry["label_en"] = label_en
        entry["help_en"] = help_en
        if key in CHOICE_LABELS:
            entry["choice_labels_en"] = CHOICE_LABELS[key]
    for key, entry in catalog.get("legend_fields", {}).items():
        label_en, help_en = LEGEND[key]
        entry["label_en"] = label_en
        entry["help_en"] = help_en
    for key, entry in catalog.get("types", {}).items():
        columns = entry.get("data_column_labels", [])
        translated = COLUMNS[key]
        if len(columns) != len(translated):
            raise SystemExit(
                f"{key}: catalog has {len(columns)} column labels, table has {len(translated)}"
            )
        entry["data_column_labels_en"] = translated

    CATALOG.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"translated {len(FIELDS)} fields, {len(LEGEND)} legend fields, "
          f"{len(COLUMNS)} type column layouts → {CATALOG.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
