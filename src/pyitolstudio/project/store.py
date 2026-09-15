"""``.pyitolproj`` project store: JSON on disk, transparent and diffable."""

from __future__ import annotations

import json
from pathlib import Path

from .model import PyitolProject

EXTENSION = ".pyitolproj"


def save_project(project: PyitolProject, path: str | Path) -> Path:
    """Serialize the project atomically (write temp, then replace)."""
    out = Path(path)
    if out.suffix != EXTENSION:
        out = out.with_suffix(EXTENSION)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(project.to_dict(), ensure_ascii=False, indent=2)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(out)
    return out


def load_project(path: str | Path) -> PyitolProject:
    """Load a project file; raises ValueError on unreadable content."""
    src = Path(path)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"工程文件不是有效的 JSON：{src}（{exc}）") from exc
    if not isinstance(data, dict) or "units" not in data:
        raise ValueError(f"工程文件结构不符合 .pyitolproj 规范：{src}")
    return PyitolProject.from_dict(data)
