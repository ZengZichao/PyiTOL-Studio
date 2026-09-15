"""Learner bridge: reverse-parse existing iTOL templates back into unit
models (FR-6). Wraps ``pyitol.templates.learner.learn_template``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .generator_bridge import UnitSpec, normalize_separator

logger = logging.getLogger(__name__)

# Raw parameter keys that belong to the legend section rather than the
# plain parameter form.
_LEGEND_KEYS = (
    "LEGEND_TITLE",
    "LEGEND_POSITION_X",
    "LEGEND_POSITION_Y",
    "LEGEND_HORIZONTAL",
    "LEGEND_SHAPES",
    "LEGEND_COLORS",
    "LEGEND_LABELS",
    "LEGEND_SHAPE_SCALES",
)


@dataclass
class LearnedUnit:
    """One dataset parsed out of a template file."""

    type_name: str
    header: str
    separator: str  # canonical TAB / SPACE / COMMA
    label: str
    color: str
    columns: list[str] = field(default_factory=list)
    data_rows: list[dict[str, str]] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)
    legend: dict[str, str] = field(default_factory=dict)
    source_file: str = ""

    def to_spec(self, template_name: str = "") -> UnitSpec:
        return UnitSpec(
            type_name=self.type_name,
            label=self.label,
            color=self.color,
            separator=self.separator,
            columns=list(self.columns),
            data_rows=[dict(r) for r in self.data_rows],
            parameters=dict(self.parameters),
            legend=dict(self.legend),
            template_name=template_name or self.source_file,
        )


def learn_from_file(template_path: str | Path) -> list[LearnedUnit]:
    """Parse a template file into learned units (one per dataset block)."""
    from pyitol.templates.learner import learn_template
    from pyitol.templates.schemas.base import SEPARATOR_REVERSE

    result = learn_template(str(template_path))
    units: list[LearnedUnit] = []
    for ds in result.get("datasets", []):
        sep_char = ds.get("separator", "\t")
        parameters = {
            k: v for k, v in ds.get("parameters", {}).items() if k not in ("DATASET_LABEL", "COLOR", *_LEGEND_KEYS)
        }
        legend = {k: str(ds.get("parameters", {}).get(k, "")) for k in _LEGEND_KEYS}
        units.append(
            LearnedUnit(
                type_name=ds.get("type", ""),
                header=ds.get("header", ""),
                separator=normalize_separator(SEPARATOR_REVERSE.get(sep_char, "TAB")),
                label=str(ds.get("profile", {}).get("name", "")),
                color=str(ds.get("profile", {}).get("color", "#dd4477")),
                columns=[str(c) for c in ds.get("columns", [])],
                data_rows=[{k: str(v) for k, v in row.items()} for row in ds.get("data", [])],
                parameters=parameters,
                legend=legend,
                source_file=Path(template_path).name,
            )
        )
    if not units:
        raise ValueError(f"未在文件中找到可识别的模板数据集：{template_path}")
    return units


def to_form_values(unit: LearnedUnit, idl: dict[str, Any]) -> dict[str, Any]:
    """Map a learned unit onto a form IDL: {field key: current value}.

    Fields unknown to the IDL are kept so the inspector can show them in a
    generic "其他参数" section (plan R7).
    """
    known = {f["key"] for f in idl["fields"]}
    values: dict[str, Any] = {}
    for f in idl["fields"]:
        key = f["key"]
        if key == "DATASET_LABEL":
            values[key] = unit.label
        elif key == "COLOR":
            values[key] = unit.color
        elif key in unit.legend and unit.legend[key] != "":
            values[key] = unit.legend[key]
        elif key in unit.parameters:
            values[key] = unit.parameters[key]
        else:
            values[key] = f.get("default", "")
    extra = {
        k: v
        for k, v in unit.parameters.items()
        if k not in known and k not in ("DATASET_LABEL", "COLOR")
    }
    values["__extra_params__"] = extra
    values["__separator__"] = unit.separator
    return values
