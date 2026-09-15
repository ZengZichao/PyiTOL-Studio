"""Bundled read-only resources (JSON catalogs)."""

from __future__ import annotations

import sys
from importlib.resources import files


def resource_path(name: str):
    """Return a traversable path for a bundled resource file.

    Under PyInstaller the package lives inside the PYZ archive, where
    ``importlib.resources`` cannot see data files; resolve them from the
    extraction directory (``sys._MEIPASS``) instead.
    """
    if getattr(sys, "frozen", False):  # PyInstaller onefile/onedir
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            from pathlib import Path  # noqa: PLC0415

            frozen = Path(meipass) / "pyitolstudio" / "resources" / name
            if frozen.exists():
                return frozen
    return files("pyitolstudio.resources").joinpath(name)
