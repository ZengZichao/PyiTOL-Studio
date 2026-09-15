"""Project document model (FR-10): one project = one tree + N annotation
units, mirroring the itol.toolkit "hub" concept."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from ..adapter import UnitSpec

PROJ_VERSION = 1


@dataclass
class Unit:
    """One annotation unit (= one iTOL dataset block)."""

    type_name: str
    label: str = ""
    color: str = "#dd4477"
    separator: str = "TAB"
    columns: list[str] = field(default_factory=list)
    data_rows: list[dict[str, str]] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)
    legend: dict[str, str] = field(default_factory=dict)
    unit_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: str = "manual"  # manual | learned

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
            template_name=template_name or self.label,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "type_name": self.type_name,
            "label": self.label,
            "color": self.color,
            "separator": self.separator,
            "columns": list(self.columns),
            "data_rows": [dict(r) for r in self.data_rows],
            "parameters": dict(self.parameters),
            "legend": dict(self.legend),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Unit":
        if not isinstance(data, dict):
            raise ValueError(f"注释单元条目必须是对象，实际为：{type(data).__name__}")
        known = {f for f in cls.__dataclass_fields__}  # noqa: C416
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class PyitolProject:
    """Root document: tree file + annotation units."""

    name: str = "未命名工程"
    tree_path: str = ""
    units: list[Unit] = field(default_factory=list)
    project_version: int = PROJ_VERSION

    def add_unit(self, unit: Unit) -> Unit:
        self.units.append(unit)
        return unit

    def remove_unit(self, unit_id: str) -> bool:
        before = len(self.units)
        self.units = [u for u in self.units if u.unit_id != unit_id]
        return len(self.units) < before

    def get_unit(self, unit_id: str) -> Unit | None:
        return next((u for u in self.units if u.unit_id == unit_id), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pyitolproj_version": self.project_version,
            "name": self.name,
            "tree_path": self.tree_path,
            "units": [u.to_dict() for u in self.units],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PyitolProject":
        version = int(data.get("pyitolproj_version", 1))
        if version > PROJ_VERSION:
            raise ValueError(f"工程文件版本过新（{version} > {PROJ_VERSION}），请升级 PyiTOL Studio")
        units_raw = data.get("units", [])
        if not isinstance(units_raw, list):
            raise ValueError("units 字段必须是列表")
        return cls(
            name=str(data.get("name", "未命名工程")),
            tree_path=str(data.get("tree_path", "")),
            units=[Unit.from_dict(u) for u in units_raw],
            project_version=version,
        )
