"""Config file generator dialog (FR-7) and upload dialog (FR-8)."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..adapter.client_bridge import EXPORT_FORMATS, upload_and_export
from ..adapter.config_bridge import build_config_yaml, config_idl, validate_config_values
from ..i18n import tr
from ..icons import icon
from ..paths import normalize_input_path as _normalize_dialog_path
from ..paths import writable_target


def _writable_target(raw: str) -> str | None:
    """A canonical path without ``..`` traversal segments.

    Thin alias to :func:`paths.writable_target` — kept as the dialog-local name
    so all four call sites read naturally.
    """
    return writable_target(raw)


class ConfigEditorDialog(QDialog):
    """Visual editor producing a pyitol YAML config file."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("config.title"))
        self.resize(640, 480)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._widgets: dict[str, QWidget] = {}
        for field in config_idl():
            widget = self._make_widget(field)
            self._widgets[field["key"]] = widget
            label = QLabel(field["label"])
            if field.get("help"):
                label.setToolTip(field["help"])
                widget.setToolTip(field["help"])
            form.addRow(label, widget)
        layout.addLayout(form)
        self.error_label = QLabel("")
        self.error_label.setObjectName("inlineError")
        self.error_label.hide()
        layout.addWidget(self.error_label)
        self.notice_label = QLabel("")
        self.notice_label.setObjectName("noticeChip")
        self.notice_label.setProperty("state", "accent")
        self.notice_label.hide()
        layout.addWidget(self.notice_label)
        buttons = QHBoxLayout()
        export_button = QPushButton(icon("file-output", 16), tr("config.export_yaml"))
        export_button.setObjectName("primary")
        close_button = QPushButton(tr("dialog.close"))
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        buttons.addWidget(export_button)
        layout.addLayout(buttons)
        export_button.clicked.connect(self._export)
        close_button.clicked.connect(self.accept)

    def _set_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()
        self.notice_label.hide()

    def _set_notice(self, message: str) -> None:
        self.notice_label.setText(message)
        self.notice_label.show()
        self.error_label.hide()

    def _make_widget(self, field: dict) -> QWidget:
        if field["widget"] == "choice":
            combo = QComboBox()
            combo.addItems(field.get("choices", []))
            if field.get("default"):
                combo.setCurrentText(str(field["default"]))
            return combo
        if field["widget"] in ("path", "dir"):
            want_dir = field["widget"] == "dir"
            host = QWidget()
            inner = QHBoxLayout(host)
            inner.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(str(field.get("default", "")))
            browse = QPushButton("…")
            # The global QPushButton QSS pads 16px each side; inside a 28px
            # button that leaves a negative content rect and the "…" vanishes.
            # #browseButton restates padding 0 so the glyph fits (UI review:
            # button text must never truncate).
            browse.setObjectName("browseButton")
            browse.setFixedWidth(28)
            browse.setAccessibleName(tr("fd.select_file"))

            def browse_path() -> None:
                current = _normalize_dialog_path(self._value(field["key"])) or ""
                start = os.path.dirname(current) or os.path.expanduser("~")
                if want_dir:
                    path = QFileDialog.getExistingDirectory(host, tr("fd.select_dir"), current or start)
                else:
                    path, _ = QFileDialog.getSaveFileName(host, tr("fd.select_file"), start)
                safe = _normalize_dialog_path(path)
                if safe:
                    edit.setText(safe)

            browse.clicked.connect(browse_path)
            inner.addWidget(edit)
            inner.addWidget(browse)
            host._edit = edit  # noqa: B010 - simple attr marker
            return host
        return QLineEdit(str(field.get("default", "")))

    def _value(self, key: str) -> str:
        widget = self._widgets[key]
        edit = getattr(widget, "_edit", widget)
        return edit.text().strip() if hasattr(edit, "text") else ""

    def _export(self) -> None:
        values = {key: self._value(key) for key in self._widgets}
        errors = validate_config_values(values)
        if errors:
            self._set_error("；".join(errors))
            return
        current = _normalize_dialog_path(values.get("api_key_file", "")) or ""
        start = os.path.dirname(current) or os.path.expanduser("~")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("fd.export_config"), os.path.join(start, "pyitol_config.yaml"), tr("fd.filter_yaml")
        )
        if not path:
            return  # user cancelled the save dialog — not an error
        target = _writable_target(path)
        if target is None:
            self._set_error(tr("config.rejected"))
            return
        try:
            Path(target).write_text(build_config_yaml(values), encoding="utf-8")
        except OSError as exc:
            self._set_error(tr("config.write_failed", exc))
            return
        # Success is reported inline too — a modal would interrupt, and the
        # written path is worth keeping on screen.
        self._set_notice(tr("config.done_msg", target))


# Upload tasks that outlived their dialog (closed while running) — keeps a
# Python reference so the running QThread is never garbage-collected.
_DETACHED_TASKS: set = set()


class UploadDialog(QDialog):
    """Batch upload + export with progress; the API key is never entered or
    stored here — only its file path / environment variable is used."""

    def __init__(self, tree_path: str, template_paths: list[str], output_dir: str,
                 parent=None, project_name: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("upload.title"))
        self.resize(560, 420)
        self.tree_path = tree_path
        self.template_paths = list(template_paths)
        self.output_dir = output_dir or str(Path(tree_path).parent or Path.cwd())
        self._project_name = project_name
        self.task: object | None = None
        self._running = False

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.tree_edit = QLineEdit(tree_path)
        browse_tree = QPushButton(icon("folder-open", 14), "")
        browse_tree.setObjectName("browseButton")
        browse_tree.setFixedWidth(28)
        browse_tree.clicked.connect(self._browse_tree)
        tree_host = QWidget()
        tree_inner = QHBoxLayout(tree_host)
        tree_inner.setContentsMargins(0, 0, 0, 0)
        tree_inner.addWidget(self.tree_edit)
        tree_inner.addWidget(browse_tree)
        self._tree_label = QLabel(tr("upload.tree_label"))
        form.addRow(self._tree_label, tree_host)

        self.key_edit = QLineEdit("")
        self.key_edit.setPlaceholderText(tr("upload.key_placeholder"))
        browse_key = QPushButton(icon("key", 14), "")
        browse_key.setFixedWidth(28)
        browse_key.clicked.connect(self._browse_key_file)
        key_host = QWidget()
        key_inner = QHBoxLayout(key_host)
        key_inner.setContentsMargins(0, 0, 0, 0)
        key_inner.addWidget(self.key_edit)
        key_inner.addWidget(browse_key)
        self._key_label = QLabel(tr("upload.key_label"))
        form.addRow(self._key_label, key_host)

        self.format_combo = QComboBox()
        self.format_combo.addItems(EXPORT_FORMATS)
        self._format_label = QLabel(tr("upload.format_label"))
        form.addRow(self._format_label, self.format_combo)

        self.out_edit = QLineEdit(self.output_dir)
        browse_out = QPushButton(icon("folder-open", 14), "")
        browse_out.setObjectName("browseButton")
        browse_out.setFixedWidth(28)
        browse_out.clicked.connect(self._browse_output_dir)
        out_host = QWidget()
        out_inner = QHBoxLayout(out_host)
        out_inner.setContentsMargins(0, 0, 0, 0)
        out_inner.addWidget(self.out_edit)
        out_inner.addWidget(browse_out)
        self._output_label = QLabel(tr("upload.output_label"))
        form.addRow(self._output_label, out_host)

        self.force_check = QCheckBox(tr("upload.force"))
        form.addRow(QLabel(""), self.force_check)
        layout.addLayout(form)

        self._templates_label = QLabel(tr("upload.templates_label"))
        layout.addWidget(self._templates_label)
        self.template_list = QListWidget()
        self.template_list.addItems(self.template_paths)
        self.template_list.setMaximumHeight(110)
        layout.addWidget(self.template_list)
        tpl_buttons = QHBoxLayout()
        add_button = QPushButton(icon("file-plus", 14), tr("upload.add_template"))
        remove_button = QPushButton(icon("trash", 14), tr("upload.remove"))
        tpl_buttons.addWidget(add_button)
        tpl_buttons.addWidget(remove_button)
        tpl_buttons.addStretch(1)
        layout.addLayout(tpl_buttons)
        add_button.clicked.connect(self._add_templates)
        remove_button.clicked.connect(self._remove_selected)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status_label = QLabel(tr("upload.status_pending"))
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        self.error_label = QLabel("")
        self.error_label.setObjectName("inlineError")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.run_button = QPushButton(icon("upload", 14), tr("upload.run"))
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self._run)
        layout.addWidget(self.run_button)
        # Everything that can mutate the run's inputs — the dialog must not
        # let the user edit a form that a running task already snapshotted.
        self._form_widgets = [
            self.tree_edit, self.key_edit, self.format_combo, self.out_edit,
            self.force_check, self.template_list, add_button, remove_button,
            browse_tree, browse_key, browse_out,
        ]

    def _add_templates(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, tr("fd.select_templates"), os.path.expanduser("~"), tr("fd.filter_template"))
        for path in paths:
            safe = _normalize_dialog_path(path)
            if safe and safe not in self.template_paths:
                self.template_paths.append(safe)
                self.template_list.addItem(safe)

    def _remove_selected(self) -> None:
        for item in self.template_list.selectedItems():
            self.template_paths.remove(item.text())
            self.template_list.takeItem(self.template_list.row(item))

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, tr("fd.select_output_dir"), self.out_edit.text().strip() or os.path.expanduser("~"))
        safe = _normalize_dialog_path(path)
        if safe:
            self.out_edit.setText(safe)

    def _browse_tree(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("fd.select_tree"), os.path.expanduser("~"), tr("fd.filter_tree")
        )
        safe = _normalize_dialog_path(path)
        if safe:
            self.tree_edit.setText(safe)

    def _browse_key_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("fd.select_key"), os.path.expanduser("~"))
        safe = _normalize_dialog_path(path)
        if safe:
            self.key_edit.setText(safe)

    def _run(self) -> None:
        from ..adapter.tasks import EngineTask

        tree = _normalize_dialog_path(self.tree_edit.text().strip())
        if not tree or not Path(tree).is_file():
            # Validation is reported inline, never as a modal (design §5.3).
            self.error_label.setText(tr("upload.no_tree_msg"))
            self.error_label.show()
            return
        out_dir = _normalize_dialog_path(self.out_edit.text().strip())
        if not out_dir:
            self.error_label.setText(tr("upload.bad_output_msg"))
            self.error_label.show()
            return
        self.error_label.hide()
        self._running = True
        self.run_button.setEnabled(False)
        for widget in self._form_widgets:
            widget.setEnabled(False)
        self.progress.setRange(0, 0)  # busy indicator
        self.status_label.setText(tr("upload.running"))
        self.task = EngineTask(
            upload_and_export,
            tree,
            list(self.template_paths),
            out_dir,
            fmt=self.format_combo.currentText(),
            api_key_file=_normalize_dialog_path(self.key_edit.text().strip()) or None,
            project_name=self._project_name,
            force=self.force_check.isChecked(),
        )
        self.task.failed.connect(self._failed)
        self.task.finished_with.connect(self._done)
        # Hold a reference past this dialog: if the user closes while running,
        # Python must not GC the QThread mid-run (which aborts the thread).
        _DETACHED_TASKS.add(self.task)
        self.task.finished.connect(lambda t=self.task: _DETACHED_TASKS.discard(t))
        self.task.start()

    def _end_run(self) -> None:
        self._running = False
        self.run_button.setEnabled(True)
        for widget in self._form_widgets:
            widget.setEnabled(True)

    def reject(self) -> None:
        if self._running:
            # The task keeps running detached (its reference lives in
            # _DETACHED_TASKS, so closing this dialog is safe); results are
            # simply dropped when the receivers are destroyed.
            self._running = False
        super().reject()

    def _failed(self, message: str) -> None:
        self._end_run()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status_label.setText(tr("upload.failed", message))

    def _done(self, result: dict) -> None:
        self._end_run()
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        files = "、".join(str(p) for p in result.get("files", {}).values()) or tr("upload.no_files")
        self.status_label.setText(tr("upload.success", result.get("tree_id"), files))
