#!/usr/bin/env python3
"""Collect all Lucide SVG icons used by PyiTOL Studio into the resources folder.

Reads the icon names referenced in the source code and copies the corresponding
``.svg`` files from the Lucide icon pack into ``src/pyitolstudio/resources/icons/``.

Usage::

    python scripts/collect_svg_icons.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Resolve paths relative to this script.
PROJECT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT / "src" / "pyitolstudio"
LUCIDE_DIR = PROJECT.parent / "PyiTOL-Studio-开发素材" / "lucide-1.45.0-icons"
DEST_DIR = SRC_DIR / "resources" / "icons"

# Every icon name referenced in the codebase (grep-collected).
# Includes toolbar icons, type icons, and all dynamically referenced names.
ICON_NAMES: set[str] = {
    # Toolbar
    "search", "file-plus", "folder-open", "save", "wand", "import", "eye",
    "file-output", "upload", "settings",
    # Panel toggles
    "panel-left", "panel-right", "panel-left-open", "panel-left-close",
    "panel-right-open", "panel-right-close",
    # Menus / actions
    "languages", "sun-moon", "eye-off", "trash", "grip-vertical",
    "ellipsis-vertical", "ellipsis", "chevron-left", "chevron-down",
    "chevron-right", "check", "clipboard-paste", "plus", "rotate-ccw",
    "rows-3", "circle-check", "sliders-horizontal", "key", "circle-dot",
    "terminal", "folder-tree",
    # Type icons (unit_list.py TYPE_ICONS + wizard.py TYPE_GLYPHS)
    # NOTE: Lucide 1.45.0 renamed some icons — the code maps old → new names.
    "rectangle-horizontal", "chart-no-axes-column", "chart-column",
    "grid-3x3", "grid-2x2", "shapes", "chart-pie", "chart-line",
    "network", "ruler", "type", "palette", "scissors",
    "move-horizontal", "info", "book-open", "dna", "layout-grid",
    "settings-2", "text-align-justify", "brackets", "timer", "git-branch",
    "blend", "square", "image", "move-up-right", "text-cursor",
    # Status chips (table_editor.py)
    "circle-dashed", "triangle-alert",
}


def main() -> int:
    if not LUCIDE_DIR.is_dir():
        print(f"ERROR: Lucide icon source not found: {LUCIDE_DIR}")
        return 1

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    copied = 0
    for name in sorted(ICON_NAMES):
        src = LUCIDE_DIR / f"{name}.svg"
        if not src.is_file():
            missing.append(name)
            continue
        dst = DEST_DIR / f"{name}.svg"
        shutil.copy2(src, dst)
        copied += 1

    if missing:
        print(f"WARNING: {len(missing)} icon(s) not found in Lucide source:")
        for name in missing:
            print(f"  - {name}.svg")

    # Write a manifest (sorted list of icon names) for the build to verify.
    manifest = DEST_DIR / "_manifest.txt"
    manifest.write_text(
        "\n".join(sorted(ICON_NAMES)) + "\n", encoding="utf-8"
    )

    print(f"Collected {copied}/{len(ICON_NAMES)} SVG icons into {DEST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
