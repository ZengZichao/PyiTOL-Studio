"""PyiTOL Studio — desktop companion for iTOL annotation.

A macOS GUI workbench built on top of the pyitol engine. This package
follows the layering discipline from the development plan:

- ``pyitolstudio.adapter``  : registry introspection, form IDL, engine bridges
- ``pyitolstudio.app``      : PySide6 widgets (imported lazily, requires Qt)
- ``pyitolstudio.i18n``     : bilingual Chinese / English translation (``tr()``)
- ``pyitolstudio.icons``    : Lucide SVG icon integration (``icon()``)
- ``pyitolstudio.theme``    : visual tokens converted from the HTML mockup
- ``pyitolstudio.project``  : ``.pyitolproj`` project model and store
- ``pyitolstudio.resources``: bundled JSON resources (param ranges, groups)

The GUI layer never imports ``pyitol`` directly; everything goes through
the adapter layer.
"""

__app_name__ = "PyiTOL Studio"
__subtitle__ = "Desktop companion for iTOL annotation"

# Version single-sourced from the installed distribution's metadata
# (pyproject.toml is the authority).  When running straight from the source
# tree without an install, ``version()`` raises PackageNotFoundError; fall back
# to this literal, which is kept in step with pyproject for that case only.
_FALLBACK_VERSION = "0.1.0"

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version

    try:
        __version__ = _pkg_version("pyitol-studio")
    except PackageNotFoundError:
        __version__ = _FALLBACK_VERSION
except Exception:  # noqa: BLE001 - metadata machinery absent → literal
    __version__ = _FALLBACK_VERSION
