#!/usr/bin/env python3
"""(Re)generate the bundled example project.

Writes two files into ``src/pyitolstudio/resources/samples/``:

* ``example_tree.nwk``  — a small 8-leaf Newick tree
* ``example_project.pyitolproj`` — a project with two annotation units
  (colour strip + heatmap) whose row IDs all match the tree

Run from the project root::

    python scripts/make_example_project.py

The project's ``tree_path`` is stored empty on purpose: the app resolves the
sibling ``example_tree.nwk`` at load time, so the sample keeps working no
matter where the bundle is installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from pyitolstudio.project import PyitolProject, Unit, save_project  # noqa: E402

SAMPLES_DIR = PROJECT / "src" / "pyitolstudio" / "resources" / "samples"
TREE_NAME = "example_tree.nwk"
PROJECT_NAME = "example_project.pyitolproj"

TREE = (
    "((Ailuropoda:0.10,Homo_sapiens:0.12):0.08,"
    "((Mus_musculus:0.05,Rattus_norvegicus:0.07):0.06,"
    "(Danio_rerio:0.04,Drosophila:0.06):0.05):0.09,"
    "(Arabidopsis:0.11,Oryza_sativa:0.10):0.07);"
)

IDS = [
    "Ailuropoda",
    "Homo_sapiens",
    "Mus_musculus",
    "Rattus_norvegicus",
    "Danio_rerio",
    "Drosophila",
    "Arabidopsis",
    "Oryza_sativa",
]


def main() -> int:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    (SAMPLES_DIR / TREE_NAME).write_text(TREE + "\n", encoding="utf-8")

    project = PyitolProject(name="Example Project", tree_path="")

    # 1 — colour strip: one categorical mark per tip.
    strip_colors = ["#2e5cff", "#002fa7", "#8aa4ff", "#5a6472",
                    "#9aa5b4", "#0a0a0c", "#e6e9ee", "#4d74ff"]
    project.add_unit(
        Unit(
            type_name="dataset_colorstrip",
            label="Genome assembly status",
            color="#2e5cff",
            separator="TAB",
            columns=["id", "value", "color"],
            data_rows=[
                {"id": tip, "value": str(2 ** (i % 4)), "color": strip_colors[i]}
                for i, tip in enumerate(IDS)
            ],
            parameters={"COLOR_BRANCHES": "1"},
            source="manual",
        )
    )

    # 2 — heatmap: four quantitative traits per tip (values in 0–1).
    traits = ("GC", "LEN", "EXPR", "DIV")
    project.add_unit(
        Unit(
            type_name="dataset_heatmap",
            label="Genome traits",
            color="#002fa7",
            separator="TAB",
            columns=["id", *traits],
            data_rows=[
                {
                    "id": tip,
                    "GC": f"{0.40 + 0.07 * ((i * 3) % 6):.2f}",
                    "LEN": f"{0.10 + 0.12 * ((i * 5) % 8):.2f}",
                    "EXPR": f"{0.20 + 0.10 * ((i * 7) % 8):.2f}",
                    "DIV": f"{0.02 + 0.03 * ((i * 2) % 9):.2f}",
                }
                for i, tip in enumerate(IDS)
            ],
            parameters={"COLOR_MIN": "#f2f2f2", "COLOR_MAX": "#002fa7"},
            source="manual",
        )
    )

    out = save_project(project, SAMPLES_DIR / PROJECT_NAME)
    print(f"wrote {SAMPLES_DIR / TREE_NAME}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
