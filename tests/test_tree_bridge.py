"""Tree bridge: leaf labels for workbench ID validation (FR-3)."""

from __future__ import annotations

import pytest

pyitol = pytest.importorskip("pyitol")

from pyitolstudio.adapter.tree_bridge import tree_leaf_ids  # noqa: E402


def test_leaf_ids_extracted(fixtures_dir):
    ids = tree_leaf_ids(fixtures_dir / "tree_of_life.tree.txt")
    assert ids is not None
    assert len(ids) > 0
    # labels are unique non-empty strings
    assert all(isinstance(i, str) and i for i in ids)


def test_missing_tree_returns_none(tmp_path):
    assert tree_leaf_ids(tmp_path / "nope.nwk") is None


def test_non_tree_file_returns_none(tmp_path):
    bad = tmp_path / "bad.nwk"
    bad.write_text("this is not a newick tree", encoding="utf-8")
    assert tree_leaf_ids(bad) is None
