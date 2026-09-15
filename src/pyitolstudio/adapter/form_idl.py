"""Declarative form IDL builder (development plan §5.4).

Combines three sources into a single declarative description of the
parameter form for one template type:

1. the pyitol ``TemplateRegistry`` (header, required columns,
   label/color flags);
2. the bundled parameter catalog (``resources/param_ranges.json``);
3. universal legend fields shared by dataset types.

The GUI renders controls purely from this IDL; adding or changing a
template type in the engine requires no GUI code changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .registry import get_type_info

WIDGET_CHOICES = frozenset({"text", "int", "float", "color", "bool", "choice", "color_list", "text_list"})

# Separator choices are fixed by the iTOL format (FR-2).
SEPARATOR_CHOICES = ("TAB", "SPACE", "COMMA")

# ---------------------------------------------------------------------------
# Parameter groups (design book §5.1: 基本信息 / 数据映射 / 外观 / 图例)
#
# The grouping is presentation metadata, so it lives here rather than in the
# engine-parameter catalog.  Group *labels* are UI copy and live in i18n
# (``inspector.group.*``); this table only maps catalog keys to group keys, so
# adding a template type still needs zero GUI code.
# ---------------------------------------------------------------------------
GROUP_ORDER = ("basic", "mapping", "appearance", "legend")

# Groups expanded on first paint (design book §5.1: "默认展开前两组").
GROUP_EXPANDED_BY_DEFAULT = frozenset({"basic", "mapping"})

_BASIC_FIELDS = frozenset({"DATASET_LABEL", "COLOR"})

# How data becomes visual encoding: colour ramps, scales, ranges, thresholds
# and field↔column mapping.  Everything else (except basic/legend) is 外观.
_MAPPING_FIELDS = frozenset(
    {
        "COLOR_MIN",
        "COLOR_MID",
        "COLOR_MAX",
        "USE_MID_COLOR",
        "COLOR_BRANCHES",
        "SIZE_FACTOR",
        "MAXIMUM_SIZE",
        "MAXIMUM_SYMBOL_SIZE",
        "MAXIMUM_LINE_WIDTH",
        "FIELD_COLORS",
        "FIELD_LABELS",
        "FIELD_SHAPES",
        "BAR_ZERO",
        "BAR_SHIFT",
        "ALIGN_FIELDS",
        "DATASET_SCALE",
        "AUTO_SCALE",
        "SCALING_FACTOR",
        "SHOW_TREE",
        "FIELD_TREE",
        "TREE_HEIGHT",
        "ALIGN_TO_TREE",
        "AXIS_X",
        "AXIS_Y",
        "HIGHLIGHT_TYPE",
        "HIGHLIGHT_REFERENCES",
        "MARK_REFERENCES",
        "REFERENCE_BOX_BORDER_COLOR",
        "REFERENCE_BOX_BORDER_WIDTH",
        "REFERENCE_BOX_FILL_COLOR",
        "CUSTOM_COLOR_SCHEME",
        "RANGE_TYPE",
        "RANGE_COVER",
        "COVER_DATASETS",
        "COVER_LABELS",
        "BRACKET_STYLE",
        "BRACKET_SIZE",
        "BRACKET_SHIFT",
        "BRACKET_BEHIND_DATASETS",
    }
)

# Unit *keys* (not copy): the inspector renders them through ``tr()``.
_FIELD_UNITS = {
    "STRIP_WIDTH": "px",
    "STRIP_WIDTH_LEGACY": "px",
    "MARGIN": "px",
    "BORDER_WIDTH": "px",
    "WIDTH": "px",
    "TREE_HEIGHT": "px",
    "MAXIMUM_SYMBOL_SIZE": "px",
    "DOT_SIZE": "px",
    "LINE_WIDTH": "px",
    "ARROW_SIZE": "px",
    "BRACKET_SIZE": "px",
    "RANGE_LABEL_SIZE": "px",
    "LABEL_OUTLINE_WIDTH": "px",
    "REFERENCE_BOX_BORDER_WIDTH": "px",
    "BAR_SHIFT": "px",
    "CHART_SHIFT": "px",
    "IMAGE_SHIFT_H": "px",
    "IMAGE_SHIFT_V": "px",
    "LABEL_SHIFT_X": "px",
    "LABEL_SHIFT_Y": "px",
    "RANGE_LABEL_SHIFT_X": "px",
    "RANGE_LABEL_SHIFT_Y": "px",
    "VALUE_LABEL_SHIFT": "px",
    "LABEL_ROTATION": "deg",
    "LABEL_ROTATION_X": "deg",
    "IMAGE_ROTATION": "deg",
    "RANGE_LABEL_ROTATION": "deg",
    "VALUE_LABEL_ROTATION": "deg",
    "CURVE_ANGLE": "deg",
    "LEGEND_POSITION_X": "percent",
    "LEGEND_POSITION_Y": "percent",
    "HEIGHT_FACTOR": "factor",
    "SIZE_FACTOR": "factor",
    "LABEL_SIZE_FACTOR": "factor",
    "VALUE_LABEL_SIZE_FACTOR": "factor",
    "SCALING_FACTOR": "factor",
    "SYMBOL_SPACING": "factor",
    "SHAPE_SPACING": "factor",
}

# Curated note overrides where the range is not the useful hint.  Kept to the
# cases the prototype itself shows; the generic path derives "unit · min–max".
_FIELD_HINTS = {
    "BORDER_WIDTH": "0 表示无边框",
}


def group_for(key: str) -> str:
    """Which inspector group a catalog parameter belongs to."""
    if key in _BASIC_FIELDS:
        return "basic"
    if key.startswith("LEGEND_"):
        return "legend"
    if key in _MAPPING_FIELDS:
        return "mapping"
    return "appearance"


def _number(value: float) -> str:
    """Render a bound without a trailing ``.0`` (1.0 → "1")."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


@dataclass(frozen=True)
class FieldSpec:
    """One form control description."""

    key: str
    label: str
    widget: str
    default: Any = ""
    required: bool = False
    choices: tuple[str, ...] = ()
    choice_labels: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    help_text: str = ""
    group: str = "appearance"
    unit: str = ""
    hint: str = ""

    @property
    def range_text(self) -> str:
        """Language-neutral range part of the field note ("1–100", "≥ 0")."""
        if self.minimum is None and self.maximum is None:
            return ""
        if self.minimum is not None and self.maximum is not None:
            return f"{_number(self.minimum)}–{_number(self.maximum)}"
        if self.minimum is not None:
            return f"≥ {_number(self.minimum)}"
        return f"≤ {_number(self.maximum)}"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "widget": self.widget,
            "default": self.default,
            "required": self.required,
            "group": self.group,
        }
        if self.choices:
            d["choices"] = list(self.choices)
        if self.choice_labels:
            d["choice_labels"] = list(self.choice_labels)
        if self.minimum is not None:
            d["minimum"] = self.minimum
        if self.maximum is not None:
            d["maximum"] = self.maximum
        if self.range_text:
            d["range"] = self.range_text
        if self.unit:
            d["unit"] = self.unit
        if self.hint:
            d["hint"] = self.hint
        if self.help_text:
            d["help"] = self.help_text
        return d


_CATALOG: dict[str, Any] | None = None


def load_catalog() -> dict[str, Any]:
    """Load and cache the bundled parameter catalog."""
    global _CATALOG  # noqa: PLW0603
    if _CATALOG is None:
        from ..resources import resource_path  # noqa: PLC0415

        with open(resource_path("param_ranges.json"), encoding="utf-8") as fh:
            _CATALOG = json.load(fh)
    return _CATALOG


def _spec_from_entry(key: str, entry: dict[str, Any]) -> FieldSpec:
    widget = entry.get("widget", "text")
    if widget not in WIDGET_CHOICES:
        widget = "text"
    minimum = entry.get("min")
    maximum = entry.get("max")
    return FieldSpec(
        key=key,
        label=entry.get("label", key),
        widget=widget,
        default=entry.get("default", ""),
        choices=tuple(str(c) for c in entry.get("choices", ())),
        choice_labels=tuple(entry.get("choice_labels", ())),
        minimum=None if minimum is None else float(minimum),
        maximum=None if maximum is None else float(maximum),
        help_text=entry.get("help", ""),
        group=group_for(key),
        unit=_FIELD_UNITS.get(key, ""),
        hint=_FIELD_HINTS.get(key, ""),
    )


def build_form_idl(type_name: str) -> dict[str, Any]:
    """Build the declarative form IDL for one template type.

    Returns a dict with:
        type_name, header, group_label, separator_choices,
        uses_label_color, fields (list of FieldSpec dicts),
        data_columns, data_column_labels, data_columns_dynamic
    """
    info = get_type_info(type_name)
    catalog = load_catalog()
    catalog_types = catalog.get("types", {})
    entry = catalog_types.get(type_name)
    if entry is None:
        entry = {
            "fields": catalog.get("fallback", {}).get("fields", []),
            "data_columns": ["id"],
            "data_column_labels": ["树 ID"],
        }

    fields: list[FieldSpec] = []
    if info.wizard_supported:
        # Label + color are handled as explicit leading controls (unless the
        # registry flags the type as no-label-color, e.g. tree operations).
        if not info.no_label_color:
            fields.append(_spec_from_entry("DATASET_LABEL", catalog["fields"]["DATASET_LABEL"]))
            fields.append(_spec_from_entry("COLOR", catalog["fields"]["COLOR"]))
        for key in entry.get("fields", []):
            if key in ("DATASET_LABEL", "COLOR"):
                continue  # already added / suppressed above
            spec_entry = catalog["fields"].get(key)
            if spec_entry is not None:
                fields.append(_spec_from_entry(key, spec_entry))
        # Legend controls for dataset types that render a legend.
        if info.group in ("datasets", "extensions"):
            for key, spec_entry in catalog.get("legend_fields", {}).items():
                fields.append(_spec_from_entry(key, spec_entry))

    field_dicts = [f.to_dict() for f in fields]
    return {
        "type_name": type_name,
        "header": info.header,
        "group_label": info.group_label,
        "wizard_supported": info.wizard_supported,
        "no_label_color": info.no_label_color,
        "separator_choices": list(SEPARATOR_CHOICES),
        "fields": field_dicts,
        # Same fields, bucketed for the collapsible inspector (design book
        # §5.1).  Empty groups are dropped so a type only shows what it has.
        "groups": [
            {
                "key": group_key,
                "label_key": f"inspector.group.{group_key}",
                "expanded": group_key in GROUP_EXPANDED_BY_DEFAULT,
                "fields": [f for f in field_dicts if f["group"] == group_key],
            }
            for group_key in GROUP_ORDER
            if any(f["group"] == group_key for f in field_dicts)
        ],
        "data_columns": list(entry.get("data_columns", ["id"])),
        "data_column_labels": list(entry.get("data_column_labels", ["树 ID"])),
        "data_columns_dynamic": entry.get("data_columns_dynamic"),
    }


def defaults_for_idl(idl: dict[str, Any]) -> dict[str, Any]:
    """Extract a flat {field key: default value} mapping from an IDL."""
    return {f["key"]: f["default"] for f in idl["fields"] if f["default"] != ""}
