#!/usr/bin/env python3
"""Generate macOS app icon (.icns / iconset) from the SVG source.

Uses ``rsvg-convert`` (or ``sips`` as fallback) to rasterise the SVG at each
required resolution, then ``iconutil`` to build the ``.icns`` bundle.

Prerequisites on macOS::

    brew install librsvg   # for rsvg-convert

Usage::

    python scripts/generate_app_icon.py
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ICONS_DIR = PROJECT / "packaging" / "icons"
SVG_SOURCE = ICONS_DIR / "pyitolstudio.svg"
ICONSET_DIR = ICONS_DIR / "pyitolstudio.iconset"
ICNS_OUTPUT = ICONS_DIR / "pyitolstudio.icns"
PNG_OUTPUT = ICONS_DIR / "pyitolstudio_1024.png"

# (filename, pixel-size) for each iconset entry.
ICONSET_SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_64x64.png", 64),
    ("icon_64x64@2x.png", 128),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def find_converter() -> str:
    """Return the first available SVG → PNG rasteriser (PySide6 QSvgRenderer
    covers machines without librsvg)."""
    try:
        import PySide6  # noqa: F401

        return "pyside6"
    except ImportError:
        pass
    for tool in ("rsvg-convert",):
        if shutil.which(tool):
            return tool
    return ""


def rasterise_with_pyside(svg: Path, size: int, output: Path) -> bool:
    """QSvgRenderer fallback: render the 1024-grid SVG at *size* px square."""
    try:
        raw = svg.read_bytes()
        if len(raw) > 262_144:
            raise ValueError("SVG source larger than 256 KiB — refusing to parse")
        # The SVG is a repo-controlled asset, but refuse DTDs anyway: the
        # stdlib XML parser accepts internal entities (billion-laughs).
        if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
            raise ValueError("SVG contains a DOCTYPE/ENTITY — refusing to parse")
        from PySide6.QtCore import QByteArray, QRectF
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtSvg import QSvgRenderer

        renderer = QSvgRenderer(QByteArray(raw))
        if not renderer.isValid():
            raise ValueError("QSvgRenderer reported an invalid document")
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(0)  # transparent ground — the tile paints itself
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        return image.save(str(output), "PNG")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR rasterising {output.name} at {size}px (PySide6): {exc}")
        return False


def rasterise_svg(svg: Path, size: int, output: Path, tool: str) -> bool:
    """Rasterise *svg* to *output* at *size*×*size* pixels."""
    if tool == "pyside6":
        return rasterise_with_pyside(svg, size, output)
    try:
        if tool == "rsvg-convert":
            subprocess.run(
                ["rsvg-convert", "-w", str(size), "-h", str(size),
                 "-f", "png", "-o", str(output), str(svg)],
                check=True, capture_output=True, shell=False,
            )
        else:
            # Fallback: use sips (macOS built-in) — it handles SVG on macOS 14+.
            subprocess.run(
                ["sips", "-s", "format", "png", "-z", str(size), str(size),
                 str(svg), "--out", str(output)],
                check=True, capture_output=True, shell=False,
            )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"ERROR rasterising {output.name} at {size}px: {exc}")
        return False


def main() -> int:
    if not SVG_SOURCE.is_file():
        print(f"ERROR: SVG source not found: {SVG_SOURCE}")
        return 1

    tool = find_converter()
    if not tool:
        print("ERROR: No SVG rasteriser found. Install librsvg: brew install librsvg")
        return 1

    print(f"Using rasteriser: {tool}")

    # Fresh iconset directory.
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True)

    # Render each size.
    for filename, size in ICONSET_SIZES:
        output = ICONSET_DIR / filename
        if not rasterise_svg(SVG_SOURCE, size, output, tool):
            return 1
        print(f"  {filename} ({size}×{size})")

    # Also write the 1024px master PNG.
    shutil.copy2(ICONSET_DIR / "icon_512x512@2x.png", PNG_OUTPUT)

    # Build .icns from the iconset.
    if ICNS_OUTPUT.exists():
        ICNS_OUTPUT.unlink()
    try:
        subprocess.run(
            ["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_OUTPUT)],
            check=True,
            capture_output=True,
            shell=False,
        )
    except subprocess.CalledProcessError as exc:
        print(f"ERROR building .icns: {exc.stderr.decode()}")
        return 1

    print(f"\nGenerated {ICNS_OUTPUT}")
    print(f"Generated {PNG_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
