"""Three-pane main workbench + welcome page (FR-10/FR-11)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QSizePolicy,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QFileDialog,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..adapter import (
    build_form_idl,
    generate_template_text,
    learn_from_file,
    list_template_types,
    to_form_values,
)
from ..adapter.tasks import EngineTask
from ..i18n import tr, translator
from ..icons import icon
from ..project import PyitolProject, Unit, load_project, save_project
from ..paths import writable_target
from ..theme import TOOLBAR_ICON
from .. import theme_mode
from .command_palette import (
    KIND_COMMAND,
    KIND_TYPE,
    KIND_UNIT,
    CommandPalette,
    PaletteEntry,
)
from .dialogs import ConfigEditorDialog, UploadDialog
from .inspector import InspectorPanel
from .preview import TemplatePreview
from .table_editor import DataEditorPage
from .toast import show_toast
from .unit_list import UNIT_ID_ROLE, RailWidget, type_icon_name
from .welcome import WelcomePage
from .wizard import TemplateWizard

RECENT_KEY = "recent_projects"
SPLITTER_KEY = "ui/splitter_sizes"
_DEFAULT_SPLITTER = [280, 700, 302]


def _mode_matches(mode: str) -> bool:
    """Whether the active override equals *mode* (``dark`` / ``light``)."""
    return theme_mode.override() == (mode == "dark")


class MainWindow(QMainWindow):
    """Left: project navigation · Center: table + preview · Right: inspector."""

    theme_mode_changed = Signal()
    """Emitted after the 外观 menu changes the mode; the app re-applies QSS."""

    def __init__(self) -> None:
        super().__init__()
        translator().load_saved()
        self._actions: dict[str, QAction] = {}
        self._action_icons: dict[str, str] = {}
        self._toolbar: QToolBar | None = None
        self._lang_menu: QMenu | None = None
        self.project = PyitolProject()
        self.current_unit: Unit | None = None
        self._current_idl: dict | None = None
        self._leaf_ids: set[str] | None = None
        # UI-only: the .pyitolproj schema is frozen for this iteration, so the
        # eye's state is not persisted with the project.
        self._hidden_units: set[str] = set()
        self._tasks: list[EngineTask] = []  # keep worker refs alive while running
        # Last non-zero width per outer pane, so a restore after collapse does
        # not come back at zero.
        self._pane_widths: dict[str, int] = {}
        self._tree_loading = False
        # Unsaved-changes guard (code review P1-6): the tree/parameter edits all
        # funnel through here so the title can carry a "*" and a project switch
        # can ask before discarding work.
        self._dirty = False
        # Set while a unit is being loaded so the resulting preview refresh is
        # not mistaken for a user edit (which would flip the dirty flag).
        self._loading_unit = False
        # Generation counter for reference-tree loads (code review P1-5): a fast
        # A→B tree switch must not let A's late reply clobber B's leaf IDs.
        self._tree_generation = 0
        # Upload temp dirs, cleaned once the dialog closes (code review P2-6).
        self._temp_dirs: list[Path] = []
        # Where the current project lives on disk, if it has been saved
        # (drives the default save name / project rename, code review P2-5).
        self._project_path: str | None = None

        self.preview = TemplatePreview()
        self.editor = DataEditorPage(self.preview)
        self.inspector = InspectorPanel()

        self.rail = RailWidget()
        self.unit_list = self.rail.unit_list
        self.unit_list.unit_activated.connect(self._on_unit_activated)
        self.unit_list.toggle_hidden.connect(self._toggle_unit_hidden)
        self.unit_list.overflow_requested.connect(self._show_nav_menu)
        self.unit_list.reordered.connect(self._reorder_units)
        self.unit_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.unit_list.customContextMenuRequested.connect(self._show_nav_menu_at)
        self.rail.tree_card.change_requested.connect(self.choose_tree_file)
        # Panel chevrons drive the same hide/show as the toolbar toggles.
        self.rail.collapse_requested.connect(
            lambda: self._toggle_pane("rail", visible=False)
        )
        self.inspector.collapse_requested.connect(
            lambda: self._toggle_pane("inspector", visible=False)
        )

        from PySide6.QtWidgets import QSplitter

        center_stack = QStackedWidget()
        self.welcome = WelcomePage()
        center_stack.addWidget(self.welcome)
        center_stack.addWidget(self.editor)
        self.center_stack = center_stack

        self.welcome.new_project.connect(self.new_project)
        self.welcome.open_project.connect(self.open_project)
        self.welcome.browse_examples.connect(self.open_wizard)
        self.welcome.open_path.connect(self._open_project_path)
        self.editor.wizard_requested.connect(self.open_wizard)
        self.inspector.wizard_requested.connect(self.open_wizard)

        splitter = QSplitter()
        splitter.addWidget(self.rail)
        splitter.addWidget(center_stack)
        splitter.addWidget(self.inspector)
        # A pane the user cannot shrink to zero (and the centre column cannot
        # be starved by the outer ones) — the split stays usable on windows
        # narrower than the default 1280px layout.
        self.rail.setMinimumWidth(220)
        center_stack.setMinimumWidth(420)
        self.inspector.setMinimumWidth(260)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        saved = QSettings().value(SPLITTER_KEY, _DEFAULT_SPLITTER)
        try:
            sizes = [int(v) for v in saved]
        except (TypeError, ValueError):
            sizes = list(_DEFAULT_SPLITTER)
        if len(sizes) != 3:
            sizes = list(_DEFAULT_SPLITTER)
        splitter.setSizes(sizes)
        splitter.splitterMoved.connect(
            lambda _pos, _idx, s=splitter: QSettings().setValue(SPLITTER_KEY, s.sizes())
        )
        self.splitter = splitter
        self.setCentralWidget(splitter)

        self._build_toolbar()
        # _build_toolbar() already constructed the language and theme menus.

        self.setAcceptDrops(True)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("app.status_ready"))
        # Live preview: wired once here; re-selecting units must not stack
        # duplicate connections (each would regenerate the preview N times).
        self.inspector.values_changed.connect(self.refresh_preview)
        # ``生成模板`` (⌘↩) regenerates the preview, same loop as a field edit.
        self.inspector.generate_requested.connect(self._on_generate_requested)
        # Table edits participate in the same live-preview loop (FR-2/FR-3).
        self.editor.model.invalidity_changed.connect(self.refresh_preview)
        self._refresh_nav()
        self.retranslate_ui()

        # Re-translate on locale change.
        translator().add_listener(self.retranslate_ui)
        # Icon/pixmap re-rasterisation on theme change is driven by
        # main.apply_theme() (also covers OS-driven switches).

    # ------------------------------------------------------------------
    def _build_toolbar(self) -> None:
        """One bar, three groups by intent, and an overflow for everything else.

        The bar used to carry fourteen equal-weight icons in a row behind two
        1px separators: no hierarchy at all, and no way to tell which
        operations actually matter without hovering each one in turn.  Only the
        high-frequency actions keep a permanent slot now; the occasional ones
        (preview refresh, upload, config) and the set-once ones (pane toggles,
        language, theme) move into the overflow menu at the right edge
        (UI review §04 ②).
        """
        toolbar = QToolBar("main")
        self.addToolBar(toolbar)
        self._toolbar = toolbar
        self._overflow_menu = QMenu(self)

        # (action_key, icon_name, text_key, handler, shortcut)
        entries = [
            ("palette", "search", "cmd.open", self.open_command_palette, "Ctrl+K"),
            ("new", "file-plus", "tb.new", self.new_project, "Ctrl+N"),
            ("open", "folder-open", "tb.open", self.open_project, "Ctrl+O"),
            ("save", "save", "tb.save", self.save_project, "Ctrl+S"),
            ("wizard", "wand", "tb.wizard", self.open_wizard, ""),
            ("import", "import", "tb.import", self.import_template, ""),
            ("export", "file-output", "tb.export", self.export_current_template, "Ctrl+Shift+E"),
            ("preview", "eye", "tb.preview", self.refresh_preview, ""),
            ("upload", "upload", "tb.upload", self.open_upload, ""),
            ("config", "settings", "tb.config", self.open_config_editor, ""),
        ]
        for key, icon_name, text_key, handler, shortcut in entries:
            act = QAction(icon(icon_name, TOOLBAR_ICON), tr(text_key), self)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
                native = QKeySequence(shortcut).toString(QKeySequence.SequenceFormat.NativeText)
                act.setToolTip(f"{tr(text_key)}   {native}")
            else:
                act.setToolTip(tr(text_key))
            act.triggered.connect(handler)
            self._actions[key] = act
            self._action_icons[key] = icon_name

        # 文件 · 数据 — the two groups that earn a permanent slot.  Accent fills
        # only the primary action, so `accent` stays unmistakable for "the main
        # thing"; every other button stays neutral until hover.
        for index, group in enumerate(
            (["palette"], ["new", "open", "save"], ["wizard", "import", "export"])
        ):
            if index:
                toolbar.addSeparator()
            for key in group:
                act = self._actions[key]
                toolbar.addAction(act)
                if key == "new":
                    toolbar.widgetForAction(act).setObjectName("primaryTool")

        # Pane toggles: set once per session, so they belong in the overflow.
        self._pane_actions: dict[str, QAction] = {}
        for pane, icon_name, text_key in (
            ("rail", "panel-left", "tb.toggle_rail"),
            ("inspector", "panel-right", "tb.toggle_inspector"),
        ):
            act = QAction(icon(icon_name, TOOLBAR_ICON), tr(text_key), self)
            act.setCheckable(True)
            act.setChecked(True)
            # QAction.triggered carries no payload in PySide6 — read the
            # (already toggled) check state instead of a lambda default,
            # which is always False and can only ever hide the pane.
            act.triggered.connect(
                lambda _=False, p=pane: self._toggle_pane(p, self._pane_actions[p].isChecked())
            )
            self._pane_actions[pane] = act
            self._action_icons[pane] = icon_name

        for key in ("preview", "upload", "config"):
            self._overflow_menu.addAction(self._actions[key])
        self._overflow_menu.addSeparator()
        for pane in ("rail", "inspector"):
            self._overflow_menu.addAction(self._pane_actions[pane])
        self._overflow_menu.addSeparator()

        # Language switcher (globe icon + menu).
        lang_action = QAction(icon("languages", TOOLBAR_ICON), tr("tb.language"), self)
        lang_action.setToolTip(tr("tb.language"))
        self._lang_action = lang_action
        self._action_icons["language"] = "languages"
        # Appearance switcher (sun/moon icon + menu) — lets both modes be
        # verified without changing the OS setting.
        theme_action = QAction(icon("sun-moon", TOOLBAR_ICON), tr("tb.theme"), self)
        theme_action.setToolTip(tr("tb.theme"))
        self._theme_action = theme_action
        self._action_icons["theme"] = "sun-moon"
        self._overflow_menu.addAction(lang_action)
        self._overflow_menu.addAction(theme_action)

        # Overflow button, pinned against the right edge.
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        overflow = QToolButton()
        overflow.setObjectName("iconButton")
        overflow.setToolTip(tr("tb.more"))
        overflow.setIcon(icon("ellipsis-vertical", TOOLBAR_ICON))
        overflow.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        overflow.setMenu(self._overflow_menu)
        toolbar.addWidget(overflow)
        self._overflow_button = overflow

        self._build_language_menu()
        self._build_theme_menu()

    def _build_language_menu(self) -> None:
        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for locale, label_key in (("zh", "lang.zh"), ("en", "lang.en")):
            act = QAction(tr(label_key), menu)
            act.setCheckable(True)
            act.setChecked(translator().locale == locale)
            act.triggered.connect(lambda checked=False, loc=locale: self._switch_language(loc))
            group.addAction(act)
            menu.addAction(act)
        self._lang_menu = menu
        self._lang_action.setMenu(menu)
        # Make the arrow visible next to the globe icon — when it has one.
        self._bind_popup(self._lang_action)

    def _build_theme_menu(self) -> None:
        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for mode, label_key in (
            ("system", "theme.system"),
            ("dark", "theme.dark"),
            ("light", "theme.light"),
        ):
            act = QAction(tr(label_key), menu)
            act.setCheckable(True)
            act.setChecked(theme_mode.follows_system() if mode == "system" else _mode_matches(mode))
            act.triggered.connect(lambda checked=False, m=mode: self._switch_theme(m))
            group.addAction(act)
            menu.addAction(act)
        self._theme_menu = menu
        self._theme_action.setMenu(menu)
        self._bind_popup(self._theme_action)

    def _bind_popup(self, action: QAction) -> None:
        """Give an action's button the instant-popup arrow, when it has one.

        Actions now live either on the bar or in the overflow menu; only the
        former have a toolbar button to configure, and menu items get their
        submenu arrow from the menu itself.
        """
        button = self._toolbar.widgetForAction(action)
        if button is not None:
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def _switch_theme(self, mode: str) -> None:
        """Force a mode, or follow the platform again (``system``)."""
        theme_mode.set_override(None if mode == "system" else (mode == "dark"))
        self.theme_mode_changed.emit()

    # ------------------------------------------------------------------
    def _toggle_pane(self, pane: str, visible: bool) -> None:
        """Hide/show one outer pane (rail / inspector) in the central splitter.

        Marked visible while the pane is on screen. Collapsing one pane lets
        the middle column take all the width; the chevron on each panel stays
        in sync so either entry point reflects the same state.
        """
        widget = self.rail if pane == "rail" else self.inspector
        if widget.isVisible() == visible:
            self._sync_pane_action(pane, visible)
            return
        splitter = self.splitter
        idx = splitter.indexOf(widget)
        if visible:
            widget.show()
            sizes = splitter.sizes()
            sizes[idx] = self._pane_widths.get(pane, _DEFAULT_SPLITTER[idx])
            splitter.setSizes(sizes)
        else:
            # Capture the width while the pane is still laid out; reading it
            # after hide() would return 0 and the restore would collapse.
            self._pane_widths[pane] = max(splitter.sizes()[idx], 1)
            widget.hide()
        # The centre column is the only pane that may stretch; the outer panes
        # keep the width the user gave them.
        splitter.setStretchFactor(idx, 0)
        QSettings().setValue(SPLITTER_KEY, splitter.sizes())
        if pane == "rail":
            self.rail.set_collapsed(not visible)
        else:
            self.inspector.set_collapsed(not visible)
        self._sync_pane_action(pane, visible)

    def _sync_pane_action(self, pane: str, visible: bool) -> None:
        """Mirror the pane state into the toolbar toggle without re-triggering it."""
        act = self._pane_actions.get(pane)
        if act is not None and act.isChecked() != visible:
            act.blockSignals(True)
            act.setChecked(visible)
            act.blockSignals(False)

    # ------------------------------------------------------------------
    def _switch_language(self, locale: str) -> None:
        translator().set_locale(locale)

    # ------------------------------------------------------------------
    def retranslate_ui(self) -> None:
        """Re-apply all translatable text after a locale switch."""
        self._update_title()
        # Toolbar actions
        text_map = {
            "palette": "cmd.open",
            "new": "tb.new", "open": "tb.open", "save": "tb.save",
            "wizard": "tb.wizard", "import": "tb.import", "preview": "tb.preview",
            "export": "tb.export", "upload": "tb.upload", "config": "tb.config",
        }
        for key, tk in text_map.items():
            if key in self._actions:
                self._actions[key].setText(tr(tk))
        for pane, tk in (("rail", "tb.toggle_rail"), ("inspector", "tb.toggle_inspector")):
            if pane in self._pane_actions:
                self._pane_actions[pane].setText(tr(tk))
        if hasattr(self, "_lang_action"):
            self._lang_action.setText(tr("tb.language"))
            self._lang_action.setToolTip(tr("tb.language"))
        # Rebuild language menu labels
        if self._lang_menu is not None:
            actions = self._lang_menu.actions()
            if len(actions) >= 2:
                actions[0].setText(tr("lang.zh"))
                actions[1].setText(tr("lang.en"))
                actions[0].setChecked(translator().locale == "zh")
                actions[1].setChecked(translator().locale == "en")
        if hasattr(self, "_theme_action"):
            self._theme_action.setText(tr("tb.theme"))
            self._theme_action.setToolTip(tr("tb.theme"))
        if getattr(self, "_theme_menu", None) is not None:
            for (mode, label_key), act in zip(
                (("system", "theme.system"), ("dark", "theme.dark"), ("light", "theme.light")),
                self._theme_menu.actions(),
            ):
                act.setText(tr(label_key))
                act.setChecked(
                    theme_mode.follows_system() if mode == "system" else _mode_matches(mode)
                )
        # Welcome page
        self.welcome.retranslate_ui()
        # Inspector header
        self.inspector.retranslate_ui()
        self._update_validation()
        # Left rail (tree card + unit list)
        self.rail.retranslate_ui()
        self._refresh_nav()
        # Status bar
        self.status_bar.showMessage(tr("app.status_ready"))
        # Editor
        self.editor.retranslate_ui()
        # Overflow button: not in _actions, so translate/label it explicitly.
        self._overflow_button.setToolTip(tr("tb.more"))
        self._overflow_button.setAccessibleName(tr("tb.more"))

    # ------------------------------------------------------------------
    def retheme_ui(self) -> None:
        """Re-render everything that rasterised a theme colour to a pixmap.

        The stylesheet handles plain QSS colours on theme switch, but icons
        and the preview's syntax-highlight formats were resolved to concrete
        colours at build time — without this they keep the previous mode's
        glyphs (e.g. dark-on-dark after dark→light).
        """
        for key, act in self._actions.items():
            name = self._action_icons.get(key)
            if name:
                act.setIcon(icon(name))
        for pane, act in self._pane_actions.items():
            act.setIcon(icon(self._action_icons[pane]))
        for key in ("language", "theme"):
            act = getattr(self, "_lang_action" if key == "language" else "_theme_action", None)
            if act is not None:
                act.setIcon(icon(self._action_icons[key], 18))
        self.preview.set_dark(theme_mode.current_dark())
        self.inspector.retheme_ui()
        self.rail.retheme_ui()
        self.welcome.retheme_ui()
        self.editor.retheme_ui()
        # The overflow button is not in _actions / _pane_actions, so it must be
        # re-rasterised explicitly — otherwise its near-white glyph survives a
        # dark→light switch and vanishes on the light toolbar (UI P0-1).
        self._overflow_button.setIcon(icon("ellipsis-vertical", TOOLBAR_ICON))

    # ------------------------------------------------------------------
    def _status_path(self, key: str, path, *extra) -> None:
        """Show *path* by its file name, keeping the full path in the tooltip.

        The status bar used to print an absolute path verbatim: it filled the
        whole strip, told the user nothing they could act on, and left the one
        place a full path is actually useful — a hover — empty
        (UI review §04 ⑤).
        """
        self.status_bar.showMessage(tr(key, Path(path).name, *extra))
        self.status_bar.setToolTip(str(path))

    def _update_title(self) -> None:
        name = self.project.name or tr("app.title")
        marker = "• " if self._dirty else ""
        self.setWindowTitle(f"{marker}{name}")

    def _set_dirty(self, dirty: bool) -> None:
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self._update_title()

    def _reset_project_context(self) -> None:
        """Drop all tree-derived state when a project is created / opened.

        ``_leaf_ids`` lived on across a project switch, so a freshly created
        project validated new units against the previous tree's leaves
        (code review P1-1).
        """
        self._tree_generation += 1  # invalidate any in-flight tree load
        self._leaf_ids = None
        self._tree_loading = False

    def _maybe_confirm_discard(self) -> bool:
        """Ask before discarding unsaved edits.  ``True`` → safe to proceed."""
        if not self._dirty:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("app.unsaved_title"))
        box.setText(tr("app.unsaved_msg"))
        save = box.addButton(tr("app.unsaved_save"), QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton(tr("app.unsaved_discard"), QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton(tr("app.unsaved_cancel"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        chosen = box.clickedButton()
        if chosen is cancel:
            return False
        if chosen is save:
            self.save_project()
            # A cancelled/failed save must not discard the edits either.
            return not self._dirty
        return True  # discard

    def new_project(self) -> None:
        if not self._maybe_confirm_discard():
            return
        self.project = PyitolProject()
        self._project_path = None
        self._hidden_units.clear()
        self._reset_project_context()
        self._reset_unit_selection()
        self._refresh_nav()
        self.center_stack.setCurrentWidget(self.editor)
        self._set_dirty(False)
        self.status_bar.showMessage(tr("app.status_new_project"))

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("fd.open_project"), "", tr("fd.filter_project"))
        if path:
            self._open_project_path(path)

    def _open_project_path(self, path: str) -> None:
        if not self._maybe_confirm_discard():
            return
        try:
            self.project = load_project(path)
        except (ValueError, OSError) as exc:
            self.status_bar.showMessage(tr("app.status_open_failed", exc))
            return
        self._hidden_units.clear()
        self._reset_project_context()
        self._reset_unit_selection()
        self._project_path = path
        self._remember_recent(path)
        self._refresh_nav()
        self.center_stack.setCurrentWidget(self.editor)
        self._set_dirty(False)
        self._status_path("app.status_opened", path)
        if self.project.tree_path and Path(self.project.tree_path).exists():
            self._set_tree_path(self.project.tree_path)

    def save_project(self) -> None:
        default = self._project_path or f"{self.project.name}.pyitolproj"
        path, _ = QFileDialog.getSaveFileName(self, tr("fd.save_project"), default, tr("fd.filter_project"))
        if not path:
            return
        target = writable_target(path)
        if target is None:
            self.status_bar.showMessage(tr("app.status_bad_path"))
            return
        try:
            out = save_project(self.project, target)
        except OSError as exc:
            self.status_bar.showMessage(tr("app.status_save_failed", exc))
            return
        # The saved file name doubles as the project name — a rename entry that
        # also makes TEMPLATE_NAME meaningful (code review P2-5).
        self.project.name = Path(str(out)).stem
        self._project_path = str(out)
        self._remember_recent(str(out))
        self.welcome.refresh_recent()
        self._set_dirty(False)
        self._status_path("app.status_saved", out)

    def _palette_entries(self) -> list[PaletteEntry]:
        """The ⌘K index: units, then template types, then commands."""
        entries: list[PaletteEntry] = []
        for unit in self.project.units:
            entries.append(
                PaletteEntry(
                    kind=KIND_UNIT,
                    title=unit.label or unit.type_name,
                    hint=unit.type_name,
                    icon_name=type_icon_name(unit.type_name),
                    run=lambda uid=unit.unit_id: self.unit_list.select_unit(uid),
                )
            )
        for info in list_template_types():
            if not info.wizard_supported:
                continue
            entries.append(
                PaletteEntry(
                    kind=KIND_TYPE,
                    title=info.header,
                    hint=info.group_label,
                    icon_name=type_icon_name(info.type_name),
                    run=lambda name=info.type_name: self._open_wizard_for(name),
                )
            )
        entries.extend(self._command_entries())
        return entries

    def open_command_palette(self) -> None:
        """⌘K: jump to a unit, start a template type, or run a command.

        With 31 template types and a project that may hold half a dozen units,
        a searchable index is the shortest path to anything (design book §5.1).
        """
        palette = CommandPalette(self._palette_entries(), self)
        palette.exec()

    def _open_wizard_for(self, type_name: str) -> None:
        wizard = TemplateWizard(self, initial_type=type_name, project_name=self.project.name)
        if wizard.exec():
            self._absorb_wizard_result(wizard)

    def _add_unit_from_spec(self, spec) -> Unit:
        """Turn a generated :class:`UnitSpec` into a project unit (P2-3)."""
        unit = Unit(
            type_name=spec.type_name,
            label=spec.label,
            color=spec.color,
            separator=spec.separator,
            columns=list(spec.columns),
            data_rows=[dict(r) for r in spec.data_rows],
            parameters=dict(spec.parameters),
            legend=dict(spec.legend),
            source="manual",
        )
        self.project.add_unit(unit)
        return unit

    def _absorb_wizard_result(self, wizard: TemplateWizard) -> None:
        """Add the wizard's exported unit to the project and select it."""
        spec = getattr(wizard, "result_spec", None)
        if spec is None:
            self.status_bar.showMessage(tr("app.status_wizard_done"))
            return
        unit = self._add_unit_from_spec(spec)
        self.center_stack.setCurrentWidget(self.editor)
        self._refresh_nav()
        self.unit_list.select_unit(unit.unit_id)
        self._set_dirty(True)
        self.status_bar.showMessage(tr("app.status_wizard_added", unit.label or unit.type_name))

    def _command_entries(self) -> list[PaletteEntry]:
        """Every toolbar action, plus the rail's tree switcher, by name."""
        entries = [
            PaletteEntry(
                kind=KIND_COMMAND,
                title=tr("nav.tree_change"),
                hint="",
                icon_name="folder-tree",
                run=self.choose_tree_file,
            )
        ]
        for action in self._actions.values():
            if action is self._actions.get("palette"):
                continue  # calling the palette from itself would be a no-op
            entries.append(
                PaletteEntry(
                    kind=KIND_COMMAND,
                    title=action.text().replace("&", ""),
                    hint=action.shortcut().toString(QKeySequence.SequenceFormat.NativeText),
                    icon_name="terminal",
                    run=action.trigger,
                )
            )
        return entries

    def open_wizard(self) -> None:
        wizard = TemplateWizard(self, project_name=self.project.name)
        if wizard.exec():
            self._absorb_wizard_result(wizard)

    def import_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("fd.import_template"), "", tr("fd.filter_template")
        )
        if path:
            self._import_template_path(path)

    def _import_template_path(self, path: str) -> None:
        try:
            units = learn_from_file(path)
        except Exception as exc:  # noqa: BLE001
            self.status_bar.showMessage(tr("app.status_import_failed", exc))
            show_toast(self, tr("app.status_import_failed", exc), state="danger")
            return
        created: list[Unit] = []
        for learned in units:
            unit = Unit(
                type_name=learned.type_name,
                label=learned.label,
                color=learned.color,
                separator=learned.separator,
                columns=learned.columns,
                data_rows=[dict(r) for r in learned.data_rows],
                parameters=dict(learned.parameters),
                legend=dict(learned.legend),
                source="learned",
            )
            self.project.add_unit(unit)
            created.append(unit)
        self._refresh_nav()
        # Show the imported unit instead of leaving the welcome page on top.
        self.center_stack.setCurrentWidget(self.editor)
        if created:
            self.unit_list.select_unit(created[0].unit_id)
        self._set_dirty(True)
        self.status_bar.showMessage(tr("app.status_imported", len(units)))

    def refresh_preview(self) -> None:
        self._update_validation()
        if self.current_unit is None:
            self.preview.set_text(tr("preview.placeholder"))
            return
        if not self._loading_unit:
            self._set_dirty(True)  # a real parameter / table edit (code P1-6)
        values = self.inspector.values()
        extras = values.pop("__extra_params__", {})
        profile = {"DATASET_LABEL": values.pop("DATASET_LABEL", ""), "COLOR": values.pop("COLOR", "")}
        self.current_unit.parameters = {
            k: str(v) for k, v in values.items() if not k.startswith("LEGEND_") and not k.startswith("__") and v != ""
        }
        self.current_unit.parameters.update({k: v for k, v in extras.items() if str(v) != ""})
        self.current_unit.legend = {k: str(v) for k, v in values.items() if k.startswith("LEGEND_") and v != ""}
        if profile["DATASET_LABEL"]:
            self.current_unit.label = str(profile["DATASET_LABEL"])
        if profile["COLOR"]:
            self.current_unit.color = str(profile["COLOR"])
        self._sync_table_into_unit()
        spec = self.current_unit.to_spec(template_name=self.project.name)
        try:
            self.preview.set_text(generate_template_text(spec))
        except Exception as exc:  # noqa: BLE001
            self.preview.set_text(tr("preview.generate_failed", exc))
            show_toast(self, tr("preview.generate_failed", exc), state="danger")

    def export_current_template(self) -> None:
        """Write the selected unit (incl. table edits) to an iTOL template file."""
        if self.current_unit is None:
            self.status_bar.showMessage(tr("app.status_no_unit"))
            return
        values = self.inspector.values()
        if values:
            self.refresh_preview()  # reapplies form + table edits to the unit
        default = f"{self.current_unit.label or self.current_unit.type_name}.txt"
        path, _ = QFileDialog.getSaveFileName(self, tr("fd.export_template"), default, tr("fd.filter_template"))
        if not path:
            return
        target = writable_target(path)
        if target is None:
            self.status_bar.showMessage(tr("app.status_bad_path"))
            return
        from ..adapter import export_template_file

        try:
            out = export_template_file(self.current_unit.to_spec(template_name=self.project.name), target)
        except Exception as exc:  # noqa: BLE001
            self.status_bar.showMessage(tr("app.status_export_failed", exc))
            return
        self._status_path("app.status_exported", out)

    def _sync_table_into_unit(self) -> None:
        """Pull editor-table edits into the selected unit (FR-3 workbench)."""
        unit = self.current_unit
        if unit is None or self.editor.model.frame.empty:
            return
        frame = self.editor.model.frame
        unit.columns = [str(c) for c in frame.columns]
        unit.data_rows = self.editor.model.to_rows()

    def _on_generate_requested(self) -> None:
        """``生成模板`` (⌘↩) in the inspector footer."""
        if self.current_unit is None:
            self.status_bar.showMessage(tr("app.status_no_unit"))
            return
        self.refresh_preview()
        self.status_bar.showMessage(tr("app.status_generated"))

    def _update_validation(self) -> None:
        """Push the combined verdict into the inspector's pinned banner.

        The inspector owns no tree knowledge; the main window is the only
        place that knows both the reference leaf IDs and the edited table.
        Parameter-level field errors (required/range/colour) outrank the
        tree-match notice: they block a correct template, the tree verdict
        only affects iTOL's final render.
        """
        field_errors = self.inspector.field_error_count()
        if field_errors:
            self.inspector.set_validation("warn", tr("inspector.banner_fields", field_errors))
            self._update_tree_card()
            return
        if self.current_unit is None or self._leaf_ids is None:
            self.inspector.set_validation("muted", tr("inspector.banner_unchecked"))
            self._update_tree_card()
            return
        unmatched = self.editor.model.unmatched_ids()
        if unmatched:
            self.inspector.set_validation(
                "warn", tr("inspector.banner_unmatched", len(unmatched))
            )
        else:
            self.inspector.set_validation("ok", tr("inspector.banner_ok"))
        self._update_tree_card()

    def _load_unit_into_table(self, unit: Unit) -> None:
        columns = list(unit.columns) or (list(unit.data_rows[0].keys()) if unit.data_rows else [])
        frame = pd.DataFrame(unit.data_rows, columns=columns) if columns else pd.DataFrame()
        # The IDL is what turns a bare DataFrame into a typed grid (row numbers,
        # column labels, status column).
        self.editor.load_dataframe(frame, self._leaf_ids, self._current_idl)

    # ------------------------------------------------------------------
    def _set_tree_path(self, path: str) -> None:
        """Record the reference tree and load its tip labels on a worker
        thread so the table can flag IDs missing from the tree (FR-3)."""
        self.project.tree_path = path
        self._leaf_ids = None
        self._tree_loading = True
        self._set_dirty(True)  # choosing a tree is a project change
        self._refresh_nav()
        # Indeterminate "reading…" state on the tree card (review P1#3).
        self.rail.tree_card.set_tree(path, loading=True)
        from ..adapter import tree_leaf_ids

        # Generation guard: a fast A→B switch must let only B's result land,
        # even if A's worker finishes last (code review P1-5).
        self._tree_generation += 1
        generation = self._tree_generation
        task = EngineTask(tree_leaf_ids, path)

        def _ready(ids: set[str] | None) -> None:
            if generation != self._tree_generation:
                return  # a newer tree load superseded this one
            self._leaf_ids = ids
            self._tree_loading = False
            if self.current_unit is not None:
                self._load_unit_into_table(self.current_unit)
            self._update_tree_card()
            count = len(ids) if ids else 0
            if ids:
                self._status_path("app.status_tree_set", path, count)
            else:
                self._status_path("app.status_tree_set_no_ids", path)

        def _failed(message: str) -> None:
            if generation != self._tree_generation:
                return
            self._leaf_ids = None
            self._tree_loading = False
            self._update_tree_card()
            self.status_bar.showMessage(tr("app.status_tree_failed", message))

        task.finished_with.connect(_ready)
        task.failed.connect(_failed)
        self._track_task(task)
        task.start()

    def _track_task(self, task: EngineTask) -> None:
        """Hold a reference until the QThread finishes, so Python cannot GC a
        running worker (which aborts the thread mid-run)."""
        self._tasks.append(task)
        task.finished.connect(lambda: self._tasks.remove(task) if task in self._tasks else None)

    def _nav_item_for_unit(self, unit_id: str):
        """Locate the rail row for a unit id (None when absent)."""
        return self.unit_list.item_for_unit(unit_id)

    def open_upload(self) -> None:
        if not self.project.tree_path:
            path, _ = QFileDialog.getOpenFileName(self, tr("fd.select_tree"), "", tr("fd.filter_tree"))
            if not path:
                return
            self._set_tree_path(path)
        # The eye hides a unit from the upload without touching the project.
        units_to_upload = [u for u in self.project.units if u.unit_id not in self._hidden_units]
        if self._hidden_units:
            self.status_bar.showMessage(tr("nav.hidden_summary", len(self._hidden_units)))
        if not units_to_upload:
            self._show_upload_dialog([], [])
            return
        # Engine calls stay on a worker thread: render every unit of the
        # project to a template file, then hand the paths to the dialog.
        from ..adapter import export_template_file

        units = [u.to_spec(template_name=self.project.name) for u in units_to_upload]
        out_dir = Path(tempfile.mkdtemp(prefix="pyitolstudio_upload_"))
        self._temp_dirs.append(out_dir)  # cleaned once the dialog closes (P2-6)

        def _write_units() -> list[str]:
            return [str(export_template_file(spec, out_dir / f"{i + 1:02d}_{spec.type_name}.txt"))
                    for i, spec in enumerate(units)]

        self.status_bar.showMessage(tr("app.status_upload_exporting"))
        task = EngineTask(_write_units)

        def _ready(paths: list[str]) -> None:
            self.status_bar.showMessage(tr("app.status_upload_ready", len(paths)))
            self._show_upload_dialog(paths, [out_dir])

        def _failed(message: str) -> None:
            self.status_bar.showMessage(tr("app.status_upload_export_failed", message))
            self._show_upload_dialog([], [out_dir])

        task.finished_with.connect(_ready)
        task.failed.connect(_failed)
        self._track_task(task)
        task.start()

    def _show_upload_dialog(self, template_paths: list[str],
                            temp_dirs: list[Path] | tuple[Path, ...] = ()) -> None:
        dialog = UploadDialog(
            self.project.tree_path, template_paths, "", self,
            project_name=self.project.name,
        )
        dialog.exec()
        # The dialog is modal: once it closes the exported temp files are no
        # longer needed — remove them so repeat uploads do not litter the OS
        # temp dir (code review P2-6).
        for directory in temp_dirs:
            shutil.rmtree(directory, ignore_errors=True)
            if directory in self._temp_dirs:
                self._temp_dirs.remove(directory)

    def open_config_editor(self) -> None:
        ConfigEditorDialog(self).exec()

    # ------------------------------------------------------------------
    def _refresh_nav(self) -> None:
        """Rebuild the left rail: tree card + unit list (design book §5.1)."""
        self.unit_list.set_units(
            self.project.units,
            self._hidden_units,
            selected_id=self.current_unit.unit_id if self.current_unit else None,
        )
        self.rail.set_count(len(self.project.units))
        self._update_tree_card()

    def _update_tree_card(self) -> None:
        """Keep the tree card's match counter in step with the edited table."""
        if self._tree_loading:
            return  # the indeterminate "reading…" state owns the card until done
        path = self.project.tree_path
        leaf_count = len(self._leaf_ids) if self._leaf_ids else None
        matched = total = 0
        if self._leaf_ids is not None and self.current_unit is not None:
            rows = self.editor.model.rowCount()
            _, matched, _missing = self.editor.model.match_stats()
            total = rows
        self.rail.tree_card.set_tree(path, leaf_count, matched, total)

    def choose_tree_file(self) -> None:
        """``更换树文件`` in the tree card."""
        start = str(Path(self.project.tree_path).parent) if self.project.tree_path else ""
        path, _ = QFileDialog.getOpenFileName(self, tr("fd.select_tree"), start, tr("fd.filter_tree"))
        if path:
            self._set_tree_path(path)

    def _on_unit_activated(self, unit_id: str) -> None:
        unit = self.project.get_unit(unit_id)
        if unit is None:
            return
        self.current_unit = unit
        self._loading_unit = True
        try:
            self._load_unit_body(unit)
        finally:
            self._loading_unit = False

    def _load_unit_body(self, unit: Unit) -> None:
        try:
            idl = build_form_idl(unit.type_name)
        except KeyError:
            # e.g. a template type the bundled engine does not register
            self.inspector.set_idl(None, None)
            self.preview.set_text(tr("preview.unknown_type", unit.type_name))
            self.status_bar.showMessage(tr("app.status_unknown_type", unit.type_name))
            return
        learned = _unit_as_learned(unit)
        values = to_form_values(learned, idl)
        self._current_idl = idl
        self.inspector.set_unit(unit.label or unit.type_name, unit.type_name)
        self.inspector.set_idl(idl, values)
        self._load_unit_into_table(unit)
        self.refresh_preview()

    def _reset_unit_selection(self) -> None:
        """Drop the unit selection so edits can never leak into a unit that
        no longer belongs to the active project."""
        self.current_unit = None
        self._current_idl = None
        self.inspector.set_unit("", "")
        self.inspector.set_idl(None, None)
        self.editor.load_dataframe(pd.DataFrame())
        self.preview.set_text(tr("preview.placeholder"))
        self._update_validation()
        self._update_tree_card()

    def _toggle_unit_hidden(self, unit_id: str) -> None:
        """The eye: exclude a unit from the next upload.

        UI-only state — the .pyitolproj schema is frozen for this iteration.
        """
        if unit_id in self._hidden_units:
            self._hidden_units.discard(unit_id)
        else:
            self._hidden_units.add(unit_id)
        self.unit_list.set_hidden(unit_id, unit_id in self._hidden_units)
        if self._hidden_units:
            self.status_bar.showMessage(tr("nav.hidden_summary", len(self._hidden_units)))
        else:
            self.status_bar.showMessage(tr("app.status_ready"))

    def _reorder_units(self, ordered_ids: list[str]) -> None:
        """Dragging a row rewrites the dataset order iTOL will stack."""
        index = {unit_id: position for position, unit_id in enumerate(ordered_ids)}
        self.project.units.sort(key=lambda u: index.get(u.unit_id, len(index)))
        self._set_dirty(True)

    def _show_nav_menu_at(self, pos) -> None:
        """Right-click anywhere on a unit row."""
        item = self.unit_list.itemAt(pos)
        if item is None:
            return
        unit_id = item.data(UNIT_ID_ROLE)
        self._open_unit_menu(str(unit_id), self.unit_list.viewport().mapToGlobal(pos))

    def _show_nav_menu(self, unit_id: str, global_pos) -> None:
        """Overflow (⋯) on a unit row."""
        self._open_unit_menu(str(unit_id), global_pos)

    def _open_unit_menu(self, unit_id: str, global_pos) -> None:
        if self.project.get_unit(unit_id) is None:
            return
        hidden = unit_id in self._hidden_units
        menu = QMenu(self)
        toggle = menu.addAction(
            icon("eye-off" if not hidden else "eye", 16),
            tr("nav.show_unit") if hidden else tr("nav.hide_unit"),
        )
        menu.addSeparator()
        delete_action = menu.addAction(icon("trash", 16), tr("nav.delete"))
        chosen = menu.exec(global_pos)
        if chosen == toggle:
            self._toggle_unit_hidden(unit_id)
        elif chosen == delete_action and self.project.remove_unit(unit_id):
            self._hidden_units.discard(unit_id)
            if self.current_unit is not None and self.current_unit.unit_id == unit_id:
                self._reset_unit_selection()
            self._refresh_nav()
            self._set_dirty(True)
            self.status_bar.showMessage(tr("app.status_deleted"))

    # drag & drop (FR-11)
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        tree_suffixes = {".nwk", ".newick", ".tre", ".tree", ".nex", ".nexus"}
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path or not Path(path).exists():
                continue
            suffix = Path(path).suffix.lower()
            if suffix == ".pyitolproj":
                self._open_project_path(path)
            elif suffix == ".txt":
                # `.txt` is ambiguous: the tree filter also accepts *.txt, so a
                # Newick saved as .txt would otherwise be parsed as a template
                # and error out (code review P3-5).  Sniff the content.
                if _looks_like_newick(path):
                    self._set_tree_path(path)
                else:
                    self._import_template_path(path)
            elif suffix in tree_suffixes:
                self._set_tree_path(path)
            else:
                # Anything else (image, PDF, …) is not a project, template or
                # tree — reject it visibly instead of failing later on a worker.
                show_toast(self, tr("app.status_drop_rejected", path), state="danger")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if not self._maybe_confirm_discard():
            event.ignore()
            return
        for directory in list(self._temp_dirs):
            shutil.rmtree(directory, ignore_errors=True)
        self._temp_dirs.clear()
        # Stop the locale listener from holding (and later calling into) a
        # destroyed window (code review P2-10).
        translator().remove_listener(self.retranslate_ui)
        super().closeEvent(event)

    def _remember_recent(self, path: str) -> None:
        settings = QSettings()
        recent = settings.value(RECENT_KEY, []) or []
        if isinstance(recent, str):
            recent = [recent]
        recent = [path] + [p for p in recent if p != path]
        settings.setValue(RECENT_KEY, recent[:8])


def _looks_like_newick(path: str | Path) -> bool:
    """Whether a ``.txt`` the user dropped is really a Newick tree.

    The tree filter also accepts ``*.txt``, so extension alone is ambiguous —
    sniff the first substantive line instead (code review P3-5).
    """
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                return stripped.startswith("(")
    except OSError:
        return False
    return False


def _unit_as_learned(unit: Unit):
    """Adapt a stored Unit to the learner bridge shape for form mapping."""
    from ..adapter.learner_bridge import LearnedUnit

    return LearnedUnit(
        type_name=unit.type_name,
        header="",
        separator=unit.separator,
        label=unit.label,
        color=unit.color,
        columns=unit.columns,
        data_rows=unit.data_rows,
        parameters=unit.parameters,
        legend=unit.legend,
        source_file="",
    )
