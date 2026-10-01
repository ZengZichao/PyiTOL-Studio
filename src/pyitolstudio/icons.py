"""Lucide SVG icon integration for PySide6.

Loads bundled ``.svg`` files and renders them as crisp ``QIcon`` instances at
any pixel size — no TTF font or PNG files needed.  SVG vector rendering keeps
icons sharp on high-DPI (Retina) displays where the previous font-glyph
rasterisation produced blurry results.

Usage::

    from ..icons import icon
    action = toolbar.addAction(icon("folder-open"), "Open")

The SVG source files live at ``pyitolstudio/resources/icons/<name>.svg``.
Run ``python scripts/collect_svg_icons.py`` to refresh them from the Lucide
icon pack.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import (
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

from .theme_mode import theme_color

# Cache loaded SVG bytes keyed by icon name.
_SVG_CACHE: dict[str, bytes] | None = None

# Fallback SVG (a simple square) used when a name is not found — avoids a
# blank icon that looks like a rendering bug.
_FALLBACK_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
    b'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    b'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    b'<rect x="3" y="3" width="18" height="18" rx="2"/>'
    b'</svg>'
)


def _resource_path(*parts: str) -> str:
    """Resolve a bundled resource, honouring PyInstaller's ``_MEIPASS``.

    Both branches must resolve to the *same* file: the package data lives at
    ``pyitolstudio/resources/icons`` under the project (``__file__``) and under
    the bundle (``_MEIPASS``).  The ``_MEIPASS`` branch needs the explicit
    ``pyitolstudio/resources/icons`` prefix — without it the path points at
    ``_MEIPASS/<name>.svg``, which does not exist, so the icon never loads.
    """
    if getattr(sys, "_MEIPASS", None):
        return os.path.join(sys._MEIPASS, "pyitolstudio", "resources", "icons", *parts)
    # src/pyitolstudio/resources/icons/…
    here = os.path.dirname(__file__)
    return os.path.join(here, "resources", "icons", *parts)


def _load_svgs() -> dict[str, bytes]:
    """Lazily load every bundled ``.svg`` file into a name → bytes cache.

    Loading all files at once (rather than one-by-one on demand) is simpler
    and fast enough for ~70 small icons.  The cache survives for the process
    lifetime; the ``lru_cache`` on :func:`_icon_cached` handles the more
    granular per-(name, size, colour) caching.
    """
    global _SVG_CACHE
    if _SVG_CACHE is not None:
        return _SVG_CACHE
    cache: dict[str, bytes] = {}
    icons_dir = _resource_path()
    if os.path.isdir(icons_dir):
        for filename in os.listdir(icons_dir):
            if not filename.endswith(".svg"):
                continue
            name = filename[:-4]  # strip ".svg"
            try:
                with open(os.path.join(icons_dir, filename), "rb") as f:
                    cache[name] = f.read()
            except OSError:
                pass
    _SVG_CACHE = cache
    return cache


def _recolor_svg(svg_bytes: bytes, color: str) -> bytes:
    """Replace ``stroke="currentColor"`` (and any explicit stroke) with *color*.

    Lucide SVGs use ``stroke="currentColor"`` so the consuming app controls the
    colour.  Qt's ``QSvgRenderer`` does **not** inherit the QPainter pen colour
    into the SVG's ``currentColor`` — it resolves to black by default.  We
    therefore rewrite the XML to substitute the concrete hex before rendering.

    The rewrite is a targeted string replacement rather than a full XML
    round-trip: Lucide SVGs are machine-generated and consistently formatted,
    so ``stroke="currentColor"`` always appears verbatim.
    """
    text = svg_bytes.decode("utf-8")
    # Replace currentColor with the target colour — this is the Lucide
    # convention for theming.
    text = text.replace('stroke="currentColor"', f'stroke="{color}"')
    return text.encode("utf-8")


def _default_color() -> str:
    """Icon stroke for the active mode.

    Icons are chrome, not data: the default must follow the theme tokens, or
    a dark UI would draw near-black glyphs on a near-black toolbar.  Matches
    the prototype's ``.btn svg { stroke: currentColor }`` on ``--t1``.
    """
    return theme_color("text")


def icon(name: str, size: int = 18, color: str | None = None) -> QIcon:
    """Create a ``QIcon`` from a Lucide SVG icon name.

    Parameters
    ----------
    name : str
        Lucide icon name without the ``lucide-`` prefix
        (e.g. ``"folder-open"``, ``"upload"``, ``"settings"``).
    size : int
        Pixel size of the rendered pixmap (square).
    color : str, optional
        Hex color string (``"#9aa5b4"``).  Defaults to the active mode's
        ``text`` token; pass an explicit token value when a glyph needs
        to differ (e.g. ``accent`` on a selected row).
    """
    # Resolve the theme default *before* the cache lookup, so the cache key
    # carries the concrete color and a theme switch cannot serve stale icons.
    return _icon_cached(name, size, color or _default_color())


def icon_pixmap(name: str, size: int, color: str | None = None) -> QPixmap:
    """A DPR-preserving pixmap for ``QLabel.setPixmap`` / ``drawPixmap``.

    ``QIcon.pixmap(size, size)`` (the single-size overload) asks for a dpr=1
    image and downsamples the 2× master, so a pixmap painted directly loses
    Retina sharpness (UI review P2-1).  Request the 2.0 variant explicitly;
    ``QLabel``/``QPainter`` honour ``devicePixelRatio`` and lay it out at the
    logical *size* without any further division.
    """
    return _icon_cached(name, size, color or _default_color()).pixmap(
        QSize(size, size), 2.0
    )


@lru_cache(maxsize=256)
def _icon_cached(name: str, size: int, color: str) -> QIcon:
    svgs = _load_svgs()
    raw = svgs.get(name)
    if raw is None:
        raw = _FALLBACK_SVG

    # Recolour the SVG for this icon's theme colour.
    svg_bytes = _recolor_svg(raw, color)

    # Render at 2× the requested size for crisp Retina output, then let the
    # QIcon's device-pixel-ratio handle the downscale.  This is the standard
    # Qt high-DPI pattern: draw into a 2× pixmap, set devicePixelRatio=2, and
    # the windowing system composites it at the correct physical resolution.
    scale = 2
    phys_size = size * scale
    pixmap = QPixmap(phys_size, phys_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(QByteArray(svg_bytes))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    # Render the SVG into the full pixmap rect.  QSvgRenderer's default
    # viewBox (0 0 24 24) maps to the target rect automatically.
    renderer.render(painter, QRectF(0, 0, phys_size, phys_size))
    painter.end()

    # Mark the pixmap as high-DPI so Qt knows the logical size is `size`.
    pixmap.setDevicePixelRatio(scale)

    # Create the icon from the high-DPI pixmap.  QIcon will use the
    # devicePixelRatio to serve the right physical resolution per screen.
    result = QIcon(pixmap)
    # Also add a 1× version for non-Retina screens / offscreen rendering.
    result.addPixmap(pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation),
                     mode=QIcon.Mode.Normal)
    return result
