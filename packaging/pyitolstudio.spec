# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PyiTOL Studio (development plan §6.2 / R3).
#
# Build (from the project root):
#   pyinstaller packaging/pyitolstudio.spec
#
# Output: dist/PyiTOL Studio.app  (arm64; ad-hoc signed — see packaging/README.md
# for Developer ID signing and notarization before public distribution).
#
# Notes:
# - The engine stack (scipy / dendropy) needs explicit hidden imports.
# - universal2 requires fat wheels for every dependency; without them the
#   build falls back to the native architecture (omit target_arch).
# - codesign_identity stays None for local builds: a placeholder identity
#   makes pyinstaller fail at the codesign step.

import os
import re

SPEC_DIR = SPECPATH[0] if isinstance(SPECPATH, list) else SPECPATH
PROJECT = os.path.dirname(SPEC_DIR)  # …/PyiTOL-studio-项目代码


def _p(*parts: str) -> str:
    return os.path.join(PROJECT, *parts)


def _project_version() -> str:
    """Single source of truth: read the version from pyproject.toml, so the
    bundle version can never drift from the package version again."""
    text = open(_p("pyproject.toml"), encoding="utf-8").read()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "0.0.0"


_VERSION = _project_version()

# Signing / entitlements are opt-in via the environment so local builds stay
# ad-hoc (a placeholder identity makes PyInstaller fail at codesign), while a
# release build can pass a real Developer ID + the sandbox entitlements:
#   PYITOL_CODESIGN_IDENTITY="Developer ID Application: … (TEAMID)"
#   PYITOL_ENTITLEMENTS=packaging/macos-appstore.entitlements
_CODESIGN_IDENTITY = os.environ.get("PYITOL_CODESIGN_IDENTITY") or None
_ENTITLEMENTS = os.environ.get("PYITOL_ENTITLEMENTS") or None

# Extra Info.plist keys App Store review wants:
#  - ITSAppUsesNonExemptEncryption=false → the app only uses HTTPS (system TLS)
#    to reach iTOL, i.e. exempt encryption (no per-build export paperwork).
#  - a category so the listing is classified.
_PLIST_EXTRAS = {
    "ITSAppUsesNonExemptEncryption": False,
    "LSApplicationCategoryType": "public.app-category.education",
}


a = Analysis(
    [_p("src", "pyitolstudio", "__main__.py")],
    pathex=[_p("src")],
    binaries=[],
    datas=[
        (_p("src", "pyitolstudio", "resources", "*.json"), "pyitolstudio/resources"),
        (_p("src", "pyitolstudio", "resources", "icons", "*.svg"), "pyitolstudio/resources/icons"),
        (_p("design", "PyiTOL-Studio-视觉稿.html"), "design"),
    ],
    hiddenimports=[
        "pyitol",
        "pyitol.api.client",
        "pyitol.templates.generator",
        "pyitol.templates.learner",
        "pyitol.templates.schemas",
        "pyitol.templates.schemas.base",
        "pyitol.templates.schemas.datasets_simple",
        "pyitol.templates.schemas.datasets_advanced",
        "pyitol.templates.schemas.tree_structure",
        "pyitol.templates.schemas.annotations",
        "pyitol.templates.schemas.presets",
        "pyitol.templates.presets",
        "pyitol.templates.presets.cell",
        "pyitol.templates.presets.colorblind",
        "pyitol.templates.presets.nature",
        "pyitol.utils.tree_info",
        "scipy.special.cython_special",
        "dendropy",
        "pandas",
        # QtSvg is needed for SVG icon rendering (QSvgRenderer).
        # PyInstaller does not always detect it as a dependency of PySide6.
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Verified unused by both PyiTOL Studio and the pyitol engine; excluding
    # them keeps the bundle lean when building in a shared dev environment
    # (hooks would otherwise drag in scipy's plotting/Jupyter friends).
    excludes=[
        "tkinter",
        "matplotlib",
        "seaborn",
        "IPython",
        "jupyter",
        "notebook",
        "sphinx",
        "mypy",
        "black",
        "numba",
        "pytest",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PyiTOL Studio",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    codesign_identity=_CODESIGN_IDENTITY,
    entitlements_file=_ENTITLEMENTS,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PyiTOL Studio",
)

app = BUNDLE(
    coll,
    name="PyiTOL Studio.app",
    bundle_identifier="cn.edu.sjtu.pyitolstudio",
    icon=os.path.join(SPEC_DIR, "icons", "pyitolstudio.icns"),
    version=_VERSION,
    info_plist={
        "CFBundleName": "PyiTOL Studio",
        "CFBundleDisplayName": "PyiTOL Studio",
        "CFBundleShortVersionString": _VERSION,
        "CFBundleVersion": _VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "CFBundleDevelopmentRegion": "en",
        "NSHumanReadableCopyright": "© 2026 PyiTOL Studio contributors — MIT License",
        **_PLIST_EXTRAS,
    },
    codesign_identity=_CODESIGN_IDENTITY,
    entitlements_file=_ENTITLEMENTS,
)
