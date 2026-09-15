"""Generator bridge: build iTOL template text through the pyitol engine.

Only public engine APIs are used (``create_schema`` /
``TemplateGenerator``). Qt-free; all calls here run inside engine tasks.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEPARATOR_ERROR = "SEPARATOR 行必须形如 'SEPARATOR TAB'（恒用单个空格分隔，见 iTOL 官方规范）"


@dataclass
class UnitSpec:
    """Everything needed to render one annotation unit."""

    type_name: str
    label: str = ""
    color: str = "#dd4477"
    separator: str = "TAB"  # TAB / SPACE / COMMA
    columns: list[str] = field(default_factory=list)
    data_rows: list[dict[str, Any]] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    legend: dict[str, Any] = field(default_factory=dict)
    template_name: str = ""


def _check_separator_values(spec: UnitSpec) -> None:
    """Reject data values containing the active separator character.

    iTOL templates have no quoting mechanism, so such values would corrupt
    the column layout silently; fail loudly instead.
    """
    sep_char = {"TAB": "\t", "SPACE": " ", "COMMA": ","}.get(spec.separator, "\t")
    if sep_char == " ":
        return  # free text routinely contains spaces; iTOL tolerates it
    for i, row in enumerate(spec.data_rows):
        for col, value in row.items():
            if isinstance(value, str) and sep_char in value:
                raise ValueError(
                    f"第 {i + 1} 行字段 {col!r} 含分隔符 {sep_char!r}："
                    "当前分隔格式下无法安全写出，请清理数据或更换分隔格式"
                )


def _schema_from_spec(spec: UnitSpec):
    from pyitol.templates.generator import TemplateGenerator
    from pyitol.templates.schemas.base import LegendConfig, create_schema

    schema = create_schema(spec.type_name, label=spec.label, color=spec.color, separator=spec.separator)
    schema.columns = list(spec.columns)
    schema.data_rows = [dict(r) for r in spec.data_rows]
    schema.parameters.update({k: v for k, v in spec.parameters.items() if k not in ("SEPARATOR",)})

    legend = spec.legend or {}
    if any(legend.get(k) for k in legend):
        schema.legend = LegendConfig(
            title=legend.get("LEGEND_TITLE") or None,
            position_x=legend.get("LEGEND_POSITION_X") or None,
            position_y=legend.get("LEGEND_POSITION_Y") or None,
            horizontal=legend.get("LEGEND_HORIZONTAL") or None,
            shapes=_split_list(legend.get("LEGEND_SHAPES")),
            colors=_split_list(legend.get("LEGEND_COLORS")),
            labels=_split_list(legend.get("LEGEND_LABELS")),
            shape_scales=_split_list(legend.get("LEGEND_SHAPE_SCALES")),
        )

    generator = TemplateGenerator()
    generator.set_name(spec.template_name)
    generator.add_schema(schema)
    return generator


def _split_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value] if value else None
    text = str(value).strip()
    return text.split() if text else None


def generate_template_text(spec: UnitSpec) -> str:
    """Render the unit to iTOL template text via the engine."""
    _check_separator_values(spec)
    generator = _schema_from_spec(spec)
    with tempfile.TemporaryDirectory(prefix="pyitolstudio_") as tmp:
        out = Path(tmp) / "preview.txt"
        generator.write(out)
        return out.read_text(encoding="utf-8")


def export_template_file(spec: UnitSpec, output_path: str | Path) -> Path:
    """Write the unit to a template file via the engine (single write)."""
    _check_separator_values(spec)
    generator = _schema_from_spec(spec)
    return generator.write(output_path)


def validate_separator_line(text: str) -> list[str]:
    """Enforce the official rule: the SEPARATOR line is always written as
    ``SEPARATOR <NAME>`` with a single space — never with the active
    separator character."""
    errors: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.split(None, 1)[0] == "SEPARATOR":
            parts = line.split(" ")
            if len(parts) != 2 or parts[1] not in ("TAB", "SPACE", "COMMA"):
                errors.append(SEPARATOR_ERROR)
    return errors


def normalize_separator(name: str) -> str:
    """Map user-facing separator names to the engine's canonical names."""
    alias = {
        "tab": "TAB",
        "space": "SPACE",
        "comma": "COMMA",
        "\\t": "TAB",
        "制表符": "TAB",
        "空格": "SPACE",
        "逗号": "COMMA",
    }
    return alias.get(str(name).strip().lower(), str(name).strip().upper())
