"""Application entry point (``pyitol-studio`` / ``python -m pyitolstudio``)."""

from __future__ import annotations

import os


def main() -> int:
    if os.environ.get("PYITOLSTUDIO_SMOKE") == "1":
        return _smoke()

    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:  # friendly message instead of a stack trace
        raise SystemExit(
            "PySide6 未安装。请先执行：pip install 'PySide6>=6.5'\n"
            f"（原始错误：{exc}）"
        ) from exc

    QGuiApplication.setApplicationName("PyiTOL Studio")
    QGuiApplication.setOrganizationName("pyitol-studio")
    app = QApplication(sys_argv())

    # Load saved locale before any widget is constructed.
    from ..i18n import translator  # noqa: PLC0415
    translator().load_saved()

    # Follow the system appearance (Qt 6.5+); restyle live on change.  An
    # explicit override (PYITOLSTUDIO_THEME or the 外观 menu) wins.
    from ..theme import build_stylesheet  # noqa: PLC0415
    from ..theme_mode import (  # noqa: PLC0415
        build_palette,
        current_dark,
        follows_system,
        set_override,
    )

    env_mode = os.environ.get("PYITOLSTUDIO_THEME", "").strip().lower()
    if env_mode in ("dark", "light"):
        set_override(env_mode == "dark")

    from .main_window import MainWindow  # noqa: PLC0415

    window = MainWindow()

    def apply_theme() -> None:
        dark = current_dark()
        app.setStyleSheet(build_stylesheet(dark))
        # The stylesheet alone leaves every surface it does not paint on the
        # system palette — a dark window with light holes in it.  The palette
        # is the other half of "apply the theme"; both have to move together.
        app.setPalette(build_palette(dark))
        # Icons, pixmaps and the preview's highlight formats resolved concrete
        # colours at build time — re-rasterise them for the new mode.
        window.retheme_ui()

    apply_theme()

    def on_scheme_changed(_scheme) -> None:
        # Only react when actually following the OS; an explicit override
        # makes the flip a no-op repaint of the whole app.
        if follows_system():
            apply_theme()

    app.styleHints().colorSchemeChanged.connect(on_scheme_changed)
    window.theme_mode_changed.connect(apply_theme)
    window.show()
    return app.exec()


def _smoke() -> int:
    """Headless self-test for packaged builds (``PYITOLSTUDIO_SMOKE=1``).

    Exercises every frozen layer without opening a window: engine registry
    introspection → form IDL (bundled catalog via ``resource_path``) →
    template generation → learner round-trip.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication([sys_argv()[0], "-platform", "offscreen"])

    from ..adapter import (
        build_form_idl,
        generate_template_text,
        learn_from_file,
        list_template_types,
    )
    from ..adapter.generator_bridge import UnitSpec
    from .inspector import InspectorPanel

    types = list_template_types()
    assert len(types) >= 29, f"engine registry returned {len(types)} types"

    idl = build_form_idl("dataset_colorstrip")
    assert idl["fields"], "form IDL is empty — bundled catalog unreadable?"
    panel = InspectorPanel()
    panel.set_idl(idl, {})
    assert panel.values().get("DATASET_LABEL") is not None

    spec = UnitSpec(
        type_name="dataset_colorstrip",
        label="smoke",
        separator="TAB",
        columns=["id", "value", "color"],
        data_rows=[{"id": "A", "value": "1", "color": "#ff0000"}],
    )
    text = generate_template_text(spec)

    import tempfile  # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="pyitolstudio_smoke_") as tmp:
        from pathlib import Path  # noqa: PLC0415

        out = Path(tmp) / "roundtrip.txt"
        from ..adapter import export_template_file  # noqa: PLC0415

        export_template_file(spec, out)
        units = learn_from_file(out)
        assert units and units[0].type_name == "dataset_colorstrip"

    assert "DATASET_COLORSTRIP" in text
    app.quit()
    print(f"PyiTOL Studio smoke OK — {len(types)} template types, "
          "IDL + catalog + generator + learner round-trip verified")
    return 0


def sys_argv() -> list[str]:
    import sys  # noqa: PLC0415

    return [sys.argv[0]] + list(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
