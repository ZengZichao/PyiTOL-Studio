"""Shared format vocabulary for the adapter layer.

``EXPORT_FORMATS`` used to be duplicated verbatim in :mod:`client_bridge` and
:mod:`config_bridge`; a new engine export format then had to be added in two
places and they drifted silently (code review P2-9).  It lives here so both
modules import one definition.
"""

from __future__ import annotations

# Image / tree formats iTOL's export API accepts (development plan FR-8).
EXPORT_FORMATS: tuple[str, ...] = (
    "svg", "png", "pdf", "tiff", "eps", "newick", "nexus", "phyloxml",
)
