"""Path safety helpers (plan R6)."""

from __future__ import annotations

import os

from pyitolstudio.paths import normalize_input_path


def test_empty_path_returns_none():
    assert normalize_input_path("") is None
    assert normalize_input_path(None) is None  # type: ignore[arg-type]


def test_traversal_segments_are_rejected():
    """Regression: normpath used to collapse ".." before the check, silently
    rewriting a traversal ("/tmp/a/../../etc" → "/etc") instead of rejecting
    it."""
    assert normalize_input_path("~/../etc/passwd") is None
    assert normalize_input_path("/tmp/a/../..//b.yaml") is None
    assert normalize_input_path("/tmp/a/../../etc/passwd") is None


def test_regular_paths_are_normalized():
    raw = os.path.expanduser("~") + "/docs/config.yaml"
    assert normalize_input_path(raw) == os.path.normpath(raw)


def test_external_volume_paths_are_allowed():
    """User-confirmed dialog targets outside home/cwd (USB sticks, mounted
    drives) must not be rejected — regression: an allowlist of write roots
    made config export fail on /Volumes with a spurious security error."""
    assert normalize_input_path("/Volumes/USB/pyitol_config.yaml") == "/Volumes/USB/pyitol_config.yaml"
