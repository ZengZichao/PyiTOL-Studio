"""Qt smoke tests (skipped automatically when PySide6 is unavailable)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 未安装，跳过 GUI 冒烟测试")

from pyitolstudio.adapter import build_form_idl  # noqa: E402
from pyitolstudio.app.inspector import InspectorPanel  # noqa: E402


def test_inspector_builds_colorstrip_form(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    idl = build_form_idl("dataset_colorstrip")
    panel.set_idl(idl, {})
    values = panel.values()
    assert "DATASET_LABEL" in values
    assert "STRIP_WIDTH" in values


def test_highlighter_runs(qtbot):
    from pyitolstudio.app.preview import TemplatePreview

    preview = TemplatePreview()
    qtbot.addWidget(preview)
    preview.set_text("DATASET_COLORSTRIP\n\nSEPARATOR TAB\n\nDATASET_LABEL\tdemo\nCOLOR\t#ff0000\n\nDATA\nA\t1")
    assert preview.toPlainText().startswith("DATASET_COLORSTRIP")


def test_inspector_collects_choice_values(qtbot):
    """Regression: QComboBox has no .text(), so choice selections used to be
    collected as empty strings and silently dropped from generated templates."""
    idl = build_form_idl("dataset_colorstrip")
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    values = {f["key"]: f.get("default", "") for f in idl["fields"]}
    panel.set_idl(idl, values)
    combo = panel._widgets["COLOR_BRANCHES"]
    assert combo.currentText() == "0"
    assert panel.values()["COLOR_BRANCHES"] == "0"
    combo.setCurrentText("1")
    assert panel.values()["COLOR_BRANCHES"] == "1"


def test_inspector_rebuild_keeps_form_consistent(qtbot):
    """Selecting unit A then unit B rebuilds the same form without leftovers."""
    idl = build_form_idl("dataset_colorstrip")
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    values = {f["key"]: f.get("default", "") for f in idl["fields"]}
    panel.set_idl(idl, values)
    first = panel.values()
    panel.set_idl(idl, values)
    second = panel.values()
    assert len(panel._widgets) == len(idl["fields"])
    assert first == second
    panel.set_idl(None, None)
    assert panel.values() == {}


def test_wizard_step_rail_rows_do_not_overlap(qtbot):
    """Regression: QPushButton::sizeHint ignores the embedded layout, so the
    two-line step rows collapsed to one bare line and the labels spilled
    onto the neighbouring steps. The rail must reserve a full row per step
    and the rows must not intersect."""
    from PySide6.QtWidgets import QLabel

    from pyitolstudio.app.wizard import WizardSteps

    rail = WizardSteps()
    qtbot.addWidget(rail)
    rail.resize(212, 400)
    rail.show()
    buttons = rail._buttons
    assert len(buttons) == 4

    # The size hint must cover the *content* of a two-line row, not a bare
    # QPushButton line. Comparing against a single-line QLabel's height
    # expresses that directly and stays valid across platforms: Qt's font
    # metrics differ per runner (a 22px badge + two labels measures 48px on
    # a local macOS, but 44px on the GitHub ubuntu runner and 46px on
    # macos-latest), so any hard-coded pixel threshold is flaky.
    first = buttons[0]
    layout = first.layout()
    margins = layout.contentsMargins()
    content = layout.itemAt(0).layout().totalSizeHint().height()
    assert first.sizeHint().height() >= content + margins.top() + margins.bottom(), (
        "step row collapsed to one line: size hint does not cover its content"
    )
    # And it must be materially taller than a single bare text line, which is
    # what a sizeHint-ignores-layout regression looks like.
    single_line = QLabel(first._title).sizeHint().height()
    assert first.sizeHint().height() >= single_line + margins.top() + margins.bottom(), (
        "step row collapsed to one line"
    )

    for prev, nxt in zip(buttons, buttons[1:], strict=False):
        assert nxt.geometry().top() >= prev.geometry().bottom(), (
            f"step rows overlap: {prev._title_label.text()} / {nxt._title_label.text()}"
        )


def test_wizard_data_page_separator_matrix(qtbot):
    from pyitolstudio.app.wizard import DataPage

    page = DataPage()
    qtbot.addWidget(page)
    page.separator_combo.setCurrentText("COMMA")
    page.set_sample_columns(["id", "value", "color"], None)
    page.set_sample_text("A,1,#ff0000\nB,2,#00aa55")
    rows = page.to_rows()
    assert rows == [
        {"id": "A", "value": "1", "color": "#ff0000"},
        {"id": "B", "value": "2", "color": "#00aa55"},
    ]
    # The sample the page generates for the active separator must use it
    # throughout — the grid parses whatever it is handed (0.5.0).
    sample = DataPage.generate_sample_text(["id", "value", "color"], None, page._sep_char)
    assert "," in sample
    assert "\t" not in sample


def test_upload_dialog_template_management(qtbot):
    from PySide6.QtWidgets import QDialog

    from pyitolstudio.app.dialogs import UploadDialog

    dialog = UploadDialog("/tmp/tree.nwk", ["/tmp/a.txt"], "", None)
    qtbot.addWidget(dialog)
    assert dialog.template_paths == ["/tmp/a.txt"]
    # default output dir falls back to the tree's parent, never ""
    assert dialog.output_dir == "/tmp"
    dialog.template_paths.append("/tmp/b.txt")
    dialog.template_list.addItem("/tmp/b.txt")
    dialog.template_list.setCurrentRow(1)
    dialog._remove_selected()
    assert dialog.template_paths == ["/tmp/a.txt"]
    # Closing while the upload thread runs is allowed: the task keeps a
    # detached reference (_DETACHED_TASKS) so the running QThread is never
    # garbage-collected, and the user is no longer trapped in a modal.
    dialog._running = True
    dialog.reject()
    assert dialog.result() == QDialog.DialogCode.Rejected  # closed, not accepted


def test_upload_dialog_reports_validation_inline(qtbot):
    """Errors are presented inline — never a modal that interrupts (§5.3)."""
    from pathlib import Path

    from pyitolstudio.app.dialogs import UploadDialog
    from pyitolstudio.i18n import tr

    dialog = UploadDialog("/tmp/tree.nwk", ["/tmp/a.txt"], "", None)
    qtbot.addWidget(dialog)
    # A non-existent tree is rejected without touching the thread state.
    dialog._run()
    assert dialog.error_label.text() == tr("upload.no_tree_msg")
    assert not dialog._running

    # A valid tree file with an empty output dir is rejected too.
    dialog.tree_edit.setText(str(Path(__file__)))
    dialog.out_edit.setText("")
    dialog._run()
    assert dialog.error_label.text() == tr("upload.bad_output_msg")
    assert not dialog._running


def test_set_idl_does_not_spam_values_changed(qtbot):
    """Regression: building the form emitted change signals once per control,
    so selecting a unit regenerated the preview ~N times."""
    idl = build_form_idl("dataset_colorstrip")
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    fired = []
    panel.values_changed.connect(lambda: fired.append(1))
    panel.set_idl(idl, {})
    assert fired == []
    panel._widgets["COLOR_BRANCHES"].setCurrentText("1")
    assert fired == [1]


def test_data_page_dynamic_column_naming(qtbot):
    from pyitolstudio.app.wizard import DataPage

    page = DataPage()
    qtbot.addWidget(page)
    page.separator_combo.setCurrentText("TAB")
    page.set_sample_columns(["id", "value_1"], "value_N")
    page.set_sample_text("A\t1\t2\t3\nB\t4\t5\t6")
    rows = page.to_rows()
    assert rows[0] == {"id": "A", "value_1": "1", "value_2": "2", "value_3": "3"}
    assert rows[1]["value_3"] == "6"


def test_data_page_sample_matches_type_columns(qtbot):
    """粘贴示例 emits rows shaped like the chosen type, not a fixed demo."""
    from pyitolstudio.app.wizard import DataPage

    page = DataPage()
    qtbot.addWidget(page)
    page.set_sample_columns(["id", "field_1"], "field_N")
    page._paste_sample()
    rows = page.to_rows()
    assert len(rows) == 3
    assert all(set(r) >= {"id", "field_1"} for r in rows)
    assert rows[0]["field_1"] == "1"  # binary/numeric columns get numbers


def test_inspector_preserves_unknown_choice_value(qtbot):
    """Regression: a learned value outside the catalog choices used to leave
    the combo on its first item, so re-selecting the unit silently rewrote
    the parameter (learner data loss)."""
    idl = build_form_idl("dataset_colorstrip")
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.set_idl(idl, {"COLOR_BRANCHES": "9"})
    combo = panel._widgets["COLOR_BRANCHES"]
    assert "9" in [combo.itemText(i) for i in range(combo.count())]
    assert combo.currentText() == "9"
    assert panel.values()["COLOR_BRANCHES"] == "9"


def test_welcome_recent_counts_load_lazily(qtbot, tmp_path):
    """Regression: the recent-projects list must not read/parse each project
    synchronously on refresh (freezes the UI on a slow disk). The path shows
    immediately; the unit count arrives from a worker thread."""
    from PySide6.QtCore import QSettings

    from pyitolstudio.app.welcome import RECENT_PATH_ROLE, WelcomePage
    from pyitolstudio.project import PyitolProject, save_project

    proj = tmp_path / "lazy.pyitolproj"
    save_project(PyitolProject(), proj)
    settings = QSettings()
    settings.setValue("recent_projects", [str(proj)])

    page = WelcomePage()
    qtbot.addWidget(page)
    assert page.recent_list.count() == 1
    item = page.recent_list.item(0)
    immediate = item.data(RECENT_PATH_ROLE)
    assert "·" not in immediate, "unit count leaked into the synchronous pass"

    with qtbot.waitSignal(page._detail_tasks[0].finished, timeout=5000):
        pass
    assert "·" in item.data(RECENT_PATH_ROLE)


def test_main_entry_point_starts_without_crash():
    """Regression: a main.py refactor once dropped the MainWindow import, so
    the app crashed on launch (NameError) while every in-process test still
    passed. Launch the real entry point offscreen and require it to stay up."""
    import os
    import signal
    import subprocess
    import sys
    import time
    from pathlib import Path

    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    child_path = [src_dir] + ([os.environ["PYITOL_ENGINE_SRC"]]
                               if os.environ.get("PYITOL_ENGINE_SRC") else [])
    existing = os.environ.get("PYTHONPATH")
    if existing:
        child_path.append(existing)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=os.pathsep.join(child_path))
    proc = subprocess.Popen(
        [sys.executable, "-m", "pyitolstudio"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(4)
        alive = proc.poll() is None
        _out, err = proc.communicate(timeout=5) if not alive else ("", "")
        assert alive, f"entry point exited early:\n{err}"
        assert "Traceback" not in (err or ""), err
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGKILL)
            proc.wait(timeout=5)


def test_inspector_int_accepts_float_style_values(qtbot):
    """Regression: learned int parameters like "2.0" collapsed to 0 because
    only digit strings were parsed."""
    idl = build_form_idl("dataset_colorstrip")
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.set_idl(idl, {"STRIP_WIDTH": "2.0"})
    assert panel.values()["STRIP_WIDTH"] == "2"


def test_data_page_space_separator_uses_whitespace_runs(qtbot):
    """Regression: split(" ") turned accidental double spaces into phantom
    empty columns and shifted every field; iTOL tokenizes by whitespace."""
    from pyitolstudio.app.wizard import DataPage

    page = DataPage()
    qtbot.addWidget(page)
    page.separator_combo.setCurrentText("SPACE")
    page.set_sample_columns(["id", "value", "color"], None)
    page.set_sample_text("A 1 #ff0000\nB  2 #00aa55")  # double space in row B
    rows = page.to_rows()
    assert rows == [
        {"id": "A", "value": "1", "color": "#ff0000"},
        {"id": "B", "value": "2", "color": "#00aa55"},
    ]


def test_data_page_read_separator_follows_file_type():
    """Regression: importing a .tsv while COMMA was selected read the file
    comma-separated, garbling it into a single column."""
    from pyitolstudio.app.wizard import DataPage

    assert DataPage._read_separator(".csv", "TAB") == ","
    assert DataPage._read_separator(".tsv", "COMMA") == "\t"
    assert DataPage._read_separator(".txt", "COMMA") == ","
    assert DataPage._read_separator(".txt", "TAB") == "\t"
    assert DataPage._read_separator(".txt", "SPACE") == " "


def test_editor_page_valid_ids_flow(qtbot, fixtures_dir, tmp_path):
    """Regression: tree-ID validation coloring existed in the table model but
    no code ever supplied reference leaf IDs; _set_tree_path loads them on a
    worker task and re-applies them to the current table."""
    from pyitolstudio.app.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win._set_tree_path(str(fixtures_dir / "tree_of_life.tree.txt"))
    qtbot.waitUntil(lambda: win._leaf_ids is not None, timeout=30000)
    assert len(win._leaf_ids) > 0

    win._import_template_path(str(fixtures_dir / "tol_color_strip.txt"))
    win.unit_list.setCurrentRow(0)
    assert win.editor.model._valid_ids == win._leaf_ids

    # a first-column value missing from the tree is flagged in unmatched_ids
    model = win.editor.model
    model.setData(model.index(0, model.view_column("id")), "definitely_not_in_tree")
    assert "definitely_not_in_tree" in model.unmatched_ids()


def test_main_window_import_select_preview_roundtrip(qtbot, fixtures_dir, tmp_path):
    """Workbench integration: learner import → unit select → live preview →
    table edits flow back into the unit before generation."""
    from pyitolstudio.adapter import export_template_file
    from pyitolstudio.app.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win._import_template_path(str(fixtures_dir / "tol_color_strip.txt"))
    assert len(win.project.units) == 1

    win.unit_list.setCurrentRow(0)  # the unit row
    assert win.current_unit is not None
    assert "DATASET_COLORSTRIP" in win.preview.toPlainText()
    assert not win.editor.model.frame.empty  # table mirrors the unit data

    # edit a data cell → the live preview loop syncs it into the unit
    # (view column 0 is the row-number ruler, so data columns start at 1)
    model = win.editor.model
    column = model.frame.columns[1]
    model.setData(model.index(0, model.view_column(str(column))), "999")
    assert win.current_unit.data_rows[0][str(column)] == "999"

    out = tmp_path / "current.txt"
    written = export_template_file(win.current_unit.to_spec(), out)
    assert written.exists()
    assert "999" in written.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Inspector v2: grouped / searchable / resettable (design book §5.1)
# ---------------------------------------------------------------------------
def _colorstrip_panel(qtbot):
    from pyitolstudio.adapter import build_form_idl
    from pyitolstudio.app.inspector import InspectorPanel

    panel = InspectorPanel()
    qtbot.addWidget(panel)
    idl = build_form_idl("dataset_colorstrip")
    panel.set_idl(idl, {})
    return panel, idl


def test_inspector_renders_one_section_per_group(qtbot):
    from pyitolstudio.i18n import tr

    panel, idl = _colorstrip_panel(qtbot)
    titles = [section.header.title.text() for section, _e, _r in panel._sections]
    assert titles == [
        tr("inspector.group.basic"),
        tr("inspector.group.mapping"),
        tr("inspector.group.appearance"),
        tr("inspector.group.legend"),
    ]
    counts = [len(rows) for _s, _e, rows in panel._sections]
    assert sum(counts) == len(idl["fields"])
    # First two groups start expanded, the rest folded (design book §5.1).
    assert [section.expanded for section, _e, _r in panel._sections] == [True, True, False, False]
    assert panel._badge.text() == f"{idl['header']} · {tr('inspector.param_count', len(idl['fields']))}"


def test_inspector_search_filters_fields_and_hides_empty_groups(qtbot):
    panel, _idl = _colorstrip_panel(qtbot)
    panel._search.setText("width")
    visible = {
        section.header.title.text(): [not row.isHidden() for _f, row, _h in rows]
        for section, _e, rows in panel._sections
    }
    assert any(any(flags) for flags in visible.values()), "filter matched nothing"
    # A group with no match is hidden entirely.
    for section, _e, rows in panel._sections:
        assert any(not row.isHidden() for _f, row, _h in rows) == (not section.isHidden())

    panel._search.clear()
    for section, _e, rows in panel._sections:
        assert not section.isHidden()
        assert all(not row.isHidden() for _f, row, _h in rows)


def test_inspector_field_default_restores_only_that_field(qtbot):
    panel, idl = _colorstrip_panel(qtbot)
    panel._widgets["STRIP_WIDTH"].setValue(7)
    panel._widgets["MARGIN"].setValue(9)
    assert panel.values()["STRIP_WIDTH"] == "7"

    field = next(f for f in idl["fields"] if f["key"] == "STRIP_WIDTH")
    panel._reset_field(field)
    assert panel.values()["STRIP_WIDTH"] == str(field["default"])
    assert panel.values()["MARGIN"] == "9"  # untouched


def test_inspector_reset_all_and_generate_signal(qtbot):
    panel, idl = _colorstrip_panel(qtbot)
    panel._widgets["STRIP_WIDTH"].setValue(7)
    fired: list[int] = []
    panel.values_changed.connect(lambda: fired.append(1))
    panel.generate_requested.connect(lambda: fired.append(2))

    panel.reset_to_defaults()
    assert fired == [1]
    panel.generate_button.click()
    assert fired == [1, 2]
    assert panel.values()["STRIP_WIDTH"] == str(
        next(f for f in idl["fields"] if f["key"] == "STRIP_WIDTH")["default"]
    )


def test_inspector_validation_banner_states(qtbot):
    from pyitolstudio.i18n import tr

    panel, _idl = _colorstrip_panel(qtbot)
    assert panel.banner.property("state") == "muted"

    panel.set_validation("ok", tr("inspector.banner_ok"))
    assert panel.banner.property("state") == "ok"
    assert panel.banner.label.text() == tr("inspector.banner_ok")

    panel.set_validation("warn", tr("inspector.banner_unmatched", 3))
    assert panel.banner.property("state") == "warn"
    assert "3" in panel.banner.label.text()


def test_inspector_notes_show_unit_and_range(qtbot):
    """The note line carries the design's "像素 · 1–100" style hint."""
    from pyitolstudio.i18n import tr

    panel, idl = _colorstrip_panel(qtbot)
    field = next(f for f in idl["fields"] if f["key"] == "STRIP_WIDTH")
    assert panel._note_for(field) == f"{tr('inspector.unit.px')} · {field['range']}"
    bordered = next(f for f in idl["fields"] if f["key"] == "BORDER_WIDTH")
    assert panel._note_for(bordered) == bordered["hint"]


def test_main_window_pushes_unit_context_and_validation(qtbot, fixtures_dir):
    """The inspector owns no tree knowledge — the main window feeds it both
    the unit header and the ID-match verdict."""
    from pyitolstudio.app.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win._set_tree_path(str(fixtures_dir / "tree_of_life.tree.txt"))
    qtbot.waitUntil(lambda: win._leaf_ids is not None, timeout=30000)

    win._import_template_path(str(fixtures_dir / "tol_color_strip.txt"))
    win.unit_list.setCurrentRow(0)
    assert win.inspector._name_label.text() == "color_strip1"
    assert win.inspector.banner.property("state") == "ok"

    win.editor.model.setData(
        win.editor.model.index(0, win.editor.model.view_column("id")), "definitely_not_in_tree"
    )
    assert win.inspector.banner.property("state") == "warn"
    assert "1" in win.inspector.banner.label.text()


# ---------------------------------------------------------------------------
# Center pane data grid (design book §9.2)
# ---------------------------------------------------------------------------
_UNSET = object()


def _grid_page(qtbot, type_name: str = "dataset_colorstrip", valid_ids=_UNSET):
    import pandas as pd
    from PySide6.QtCore import Qt  # noqa: F401  (documented in the module)

    from pyitolstudio.adapter import build_form_idl
    from pyitolstudio.app.preview import TemplatePreview
    from pyitolstudio.app.table_editor import DataEditorPage

    if valid_ids is _UNSET:
        valid_ids = {"A"}

    page = DataEditorPage(TemplatePreview())
    qtbot.addWidget(page)
    idl = build_form_idl(type_name)
    frame = pd.DataFrame(
        [
            {"id": "A", "value": "1", "color": "#ff0000"},
            {"id": "B", "value": "2", "color": "#00aa55"},
        ],
        columns=["id", "value", "color"],
    )
    page.load_dataframe(frame, valid_ids, idl)
    return page, idl


def test_grid_has_row_number_and_status_columns(qtbot):
    from PySide6.QtCore import Qt

    from pyitolstudio.i18n import tr

    page, idl = _grid_page(qtbot)
    model = page.model
    assert model.columnCount() == len(idl["data_columns"]) + 2
    assert model.status_column == model.columnCount() - 1
    assert model.headerData(0, Qt.Orientation.Horizontal) == ""
    assert model.headerData(model.status_column, Qt.Orientation.Horizontal) == tr("table.col_status")

    # the row number is a read-only ruler, not a data cell
    ruler = model.index(0, 0)
    assert model.data(ruler, Qt.ItemDataRole.DisplayRole) == "1"
    assert not (model.flags(ruler) & Qt.ItemFlag.ItemIsEditable)
    assert not model.setData(ruler, "9", Qt.ItemDataRole.EditRole)


def test_grid_status_column_encodes_with_icon_and_text(qtbot):
    from PySide6.QtCore import Qt

    from pyitolstudio.app.table_editor import (
        STATUS_MATCHED,
        STATUS_MISSING,
        STATUS_ROLE,
    )
    from pyitolstudio.i18n import tr

    page, _idl = _grid_page(qtbot)
    model = page.model
    assert model.status_of_row(0) == STATUS_MATCHED
    assert model.status_of_row(1) == STATUS_MISSING
    assert model.match_stats() == (2, 1, 1)

    cell = model.index(1, model.status_column)
    assert model.data(cell, STATUS_ROLE) == STATUS_MISSING
    assert model.data(cell, Qt.ItemDataRole.DisplayRole) == tr("table.status_missing")
    # the second channel: colour is never the only carrier of the verdict
    assert model.data(cell, Qt.ItemDataRole.DecorationRole) is not None


def test_grid_reports_unchecked_without_a_reference_tree(qtbot):
    from pyitolstudio.app.table_editor import STATUS_UNCHECKED

    page, _idl = _grid_page(qtbot, valid_ids=None)
    assert page.model.status_of_row(0) == STATUS_UNCHECKED
    assert page.model.match_stats() == (2, 0, 0)


def test_grid_flags_unmatched_rows_with_danger_soft(qtbot):
    from PySide6.QtCore import Qt

    from pyitolstudio.theme_mode import theme_qcolor

    page, _idl = _grid_page(qtbot)
    model = page.model
    bad = model.data(model.index(1, model.view_column("id")), Qt.ItemDataRole.BackgroundRole)
    assert bad == theme_qcolor("danger_soft")
    assert model.data(model.index(0, model.view_column("id")), Qt.ItemDataRole.BackgroundRole) is None
    # the cell text colour is deliberately left alone
    assert model.data(model.index(1, model.view_column("id")), Qt.ItemDataRole.ForegroundRole) is None


def test_grid_uses_mono_for_ids_and_numeric_columns(qtbot):
    from PySide6.QtCore import Qt

    page, _idl = _grid_page(qtbot)
    model = page.model
    assert model.data(model.index(0, model.view_column("id")), Qt.ItemDataRole.FontRole) is not None
    assert model.data(model.index(0, model.view_column("value")), Qt.ItemDataRole.FontRole) is not None
    # a hex-colour column is text, so it keeps the UI face
    assert model.data(model.index(0, model.view_column("color")), Qt.ItemDataRole.FontRole) is None


def test_grid_add_row_updates_footer(qtbot):
    from pyitolstudio.i18n import tr

    page, _idl = _grid_page(qtbot)
    assert page.count_label.text() == tr("table.footer_count", 2, 1, 1)
    page.add_row()
    assert page.model.rowCount() == 3
    assert page.count_label.text() == tr("table.footer_count", 3, 1, 1)


def test_grid_paste_replaces_the_table_in_one_reset(qtbot):
    from PySide6.QtWidgets import QApplication

    page, _idl = _grid_page(qtbot)
    resets: list[int] = []
    page.model.modelReset.connect(lambda: resets.append(1))
    QApplication.clipboard().setText("X\t9\t#123456\nY\t8\t#654321")
    page.paste_from_clipboard()
    assert len(resets) == 1  # batched, not one refresh per row
    assert page.model.rowCount() == 2
    assert page.model.frame.iloc[0, 0] == "X"
    assert page.notice_label.isHidden()


def test_grid_paste_column_mismatch_is_reported_inline(qtbot):
    from PySide6.QtWidgets import QApplication

    from pyitolstudio.i18n import tr

    page, _idl = _grid_page(qtbot)
    before = page.model.to_rows()
    QApplication.clipboard().setText("A\t1\t2\t3\t4")
    page.paste_from_clipboard()
    assert page.model.to_rows() == before  # nothing written
    assert not page.notice_label.isHidden()  # inline, never a modal
    assert page.notice_label.text() == tr("table.paste_col_mismatch", 3, 5)


def test_grid_paste_names_dynamic_columns_like_the_wizard(qtbot):
    import pandas as pd
    from PySide6.QtWidgets import QApplication

    from pyitolstudio.adapter import build_form_idl

    page, _idl = _grid_page(qtbot)
    page.load_dataframe(pd.DataFrame(), None, build_form_idl("dataset_multibar"))
    QApplication.clipboard().setText("A\t1\t2\t3")
    page.paste_from_clipboard()
    assert page.model.columns == ["id", "value_1", "value_2", "value_3"]


def test_grid_goes_read_only_beyond_the_edit_envelope(qtbot):
    import pandas as pd
    from PySide6.QtCore import Qt

    page, _idl = _grid_page(qtbot)
    wide = pd.DataFrame(
        [[str(i) for i in range(25)]], columns=[f"value_{i}" for i in range(25)]
    )
    page.load_dataframe(wide, None, None)
    assert not page.model.editable
    assert not page.paste_button.isEnabled()
    assert not page.notice_label.isHidden()
    assert not page.model.setData(page.model.index(0, 1), "9", Qt.ItemDataRole.EditRole)


def test_grid_edit_flows_back_into_the_unit(qtbot, fixtures_dir):
    """The whole point of the grid: 改完就知道对不对."""
    from pyitolstudio.app.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win._import_template_path(str(fixtures_dir / "tol_color_strip.txt"))
    win.unit_list.setCurrentRow(0)

    model = win.editor.model
    assert model.columnCount() == len(win._current_idl["data_columns"]) + 2
    target = model.view_column("value")
    model.setData(model.index(0, target), "4242")
    assert win.current_unit.data_rows[0]["value"] == "4242"
    assert "4242" in win.preview.toPlainText()


# ---------------------------------------------------------------------------
# Left rail: tree card + unit list (design book §5.1)
# ---------------------------------------------------------------------------
def _rail_window(qtbot, fixtures_dir):
    from pyitolstudio.app.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win._import_template_path(str(fixtures_dir / "tol_color_strip.txt"))
    return win


def test_rail_row_carries_type_colour_and_visibility(qtbot, fixtures_dir):
    from pyitolstudio.app.unit_list import UNIT_COLOR_ROLE, UNIT_HIDDEN_ROLE, UNIT_TYPE_ROLE

    win = _rail_window(qtbot, fixtures_dir)
    assert win.unit_list.count() == len(win.project.units) == 1
    item = win.unit_list.item(0)
    assert item.data(UNIT_TYPE_ROLE) == "dataset_colorstrip"
    assert str(item.data(UNIT_COLOR_ROLE)).startswith("#")
    assert item.data(UNIT_HIDDEN_ROLE) is False
    assert win.rail.count_label.text() == "1"


def test_rail_eye_hides_a_unit(qtbot, fixtures_dir):
    from pyitolstudio.app.unit_list import UNIT_HIDDEN_ROLE

    win = _rail_window(qtbot, fixtures_dir)
    unit_id = win.project.units[0].unit_id
    win._toggle_unit_hidden(unit_id)
    assert unit_id in win._hidden_units
    assert win.unit_list.item(0).data(UNIT_HIDDEN_ROLE) is True
    # hiding is UI state only: the project document is untouched
    assert win.project.units[0].unit_id == unit_id
    win._toggle_unit_hidden(unit_id)
    assert unit_id not in win._hidden_units


def test_rail_eye_is_hit_testable(qtbot, fixtures_dir):
    """The eye and the overflow glyph are painted, so they need hit-testing."""
    from PySide6.QtCore import QEvent, QPointF, QRect, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QStyleOptionViewItem

    from pyitolstudio.app.unit_list import ROW_HEIGHT

    win = _rail_window(qtbot, fixtures_dir)
    listing = win.unit_list
    delegate = listing.itemDelegate()
    index = listing.indexFromItem(listing.item(0))
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 250, ROW_HEIGHT)
    parts = delegate._layout(option.rect)

    fired: list[str] = []
    listing.toggle_hidden.connect(fired.append)
    centre = QPointF(parts["eye"].center())
    release = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        centre,
        centre,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    assert delegate.editorEvent(release, listing.model(), option, index) is True
    assert fired == [win.project.units[0].unit_id]


def test_rail_reorder_rewrites_the_dataset_order(qtbot, fixtures_dir):
    """Drag order is the order iTOL stacks the datasets in."""
    from PySide6.QtCore import QModelIndex

    from pyitolstudio.project import Unit

    win = _rail_window(qtbot, fixtures_dir)
    first_id = win.project.units[0].unit_id
    second = win.project.add_unit(Unit(type_name="dataset_heatmap", label="heatmap60"))
    win._refresh_nav()
    assert win.unit_list.count() == 2
    assert [u.unit_id for u in win.project.units] == [first_id, second.unit_id]

    # Drag the second row above the first: the view emits rowsMoved, which the
    # rail forwards to the project document.
    win.unit_list.model().moveRow(QModelIndex(), 1, QModelIndex(), 0)
    assert win.unit_list.ordered_ids() == [second.unit_id, first_id]
    assert [u.unit_id for u in win.project.units] == [second.unit_id, first_id]


def test_tree_card_reports_leaf_count_and_match_rate(qtbot, fixtures_dir):
    win = _rail_window(qtbot, fixtures_dir)
    win._set_tree_path(str(fixtures_dir / "tree_of_life.tree.txt"))
    qtbot.waitUntil(lambda: win._leaf_ids is not None, timeout=30000)
    win.unit_list.setCurrentRow(0)

    card = win.rail.tree_card
    assert card.name_label.text() == "tree_of_life.tree.txt"
    assert f"{len(win._leaf_ids):,}" in card.meta_label.text()
    assert "/" in card.match_label.text()
    assert card.progress.maximum() == win.editor.model.rowCount()


def test_rail_shows_a_placeholder_before_a_tree_is_chosen(qtbot, fixtures_dir):
    from pyitolstudio.i18n import tr

    win = _rail_window(qtbot, fixtures_dir)
    assert win.rail.tree_card.name_label.text() == tr("nav.tree_none")
    assert win.rail.tree_card.match_label.text() == ""


# ---------------------------------------------------------------------------
# Command palette (⌘K) — design book §5.1/§6
# ---------------------------------------------------------------------------
def test_palette_indexes_units_types_and_commands(qtbot, fixtures_dir):
    from pyitolstudio.app.command_palette import KIND_COMMAND, KIND_TYPE, KIND_UNIT

    win = _rail_window(qtbot, fixtures_dir)
    entries = win._palette_entries()
    assert {KIND_UNIT, KIND_TYPE, KIND_COMMAND} <= {e.kind for e in entries}
    assert any(e.kind == KIND_UNIT and e.title == "color_strip1" for e in entries)
    # 31 types make a browsable grid a slow way to reach one type
    assert sum(1 for e in entries if e.kind == KIND_TYPE) >= 25


def test_palette_filters_by_query(qtbot):
    from pyitolstudio.app.command_palette import CommandPalette, PaletteEntry

    entries = [
        PaletteEntry("unit", "color_strip1", "dataset_colorstrip", "rectangle-horizontal", lambda: None),
        PaletteEntry("type", "DATASET_HEATMAP", "矩阵与热图", "grid-3x3", lambda: None),
    ]
    palette = CommandPalette(entries)
    qtbot.addWidget(palette)
    assert palette.list.count() == 2
    palette.search.setText("heat")
    assert palette.list.count() == 1
    assert palette.list.item(0).text() == "DATASET_HEATMAP"
    palette.search.clear()
    assert palette.list.count() == 2


def test_palette_unit_entry_selects_the_unit(qtbot, fixtures_dir):
    from pyitolstudio.app.command_palette import KIND_UNIT
    from pyitolstudio.project import Unit

    win = _rail_window(qtbot, fixtures_dir)
    second = win.project.add_unit(Unit(type_name="dataset_heatmap", label="heatmap60"))
    win._refresh_nav()
    target = next(
        e for e in win._palette_entries() if e.kind == KIND_UNIT and e.title == "heatmap60"
    )
    target.run()
    assert win.unit_list.current_unit_id() == second.unit_id


def test_appearance_menu_overrides_the_platform_mode(qtbot, fixtures_dir):
    """Both modes must be verifiable without changing the OS setting."""
    from pyitolstudio import theme_mode

    win = _rail_window(qtbot, fixtures_dir)
    emitted: list[int] = []
    win.theme_mode_changed.connect(lambda: emitted.append(1))
    try:
        assert theme_mode.follows_system()

        win._switch_theme("dark")
        assert theme_mode.override() is True
        assert theme_mode.current_dark() is True
        assert emitted

        win._switch_theme("light")
        assert theme_mode.override() is False
        assert theme_mode.current_dark() is False

        # Re-translating keeps the menu check state in step with the override.
        win.retranslate_ui()
        checked = [a.isChecked() for a in win._theme_menu.actions()]
        assert checked == [False, False, True]

        win._switch_theme("system")
        assert theme_mode.follows_system()
    finally:
        theme_mode.set_override(None)


def test_palette_shortcut_is_registered(qtbot, fixtures_dir):
    from PySide6.QtGui import QKeySequence

    win = _rail_window(qtbot, fixtures_dir)
    assert win._actions["palette"].shortcut() == QKeySequence("Ctrl+K")
    assert win._actions["export"].shortcut() == QKeySequence("Ctrl+Shift+E")


# ---------------------------------------------------------------------------
# Template wizard (design book §5.3)
# ---------------------------------------------------------------------------
def test_wizard_lists_only_wizard_supported_types(qtbot):
    from pyitolstudio.app.wizard import TypeGridPage

    page = TypeGridPage()
    qtbot.addWidget(page)
    # 31 registered types in the engine; 2 are NOT wizard-supported (dataset_manual,
    # dataset_treestyle). Our grid only renders the others.
    assert 25 <= page._cards.__len__() <= 30
    # The three design groups all appear.
    subgroups = {info.subgroup for info in page._all}
    assert {"basic", "matrix", "structure"} <= subgroups


def test_wizard_selects_and_advances_when_a_type_is_picked(qtbot, fixtures_dir):
    from PySide6.QtWidgets import QLabel

    from pyitolstudio.app.wizard import (
        PAGE_DATA,
        PAGE_TYPE,
        TemplateWizard,
    )

    win = _rail_window(qtbot, fixtures_dir)
    win.show()
    wizard = TemplateWizard(win)
    qtbot.addWidget(wizard)
    assert wizard.pages.currentIndex() == PAGE_TYPE

    # Preselect a type, then jump to step 2.  The wizard commits the type and
    # the data page picks up its colpill strip from the IDL.
    assert wizard.select_type("dataset_colorstrip")
    wizard._goto(PAGE_DATA)
    assert wizard.type_name == "dataset_colorstrip"
    assert wizard.idl is not None
    assert any(p.text() == "id" for p in wizard.data_page.findChildren(QLabel))


def test_wizard_steps_rail_only_enables_visited_pages(qtbot):
    from pyitolstudio.app.wizard import TemplateWizard

    wizard = TemplateWizard()
    qtbot.addWidget(wizard)
    # The rail starts at step 1; later steps are disabled.
    enabled = [b.isEnabled() for b in wizard.steps._buttons]
    assert enabled == [True, False, False, False]
    # After visiting step 2 the rail opens up to it.
    wizard.steps._buttons[1].setEnabled(True)
    wizard._reached = 1
    wizard.steps.sync(wizard.pages.currentIndex(), 1)
    enabled = [b.isEnabled() for b in wizard.steps._buttons]
    assert enabled == [True, True, False, False]


def test_wizard_step_button_paints_done_with_a_checkmark(qtbot):
    from pyitolstudio.app.wizard import StepButton

    btn = StepButton("Configure", "appearance", 0)
    btn.set_state("done")
    pix = btn._badge.pixmap()
    assert not pix.isNull()  # a checkmark is rasterised, not text


def test_wizard_search_filters_type_cards(qtbot):
    from pyitolstudio.app.wizard import TypeGridPage

    page = TypeGridPage()
    qtbot.addWidget(page)
    total = len(page._cards)
    page.search.setText("heatmap")
    visible_names = sorted(c.property("type_name") for c in page._cards if c.isVisibleTo(page))
    expected = sorted(
        info.type_name
        for info in page._all
        if "heatmap" in f"{info.header} {info.description}".lower()
    )
    assert visible_names == expected
    assert 0 < len(visible_names) < total
    page.search.clear()
    assert all(c.isVisibleTo(page) for c in page._cards)


def test_wizard_paste_sample_shapes_its_block_like_the_type(qtbot):
    from pyitolstudio.app.wizard import DataPage

    page = DataPage()
    qtbot.addWidget(page)
    page.set_sample_columns(["id", "field_1"], "field_N")
    page._paste_sample()
    rows = page.to_rows()
    assert len(rows) == 3
    # The dynamic column gets the absolute index, matching the wizard's rule.
    assert all(set(r) == {"id", "field_1", "field_2", "field_3"} for r in rows)
