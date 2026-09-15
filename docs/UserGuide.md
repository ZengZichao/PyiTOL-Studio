# PyiTOL Studio User Guide

**PyiTOL Studio** — a desktop workbench for iTOL annotation. A native macOS
graphical application (PySide6) built on the [pyitol](../../PyiTOL-项目代码/)
engine as its single source of template logic. It provides visual generation
of iTOL annotation templates, reverse mapping of existing templates back into
editable units (learner), visual editing of the pyitol YAML configuration, and
batch upload/export to iTOL.

- Chinese manual: [用户手册.md](用户手册.md)
- Applies to: PyiTOL Studio 0.3.x (engine pyitol ≥ 1.0.3)
- Last updated: 2026-09-12

> **0.3.0 interface redesign.** This release rebuilds every screen on the
> *Instrument Dark* design system (deep mode is the default, light mode is a
> first-class peer).  The left rail is now a tree card plus a drag-reorderable
> annotation-unit list; the middle pane is a structured data grid with a row
> ruler, a status chip column and tinted rows for IDs missing from the tree;
> the right inspector has search, collapsible groups, per-field defaults and a
> pinned validation banner above `Generate template`.  Plus a `⌘K` command
> palette, `⌘N/⌘O/⌘S/⌘⇧E` shortcuts, and a welcome page with three action
> cards and recent projects that show their path and unit count.

---

## Contents

1. [Overview & feature map](#1-overview--feature-map)
2. [Installation & launch](#2-installation--launch)
3. [Interface tour](#3-interface-tour)
4. [Creating and opening projects](#4-creating-and-opening-projects)
5. [Template wizard (recommended starting point)](#5-template-wizard-recommended-starting-point)
6. [Main workbench: data table · inspector · live preview](#6-main-workbench-data-table--inspector--live-preview)
7. [Template reverse mapping (import existing iTOL templates)](#7-template-reverse-mapping-import-existing-itol-templates)
8. [Project management: save · recent projects · deleting units](#8-project-management-save--recent-projects--deleting-units)
9. [pyitol configuration generator](#9-pyitol-configuration-generator)
10. [Uploading to iTOL and exporting](#10-uploading-to-itol-and-exporting)
11. [Drag & drop and shortcuts](#11-drag--drop-and-shortcuts)
12. [The .pyitolproj project file format](#12-the-pyitolproj-project-file-format)
13. [Security and privacy](#13-security-and-privacy)
14. [FAQ and troubleshooting](#14-faq-and-troubleshooting)
15. [Appendix: all 31 template types and column layouts](#15-appendix-all-31-template-types-and-column-layouts)

---

## 1. Overview & feature map

PyiTOL Studio brings the full iTOL annotation workflow of the
[pyitol](../../PyiTOL-项目代码/) command-line engine into a graphical
interface:

| Feature | What it does | Engine capability used |
|---|---|---|
| Template wizard | Pick type → paste data → fill parameters → preview → export `.txt` | `create_schema` + `TemplateGenerator` (31 types) |
| Main workbench | Data table + parameter inspector + live syntax-highlighted preview | same |
| Reverse mapping | Parse an existing iTOL template `.txt` back into editable units (type/separator/parameters/data fully back-filled) | `learn_template` |
| Config generator | Visually edit the pyitol YAML config; fields map 1:1 to the engine's `config.example.yaml` | `--config` |
| Upload & export | Batch-upload a Newick tree + templates to iTOL; export in 8 formats | `ITOLAPIClient` |
| Project files | `.pyitolproj` (JSON) stores all annotation units; session resume and version checking | — |

The interface follows macOS visual conventions and automatically follows the
system light/dark appearance. All toolbar actions and dialogs use Lucide vector
icons. The app supports live Chinese/English switching via the globe icon in
the toolbar; the language preference is saved automatically.

## 2. Installation & launch

PyiTOL Studio ships in two forms: a **packaged `.app`** (recommended — no
Python setup required) and a **pip source install**.

### 2.1 Requirements

- macOS 12+ (Apple Silicon / Intel)
- Python ≥ 3.10 (3.11 recommended; source install only)
- pyitol engine ≥ 1.0.3
- PySide6 ≥ 6.5, pandas ≥ 2.0, PyYAML ≥ 6.0

### 2.2 Option A — packaged .app (recommended)

Drag `PyiTOL Studio.app` into your Applications folder and double-click to
launch. Python, PySide6 and the pyitol engine are bundled inside the app.

- If Gatekeeper blocks the first launch (unsigned build): right-click the
  app → "Open", or run `xattr -cr "/Applications/PyiTOL Studio.app"` once.
- Build it yourself: `pyinstaller packaging/pyitolstudio.spec` — the bundle
  lands in `dist/PyiTOL Studio.app` (see `packaging/README.md`).

### 2.3 Option B — pip source install

```bash
# 1) Prepare an environment (micromamba/conda, or reuse an existing pyitol env)
micromamba create -n python-3.11 python=3.11 -y
micromamba activate python-3.11

# 2) Install the pyitol engine (either way)
pip install pyitol                         # from PyPI
# or from source:
pip install -e /path/to/PyiTOL-项目代码

# 3) Install PyiTOL Studio
pip install "PySide6>=6.5" pandas pyyaml
pip install -e /path/to/PyiTOL-studio-项目代码

# 4) Launch
pyitol-studio            # or: python -m pyitolstudio
```

### 2.4 Verify the installation (optional)

```bash
# Core logic tests (no display needed; Qt cases auto-skip without a display)
cd /path/to/PyiTOL-studio-项目代码
pytest
```

## 3. Interface tour

The app opens on the **welcome page**; after creating/opening a project you
get the **three-pane workbench**.

```
┌──────────┬──────────────────────────────┬──────────────┐
│ Project  │  Data table (QTableView,     │  Parameter   │
│ navigator│  paste directly from Excel)  │  inspector   │
│ · tree   │──────────────────────────────│  (form auto- │
│ · units  │  Template preview (syntax    │   generated  │
│          │  highlighting)               │   per type)  │
└──────────┴──────────────────────────────┴──────────────┘
Toolbar: New | Open | Save | Wizard | Import template | Preview | Export current template | Upload iTOL | Config file | Language (globe icon)
```

- **Language switching**: click the globe icon at the end of the toolbar and
  choose "中文" (Chinese) or "English" to switch the UI language in real time
  — no restart needed. The preference is saved automatically and restored on
  next launch.

- **Left — project navigator**: the current tree file and every annotation
  unit; right-click a unit to delete it.
- **Center**: the data table on top — kept in two-way sync with the selected
  unit (selecting a unit loads its rows; editing a cell writes back into the
  unit and refreshes the preview; first-column IDs missing from the reference
  tree and empty cells are flagged in red) — and the template text preview
  below (type headers, the SEPARATOR line, comments, parameter keys and hex
  colors are highlighted; hex colors render in their own color).
- **Right — parameter inspector**: the form for the selected unit. Control
  types come from a declarative IDL (text/int/float/color/checkbox/choice/
  list); any change refreshes the preview immediately.
- Hover any parameter label for its official help text.

## 4. Creating and opening projects

- **New project**: toolbar "新建" (New) or the welcome-page card. The project
  starts with no tree file selected.
- **Open project**: toolbar "打开工程" (Open) and pick a `.pyitolproj` file;
  or **double-click** an entry in the welcome page's recent-projects list; or
  drag a `.pyitolproj` file into the window.
- Opening/creating a project clears the previous unit selection so edits can
  never leak into an object that is no longer part of the active project.
- Project files written by a newer Studio version are rejected with an
  explicit "project file version is too new" message.

> The tree file can be left unset for now: pressing "上传 iTOL" (Upload)
> prompts for it when needed.

## 5. Template wizard (recommended starting point)

Open it from the toolbar ("模板向导"). Four steps:

### Step 1 · Choose a type

- Types are grouped by the official iTOL categories: **Datasets / Tree
  structure / Metadata / Advanced**; the highest-frequency P0 types
  (COLORSTRIP, SIMPLEBAR, MULTIBAR, HEATMAP, BINARY, TREE_COLORS, LABELS)
  come first.
- 29 of the engine's 31 registered types are wizard-capable
  (`DATASET_MANUAL` and `DATASET_TREESTYLE` are interactive/tree-style types
  without a wizard form).

### Step 2 · Import data

- Paste table text into the box, or click "导入 CSV/TSV…" to read a file.
- The **separator drop-down** selects `TAB / SPACE / COMMA`; pasting and file
  import both parse with the selected separator, and the placeholder text
  follows it.
- Column layout is determined by the chosen type (e.g. COLORSTRIP is
  `tree ID | strip label | color #hex`; dynamic-column types such as
  MULTIBAR/HEATMAP auto-name `value_1, value_2, …`).
- "粘贴示例" (paste sample) generates three sample rows shaped like the
  chosen type's columns — hex colors for color columns, text for label/text
  columns, shape names for shape columns, numbers for value/position columns,
  with dynamic columns filled in — so you can generate a preview immediately.

### Step 3 · Parameters

- The form is generated per type: dataset label, color, strip width, margins,
  etc.; hover for official explanations.
- Values from choice drop-downs, checkboxes and color pickers are written
  faithfully into the template.

### Step 4 · Preview & export

- Live preview of the iTOL v7 template text.
- "导出模板…" exports a `.txt` file. Output follows the official rule: the
  **SEPARATOR line is always written as `SEPARATOR <NAME>` with a single
  space**, regardless of the separator used in the data section.
- If a data value contains the active separator character (e.g. a comma in
  COMMA mode), generation fails with a row-and-field level error instead of
  silently corrupting the column layout; SPACE mode imposes no restriction
  because iTOL tolerates spaces in free text.

After exporting, the wizard closes and the main window's status bar reports
completion. To keep editing the template inside Studio, use "导入模板"
(Import template) to reverse-map the exported `.txt` back into a unit.

## 6. Main workbench: data table · inspector · live preview

1. Click an annotation unit in the left pane → its form appears on the right,
   its data rows load into the table, and a preview is generated immediately.
2. **The table and the unit stay in sync**: double-click to edit cells —
   changes are written back into the selected unit and the preview refreshes.
   The table accepts ⌘V (or right-click → "paste clipboard data") for
   Excel/TSV data (TAB / comma / whitespace auto-detected). Once a tree file
   is set or a project with a tree is opened, Studio reads the tree's tip
   labels in the background: first-column IDs absent from the tree, and empty
   cells, are flagged with a red background.
3. **Parameter inspector**: every change (text commit, checkbox, drop-down,
   color) regenerates the preview instantly — no manual refresh needed.
4. The "生成预览" (Preview) toolbar button forces a refresh at any time;
   "导出当前模板" (Export current template) writes the selected unit —
   including table edits — to a `.txt` template file.
5. If a "— other parameters (discovered by the learner) —" section appears at
   the bottom of the form, the imported template contained parameters outside
   the bundled catalog; edit them there and they will be written back on
   export.

## 7. Template reverse mapping (import existing iTOL templates)

Use the toolbar "导入模板" (or drag a `.txt` into the window) and pick an iTOL
template file:

- Studio invokes the engine's learner to parse every dataset block — type,
  header, separator, label, color, all parameters, legend (`LEGEND_*`) and
  data rows — and adds each as an annotation unit to the current project.
- Select a unit in the left pane to see the back-filled form; change
  parameters or data and export again, or go straight to "上传 iTOL".
- Round-trip consistency (learn → generate → learn) is regression-tested on
  nine representative types out of a bundled suite of 45 official iTOL v7
  fixtures (type, header, separator, parameter set and row count must match
  exactly).
- Files without a recognizable dataset are reported as such in the status
  bar.
- If a template uses a type the engine does not register (rare custom types),
  selecting the unit shows an "unknown template type" message; other units
  are unaffected.

## 8. Project management: save · recent projects · deleting units

- **Save**: toolbar "保存工程" → choose a `.pyitolproj` path (the extension is
  appended automatically). Saving is atomic (temp file + replace), so a
  half-written file can never appear.
- **Recent projects**: the welcome page lists the last 8 projects (only paths
  that still exist); double-click to open.
- **Delete a unit**: right-click it in the navigator → "删除注释单元". The
  unit is removed immediately; if it was selected, the inspector and preview
  reset.

## 9. pyitol configuration generator

The toolbar "配置文件" opens a visual editor whose fields map 1:1 to the
engine's `config.example.yaml` (enforced by a test):

| Field | Meaning | Default |
|---|---|---|
| `api_key_file` | Path to a plain-text iTOL API key file | `.itolapi.key` |
| `default_format` | svg/png/pdf/tiff/eps/newick/nexus/phyloxml | `svg` |
| `output_directory` | Export output directory | `.` |
| `template_directory` / `tree_directory` | template/tree folders (empty = current dir) | empty |
| `log_level` | DEBUG…CRITICAL | `INFO` |
| `log_file` | Log file (empty = console only) | empty |
| `multi_tree_mode` | ask/first/last/random/split/all | `ask` |
| `name_format` | auto/gtdb/embedded/ncbi/underscore/mixed | `auto` |
| `taxonomy_delimiter_mode` | segment/reverse/greedy | `segment` |

- "导出 YAML…" saves the file; export paths are normalized and `..`
  traversal is rejected. Any location confirmed in the native save dialog is
  writable — including external volumes.
- Values containing YAML-special characters (colons, hashes, quotes, …) are
  automatically double-quoted, and empty strings are written explicitly as
  `""` (not null), so `pyitol --config <file>` always parses.
- Invalid values are all reported before export.
- Cancelling the save dialog returns silently — no error is shown; unwritable
  targets report the OS error inside the dialog.

## 10. Uploading to iTOL and exporting

### 10.1 Prerequisites

1. An **iTOL subscription account** (required by the iTOL batch API).
2. An **API key**, provided in one of two ways (never typed into or stored by
   the app):
   - environment variable: `export ITOL_API_KEY=YOURKEY` (recommended; set it
     before launching `pyitol-studio`);
   - a local key file containing only the plain-text key; put its path in the
     dialog's "API 密钥文件" field.
3. A Newick tree file (`.nwk/.newick/.tre/.tree/.txt`).

### 10.2 Workflow

1. Press the toolbar "上传 iTOL":
   - if the project has no tree yet, a picker appears first;
   - if the project has annotation units, they are first **exported to
     template files automatically** on a background thread (progress is shown
     in the status bar); the upload dialog then opens with the template list
     pre-filled.
2. In the dialog you can:
   - adjust the tree path;
   - "添加模板…" add any `.txt` templates / "移除所选" remove selected ones;
   - pick the export format (8 options);
   - set the **output directory** (defaults to the tree file's folder);
   - check "覆盖 iTOL 上同名工程（force）".
3. Click "上传并导出": the progress bar turns busy; the engine retries
   automatically (HTTP 429/500/502/503/504, exponential backoff).
4. On success you get the `tree_id` and exported file paths; on failure the
   engine's error message is shown and you can retry.
5. **The dialog cannot be closed while an upload runs**, protecting the
   background worker; it closes normally once finished.

> Note: the iTOL batch endpoints have no idempotency keys; a retried upload
> may create duplicate trees on the server. Verify the target project on iTOL
> afterwards (the engine logs a warning on every retried POST).

## 11. Drag & drop and shortcuts

Drag files onto the main window:

| Dropped file | Action |
|---|---|
| `.pyitolproj` | Open the project |
| `.txt` | Reverse-map as an iTOL template (learner) |
| anything else (`.nwk`/`.newick`, …) | Set as the project's tree file and load its tip labels for ID validation |

- Extension checks are case-insensitive; non-existent paths are ignored.
- Double-click a recent-project entry on the welcome page to open it.

## 12. The .pyitolproj project file format

`.pyitolproj` is a versioned JSON text file (transparent, diffable,
version-control friendly):

```json
{
  "pyitolproj_version": 1,
  "name": "Untitled project",
  "tree_path": "/path/to/tree.nwk",
  "units": [
    {
      "unit_id": "1a2b3c4d5e6f",
      "type_name": "dataset_colorstrip",
      "label": "phylum_strip",
      "color": "#dd4477",
      "separator": "TAB",
      "columns": ["id", "value", "color"],
      "data_rows": [{"id": "A", "value": "1", "color": "#ff0000"}],
      "parameters": {"STRIP_WIDTH": "25"},
      "legend": {},
      "source": "manual"
    }
  ]
}
```

- `DATASET_LABEL`/`COLOR` live in the unit's `label`/`color` fields and are
  not duplicated into `parameters`.
- Files with a newer version are rejected with an upgrade hint; broken JSON
  or a missing `units` field produces an explicit error.

## 13. Security and privacy

- **The API key comes only from the `ITOL_API_KEY` environment variable or a
  key file**; the UI offers no plain-text key input and never persists keys.
- All dialog-produced write paths are normalized, and `..` traversal segments
  are rejected *before* normalization (so `/a/../../etc` cannot be silently
  rewritten into a legal path); there is no directory allowlist — anywhere
  the user confirmed in the native file dialog is writable.
- Uploads go over HTTPS to the official iTOL batch endpoints only.

## 14. FAQ and troubleshooting

**Q1: Why is there no tree drawing in the preview?**
v1 previews the template text; rendering happens remotely after upload.
Export SVG/PDF from iTOL for the figure.

**Q2: COMMA export fails with "contains the separator"?**
A value containing a comma would corrupt the column layout. Clean the
flagged row/field or switch to TAB/SPACE.

**Q3: Double-clicking a recent project does nothing / reports a failure?**
The file may have been moved or deleted (only existing paths are listed).
If it still fails, the status bar shows the concrete reason (invalid JSON,
version too new, …).

**Q4: Upload says "iTOL API key not found"?**
Set `ITOL_API_KEY` and **restart** Studio, or fill in the key-file path in
the dialog.

**Q5: An imported unit has no form?**
Its type is not registered by the installed engine version ("unknown
template type"). Upgrade the pyitol engine.

**Q6: A drop-down change does not appear in the template?**
This was a bug in preview builds; it is fixed in the current version —
please upgrade and report an issue if it recurs.

**Q7: How do I run tests headlessly?**
`QT_QPA_PLATFORM=offscreen pytest tests/test_app_qt.py`. Without Qt
installed, Qt cases skip automatically and the core tests still run.

**Q8: How many templates can one upload contain?**
Uploads go through the iTOL batch API (a single zip); Studio imposes no
limit — server-side limits apply.

**Q9: The packaged .app is blocked on first launch?**
Unsigned builds trigger Gatekeeper: right-click the app → "Open", or run
`xattr -cr "/Applications/PyiTOL Studio.app"`. For public distribution,
follow the signing/notarization steps in `packaging/README.md`.

**Q10: Some table IDs are flagged red?**
When a reference tree is loaded, first-column IDs missing from the tree are
flagged — usually a spelling mismatch (hyphens vs. underscores, …). Without
a tree file, no validation is applied.

## 15. Appendix: all 31 template types and column layouts

The 29 wizard-capable types (semantic column names as shown in Studio):

| Group | Type (engine name → iTOL header) | Data columns |
|---|---|---|
| Datasets | `dataset_colorstrip` → DATASET_COLORSTRIP | ID / label / color |
| Datasets | `dataset_simple_bar` → DATASET_SIMPLEBAR | ID / bar height |
| Datasets | `dataset_multibar` → DATASET_MULTIBAR | ID / value_1… (dynamic) |
| Datasets | `dataset_heatmap` → DATASET_HEATMAP | ID / value_1… (dynamic) |
| Datasets | `dataset_binary` → DATASET_BINARY | ID / field_1… (dynamic) |
| Datasets | `dataset_piechart` → DATASET_PIECHART | ID / value_1… (dynamic) |
| Datasets | `dataset_boxplot` → DATASET_BOXPLOT | ID / value_1… (dynamic) |
| Datasets | `dataset_gradient` → DATASET_GRADIENT | ID / value / color |
| Datasets | `dataset_text` → DATASET_TEXT | ID / text |
| Datasets | `dataset_symbols` → DATASET_SYMBOLS | ID / type / value / color / label |
| Datasets | `dataset_externalshape` → DATASET_EXTERNALSHAPE | ID / type / value / color / label |
| Datasets | `dataset_domains` → DATASET_DOMAINS | ID / from / to / type / label / color |
| Datasets | `dataset_arrows` → DATASET_ARROWS | ID / position / value |
| Datasets | `dataset_linechart` → DATASET_LINECHART | ID / position / value |
| Datasets | `dataset_alignment` → DATASET_ALIGNMENT | ID / alignment |
| Datasets | `dataset_range` → DATASET_RANGE | ID / label / color |
| Datasets | `dataset_connection` → DATASET_CONNECTION | ID1 / ID2 / color / width / line type |
| Datasets | `dataset_tanglegram` → DATASET_TANGLEGRAM | ID1 / ID2 / color / width |
| Datasets | `dataset_image` → DATASET_IMAGE | ID / image path / width |
| Datasets | `dataset_meme` → DATASET_MEME | ID / start / end / name |
| Datasets | `dataset_placement` → DATASET_PLACEMENT | ID / position / count / label / color |
| Tree | `dataset_tree_colors` → TREE_COLORS | ID / type / color / style / size |
| Tree | `dataset_labels` → LABELS | ID / label |
| Tree | `dataset_collapse` → COLLAPSE | node ID |
| Tree | `dataset_prune` → PRUNE | node ID |
| Tree | `dataset_spacing` → SPACING | node ID / factor |
| Metadata | `dataset_popup_info` → POPUP_INFO | ID / title / content |
| Advanced | `dataset_style` → DATASET_STYLE | ID / type / color / style |
| Advanced | `dataset_timescale` → DATASET_TIMESCALE | time point / label |

Not wizard-capable (2): `dataset_manual` (DATASET_MANUAL, interactive drawing
layer) and `dataset_treestyle` (DATASET_TREESTYLE, tree style parameters).

> Note: of these, 22 types are accepted by the iTOL batch uploader (see the
> acceptance table in the pyitol manuscript §4.4); the rest can still be
> generated and uploaded through the iTOL web interface.

---

> **Citation**  
> If you use PyiTOL Studio in your research or teaching, please also cite PyiTOL:  
> **PyiTOL: reproducible Python workflows for iTOL annotation and taxonomic monophyly assessment**  
> GitHub: https://github.com/ZengZichao/PyiTOL  
> DOI: https://doi.org/10.64898/2026.08.27.747471

*PyiTOL Studio is MIT-licensed; the annotation engine capabilities belong to
the pyitol project.*
