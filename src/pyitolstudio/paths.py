"""Path safety helpers shared by dialogs and workers (plan R6).

Qt-free so the rules can be tested headlessly. Paths coming from the
native file dialogs are user-authorized; the rules only guarantee that a
path is canonical and contains no ``..`` traversal segment — an allowlist
of write roots would wrongly reject legitimate destinations such as
external volumes.
"""

from __future__ import annotations

import os


def normalize_input_path(raw: str | None) -> str | None:
    """Normalize a dialog- or user-provided path; ``None`` on traversal.

    ``..`` segments are checked *before* normalization: ``os.path.normpath``
    would silently collapse ``/tmp/a/../../etc`` into ``/etc``, rewriting a
    traversal instead of rejecting it.
    """
    if not raw:
        return None
    expanded = os.path.expanduser(raw)
    if ".." in expanded.split(os.sep):
        return None
    return os.path.normpath(expanded)


def writable_target(raw: str | None) -> str | None:
    """Canonicalise a path the user just confirmed in a save / export dialog.

    Every write path — project save, template export, wizard export, config
    export — routes through this single entry point so the "对话框写路径统一规范
    化" rule from the development plan (R6) actually holds across all of them,
    not just the dialogs that happened to import ``normalize_input_path``
    directly (code review P2-7).  Same guarantees: expand user, reject ``..``
    traversal before normalising, no allowlist of roots (external volumes stay
    writable).
    """
    return normalize_input_path(raw)
