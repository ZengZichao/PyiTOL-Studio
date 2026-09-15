"""Learner round-trip regression over official fixtures (plan §10.1)."""

from __future__ import annotations

import pytest

pyitol = pytest.importorskip("pyitol")

from pyitolstudio.adapter import learn_from_file  # noqa: E402
from pyitolstudio.adapter.generator_bridge import generate_template_text  # noqa: E402

# (fixture, expected header, expected type)
CASES = [
    ("tol_color_strip.txt", "DATASET_COLORSTRIP", "dataset_colorstrip"),
    ("tol_simple_bar.txt", "DATASET_SIMPLEBAR", "dataset_simple_bar"),
    ("tol_heatmap1.txt", "DATASET_HEATMAP", "dataset_heatmap"),
    ("tol_binary.txt", "DATASET_BINARY", "dataset_binary"),
    ("labels.txt", "LABELS", "dataset_labels"),
    ("colors_tol.txt", "TREE_COLORS", "dataset_tree_colors"),
    ("tol_spacing.txt", "SPACING", "dataset_spacing"),
    ("popup_info_template.txt", "POPUP_INFO", "dataset_popup_info"),
    ("tol_ranges_dataset.txt", "DATASET_RANGE", "dataset_range"),
]


@pytest.mark.parametrize("fixture_name,header,type_name", CASES)
def test_learn_generate_learn_roundtrip(fixtures_dir, fixture_name, header, type_name):
    first = learn_from_file(fixtures_dir / fixture_name)[0]
    assert first.header == header
    assert first.type_name == type_name

    text = generate_template_text(first.to_spec())
    body = "\n".join(ln for ln in text.splitlines() if ln.strip() and not ln.startswith("TEMPLATE_NAME"))
    assert body.startswith(header)

    second = learn_from_path_safe(text, fixture_name)
    assert second[0].type_name == type_name
    # Semantic equivalence: same separator, same parameter set, same data.
    assert second[0].separator == first.separator
    assert _norm_params(second[0].parameters) == _norm_params(first.parameters)
    assert len(second[0].data_rows) == len(first.data_rows)


def learn_from_path_safe(text: str, name: str):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text(text, encoding="utf-8")
        return learn_from_file(path)


def _norm_params(params: dict) -> dict:
    return {k: str(v) for k, v in params.items() if k not in ("TEMPLATE_NAME",)}
