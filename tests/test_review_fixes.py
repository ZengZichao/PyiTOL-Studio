"""Regression guards added while closing the 2026-09-14 code / UI reviews.

Each test maps to a defect that the reviews flagged (identifiers in parentheses
match the reports) so the same class of breakage cannot return silently.  Pure
logic lives here without Qt; anything needing widgets is guarded by
``pytest.importorskip`` and a ``qtbot``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pyitol = pytest.importorskip("pyitol", reason="类型一致性测试需要引擎注册表")

SRC = Path(__file__).resolve().parent.parent / "src" / "pyitolstudio"


# ---------------------------------------------------------------------------
# T1 / P0-1 — the parameter catalog's type names must exist in the engine
# ---------------------------------------------------------------------------
def test_catalog_type_names_are_a_subset_of_the_engine_registry():
    """A single wrong plural ('dataset_connection') silently degraded a whole
    type's form + columns to the fallback — nothing asserted the names lined
    up (code review P0-1 / T1)."""
    from pyitolstudio.adapter.form_idl import load_catalog
    from pyitolstudio.adapter.registry import list_template_types

    catalog_types = set(load_catalog().get("types", {}))
    registry_types = {i.type_name for i in list_template_types()}
    # Every catalog type must be a real engine type.
    unknown = catalog_types - registry_types
    assert not unknown, f"param_ranges.json 有引擎未注册的类型：{unknown}"


def test_non_wizard_types_need_no_catalog_entry():
    """The only registry types allowed to lack a catalog entry are the two
    NON_WIZARD_TYPES (they never render a wizard form)."""
    from pyitolstudio.adapter.form_idl import load_catalog
    from pyitolstudio.adapter.registry import NON_WIZARD_TYPES, list_template_types

    catalog_types = set(load_catalog().get("types", {}))
    registry_types = {i.type_name for i in list_template_types() if i.wizard_supported}
    missing = registry_types - catalog_types
    assert not missing, f"向导支持类型缺少参数目录条目：{missing}"
    assert "dataset_connections" in catalog_types  # the P0-1 regression


# ---------------------------------------------------------------------------
# T2 / P0-2 — the wizard's glyph / name tables must cover every wizard type
# ---------------------------------------------------------------------------
def test_wizard_type_tables_cover_the_registry():
    from pyitolstudio.adapter.registry import list_template_types
    from pyitolstudio.app.unit_list import TYPE_ICONS
    from pyitolstudio.app import wizard

    supported = {i.type_name for i in list_template_types() if i.wizard_supported}
    # Glyph/icon map is single-sourced and must contain the real plural name.
    assert "dataset_arrows" in TYPE_ICONS
    assert "dataset_arrow" not in TYPE_ICONS  # the misspelling that hid the type
    # Every wizard type is buildable into the picker index (none silently
    # dropped by the glyph/subgroup filter — the P0-2 failure mode).
    index = {info.type_name for info in wizard._build_type_index()}
    assert index == supported, f"向导索引与向导支持类型不一致：{index ^ supported}"


def test_arrows_type_is_selectable_in_the_wizard(qtbot):
    """⌘K could list dataset_arrows but the wizard could not select it
    (code review P0-2)."""
    from pyitolstudio.app.wizard import TemplateWizard

    wizard = TemplateWizard()
    qtbot.addWidget(wizard)
    assert wizard.select_type("dataset_arrows") is True
    assert wizard.type_name == "dataset_arrows"


# ---------------------------------------------------------------------------
# T3 / P0-3 — the wizard data step must reject a mis-shaped paste
# ---------------------------------------------------------------------------
def test_wizard_data_page_rejects_wrong_column_count(qtbot):
    from pyitolstudio.app.wizard import DataPage

    page = DataPage()
    qtbot.addWidget(page)
    page.separator_combo.setCurrentText("TAB")
    page.set_sample_columns(["id", "value", "color"], None)
    page._load_rows([["A", "1", "#ff0000", "x", "y"]])  # 5 cols into a 3-col type
    assert page.model.columns != ["id", "value", "color", "col_3", "col_4"]
    assert page.column_info.property("invalid") is True  # error surfaced

    # A correctly-shaped block still loads and clears the error.
    page._load_rows([["A", "1", "#ff0000"]])
    assert page.model.columns == ["id", "value", "color"]
    assert page.column_info.property("invalid") is False


# ---------------------------------------------------------------------------
# T4 / P1-1 — creating a project drops the previous tree's leaf IDs
# ---------------------------------------------------------------------------
def test_new_project_clears_leaf_ids(qtbot):
    from pyitolstudio.app.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win._leaf_ids = {"STALE_FROM_PREVIOUS_TREE"}
    win.new_project()
    assert win._leaf_ids is None


# ---------------------------------------------------------------------------
# T5 / P1-2, P1-4 (UI) — empty rows never count as "missing"
# ---------------------------------------------------------------------------
def test_appended_empty_row_is_not_counted_unmatched(qtbot):
    import pandas as pd
    from pyitolstudio.adapter import build_form_idl
    from pyitolstudio.app.table_editor import DataEditorPage
    from pyitolstudio.app.preview import TemplatePreview

    page = DataEditorPage(TemplatePreview())
    qtbot.addWidget(page)
    frame = pd.DataFrame([{"id": "A", "value": "1", "color": "#ff0000"}])
    page.load_dataframe(frame, {"A", "B"}, build_form_idl("dataset_colorstrip"))
    page.model.append_row()  # a blank row
    _rows, _matched, missing = page.model.match_stats()
    assert len(page.model.unmatched_ids()) == missing  # same verdict, no drift


# ---------------------------------------------------------------------------
# T6 / P1-3 — "reset to defaults" keeps learner extras + unit identity
# ---------------------------------------------------------------------------
def test_reset_to_defaults_preserves_extras_and_identity(qtbot):
    from pyitolstudio.adapter import build_form_idl
    from pyitolstudio.app.inspector import ParameterForm

    idl = build_form_idl("dataset_colorstrip")
    panel = ParameterForm()
    qtbot.addWidget(panel)
    values = {f["key"]: f.get("default", "") for f in idl["fields"]}
    values["DATASET_LABEL"] = "my_strip"
    values["COLOR"] = "#00ff00"
    values["__extra_params__"] = {"CUSTOM_KEY": "keepme"}
    panel.set_idl(idl, values)

    panel.reset_to_defaults()
    out = panel.values()
    assert out.get("__extra_params__") == {"CUSTOM_KEY": "keepme"}  # not dropped
    assert out["DATASET_LABEL"] == "my_strip"  # identity untouched
    assert out["COLOR"] == "#00ff00"


# ---------------------------------------------------------------------------
# T7 / P1-4 (code) + P0-2 (UI) — set_idl validates immediately, no clamp
# ---------------------------------------------------------------------------
def test_set_idl_runs_validation_and_does_not_clamp(qtbot):
    from pyitolstudio.adapter import build_form_idl
    from pyitolstudio.app.inspector import ParameterForm

    idl = build_form_idl("dataset_colorstrip")
    panel = ParameterForm()
    qtbot.addWidget(panel)
    # STRIP_WIDTH catalog max is 100; feed an out-of-range learned value.
    values = {f["key"]: f.get("default", "") for f in idl["fields"]}
    values["STRIP_WIDTH"] = "999"
    panel.set_idl(idl, values)

    assert panel.field_error_count() >= 1            # flagged, not swallowed
    assert panel.values()["STRIP_WIDTH"] == "999"    # held, not clamped to 100


def test_float_default_does_not_show_reset_icon(qtbot):
    """A QDoubleSpinBox (decimals=3) reads back '10.000' vs a default of '10';
    a naive string compare made every float field show its reset icon forever
    (UI P0-2)."""
    from PySide6.QtWidgets import QDoubleSpinBox

    from pyitolstudio.app.inspector import ParameterForm

    field = {"key": "MAX_VALUE", "label": "Max", "widget": "float",
             "default": 10, "group": "appearance", "minimum": 0, "maximum": 100}
    idl = {
        "type_name": "dataset_x", "header": "H", "group_label": "g",
        "fields": [field],
        "groups": [{"key": "appearance", "label_key": "inspector.group.appearance",
                    "expanded": True, "fields": [field]}],
        "data_columns": ["id"], "data_column_labels": ["树 ID"],
    }
    panel = ParameterForm()
    qtbot.addWidget(panel)
    panel.set_idl(idl, {"MAX_VALUE": 10})
    panel.show()
    qtbot.waitExposed(panel)
    reset_btn = panel._reset_buttons["MAX_VALUE"][0]
    assert not reset_btn.isVisibleTo(panel), "默认 float 值不该显示还原图标"

    panel._widgets["MAX_VALUE"].setValue(80)
    assert isinstance(panel._widgets["MAX_VALUE"], QDoubleSpinBox)
    assert reset_btn.isVisibleTo(panel), "偏离默认后应显示还原图标"


# ---------------------------------------------------------------------------
# T8 / P1-4 (code) — a learner round trip through the form preserves params
# ---------------------------------------------------------------------------
def test_learner_form_roundtrip_preserves_parameters(qtbot, fixtures_dir):
    from pyitolstudio.adapter import build_form_idl, generate_template_text, learn_from_file, to_form_values
    from pyitolstudio.adapter.generator_bridge import UnitSpec
    from pyitolstudio.app.inspector import ParameterForm

    learned = learn_from_file(str(fixtures_dir / "tol_color_strip.txt"))[0]
    idl = build_form_idl(learned.type_name)
    field_keys = {f["key"] for f in idl["fields"]}
    panel = ParameterForm()
    qtbot.addWidget(panel)
    panel.set_idl(idl, to_form_values(learned, idl))
    values = panel.values()

    # Learned parameters that ARE catalog fields survive by value (incl. #000).
    for key, val in learned.parameters.items():
        if key in field_keys:
            assert str(values.get(key, "")).strip() == str(val).strip(), key
    # Legal iTOL example data must not be flagged as needing fixes.
    assert panel.field_error_count() == 0, "合法 iTOL 数据被判为参数错误"

    params = {k: v for k, v in values.items()
              if not k.startswith(("__", "LEGEND_")) and k not in ("DATASET_LABEL", "COLOR") and v != ""}
    text = generate_template_text(UnitSpec(
        type_name=learned.type_name, label=learned.label, color=learned.color,
        separator=learned.separator, columns=list(learned.columns),
        data_rows=[dict(r) for r in learned.data_rows], parameters=params,
        legend={k: v for k, v in values.items() if str(k).startswith("LEGEND_") and v != ""},
    ))
    assert "DATASET_COLORSTRIP" in text
    assert "BORDER_COLOR" in text


# ---------------------------------------------------------------------------
# Tree race (P1-5) — a newer load supersedes an older in-flight reply
# ---------------------------------------------------------------------------
def test_tree_generation_guard_field_exists(qtbot):
    from pyitolstudio.app.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    assert hasattr(win, "_tree_generation")
    before = win._tree_generation
    win._set_tree_path("/nonexistent/tree.nwk")
    assert win._tree_generation > before  # bumped on every load request


# ---------------------------------------------------------------------------
# Widget-coverage gate (UI P2-9) — declared controls are all implemented
# ---------------------------------------------------------------------------
def test_declared_widget_kinds_are_rendered(qtbot):
    from pyitolstudio.adapter.form_idl import WIDGET_CHOICES, load_catalog
    from pyitolstudio.app.inspector import ParameterForm

    catalog = load_catalog()
    used = {e.get("widget", "text") for e in catalog["fields"].values()}
    used |= {e.get("widget", "text") for e in catalog.get("legend_fields", {}).values()}
    assert used <= set(WIDGET_CHOICES), f"目录用了未声明的控件类型：{used - set(WIDGET_CHOICES)}"

    # color_list / text_list are dispatched explicitly (not the text fallback).
    form = ParameterForm()
    qtbot.addWidget(form)
    for kind in ("color_list", "text_list"):
        w = form._make_widget({"key": "K", "label": "L", "widget": kind, "default": ""}, "")
        assert type(w).__name__ == "ListEditor", f"{kind} 未走专用编辑器"


def test_param_ranges_every_widget_declared():
    from pyitolstudio.adapter.form_idl import WIDGET_CHOICES, load_catalog
    declared = set()
    for entry in load_catalog()["fields"].values():
        declared.add(entry.get("widget", "text"))
    for entry in load_catalog().get("legend_fields", {}).values():
        declared.add(entry.get("widget", "text"))
    assert declared <= set(WIDGET_CHOICES)


# ---------------------------------------------------------------------------
# i18n gate — every literal tr() key in the source exists in BOTH tables
# ---------------------------------------------------------------------------
def test_every_literal_tr_key_is_translated():
    from pyitolstudio.i18n import _EN, _ZH

    literal_keys: set[str] = set()
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "tr" and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                literal_keys.add(node.args[0].value)

    missing_zh = {k for k in literal_keys if k not in _ZH}
    missing_en = {k for k in literal_keys if k not in _EN}
    assert not missing_zh, f"tr() 字面量缺少中文词条：{missing_zh}"
    assert not missing_en, f"tr() 字面量缺少英文词条：{missing_en}"


def test_translation_tables_stay_in_parity():
    from pyitolstudio.i18n import _EN, _ZH
    assert set(_ZH) == set(_EN), f"中英词条不一致：{set(_ZH) ^ set(_EN)}"


# ---------------------------------------------------------------------------
# Contrast gate (UI P0-3 / P1-8) — small body text meets WCAG AA (>=4.5)
# ---------------------------------------------------------------------------
def _channel(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def _rgba(spec: str) -> tuple[int, int, int, float]:
    """Parse a ``#rgb`` / ``#rrggbb`` / ``rgba(r,g,b,a)`` token into RGBA."""
    text = spec.strip()
    if text.startswith("rgba"):
        nums = re.findall(r"[\d.]+", text)
        r, g, b = int(float(nums[0])), int(float(nums[1])), int(float(nums[2]))
        a = float(nums[3]) if len(nums) > 3 else 1.0
        return (r, g, b, a)
    h = text.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)


def _over(fg: tuple, bg: tuple) -> tuple[float, float, float]:
    """Composite a translucent fg over an opaque bg (source-over)."""
    r, g, b, a = fg
    return (r * a + bg[0] * (1 - a), g * a + bg[1] * (1 - a), b * a + bg[2] * (1 - a))


def _lum(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    return 0.2126 * _channel(int(r)) + 0.7152 * _channel(int(g)) + 0.0722 * _channel(int(b))


def _contrast(fg_spec: str, bg_spec: str) -> float:
    fg = _rgba(fg_spec)
    bg = _rgba(bg_spec)
    # A translucent ground is itself composited over white (the panel).
    if bg[3] < 1.0:
        bg = _over(bg, (255, 255, 255))
    else:
        bg = bg[:3]
    if fg[3] < 1.0:
        fg_rgb = _over(fg, bg)
    else:
        fg_rgb = fg[:3]
    l1, l2 = _lum(fg_rgb), _lum(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def test_accent_link_is_aa_but_plain_accent_is_not():
    """The fix moved small accent text onto accent_link; assert the new token
    passes and the old one really was below AA (guards against re-introducing
    the regression the DESIGN-NOTES claimed was already closed)."""
    from pyitolstudio.theme import palette

    light = palette(False)
    for bg_token in ("panel", "panel_alt", "accent_soft"):
        ratio = _contrast(light["accent_link"], light[bg_token])
        assert ratio >= 4.5, f"accent_link on {bg_token}: {ratio:.2f}:1 < AA"
    # The old choice was the bug — document it stays below AA on the tint.
    assert _contrast(light["accent"], light["accent_soft"]) < 4.5


def test_preview_comment_is_legible():
    """UI P1-8 — comments moved from text_disabled (unreadable) to text_tertiary."""
    from pyitolstudio.theme import palette

    light = palette(False)
    assert _contrast(light["text_tertiary"], light["panel"]) >= 4.5
    assert _contrast(light["text_disabled"], light["panel"]) < 3.0


# ---------------------------------------------------------------------------
# Theme-sync gate (UI P0-1) — the overflow button is re-rasterised on retheme
# ---------------------------------------------------------------------------
def test_retheme_ui_reassigns_overflow_icon(qtbot):
    from PySide6.QtGui import QIcon

    from pyitolstudio.app.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win._overflow_button.setIcon(QIcon())  # sentinel "stale" (empty) icon
    assert win._overflow_button.icon().isNull()
    win.retheme_ui()
    assert not win._overflow_button.icon().isNull(), \
        "retheme_ui 未刷新溢出按钮图标（深→浅切换后会消失）"
