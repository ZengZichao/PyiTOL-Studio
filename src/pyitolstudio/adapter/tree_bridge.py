"""Tree bridge: read reference leaf labels through the pyitol engine.

Used by the workbench table to flag annotation IDs that do not match the
loaded tree (FR-3 validation coloring). Qt-free; call on an engine task.
"""

from __future__ import annotations

from pathlib import Path


def tree_leaf_ids(tree_path: str | Path) -> set[str] | None:
    """Return the tree's tip labels, or ``None`` when the tree cannot be
    read (callers degrade to no validation).

    A missing engine dependency is *not* a data problem: conflating the two
    hid the real cause and made FR-3 validation silently disappear behind a
    "no leaf IDs, skipping" message (code review P2-8).  So the import is
    guarded separately and surfaced as an actionable error.
    """
    try:
        from pyitol.utils.tree_info import extract_tree_info  # noqa: PLC0415
    except ImportError as exc:  # dendropy / pyitol absent — environment, not data
        raise RuntimeError(
            f"读取树叶 ID 需要引擎依赖（dendropy / pyitol），当前环境缺失：{exc}"
        ) from exc
    try:
        info = extract_tree_info(str(tree_path))
    except Exception:  # noqa: BLE001 - malformed / unreadable tree → no validation
        return None
    if info is None or info.empty:
        return None
    tips = info.loc[info["is_tip"] == True, "id"]  # noqa: E712 - pandas truthiness
    ids = {str(v) for v in tips if str(v)}
    return ids or None
