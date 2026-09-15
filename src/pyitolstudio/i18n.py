"""Internationalisation (i18n) — bilingual Chinese / English support.

A lightweight ``tr()`` mechanism: a singleton ``Translator`` holds the
active locale and looks up keys in a pair of flat dictionaries.  Qt widgets
call ``tr()`` at construction time and again on ``retranslate_ui()`` after
the locale is switched at runtime.
"""

from __future__ import annotations

import weakref

from PySide6.QtCore import QSettings

# ---------------------------------------------------------------------------
# Translation dictionaries
# ---------------------------------------------------------------------------

_ZH: dict[str, str] = {
    # — app / window —
    "app.title": "PyiTOL Studio",
    "app.subtitle": "iTOL 注释桌面工作台",
    "app.status_ready": "就绪（引擎：pyitol）",
    "app.status_new_project": "已新建工程",
    "app.status_opened": "已打开：{}",
    "app.status_open_failed": "打开失败：{}",
    "app.status_saved": "已保存：{}",
    "app.status_save_failed": "保存失败：{}",
    "app.status_wizard_done": "向导完成：模板已导出",
    "app.status_imported": "已导入 {} 个注释单元（类型/参数/数据已回填表单）",
    "app.status_import_failed": "反推失败：{}",
    "app.status_no_unit": "未选择注释单元：请先在左侧导航选择一个单元",
    "app.status_exported": "已导出：{}",
    "app.status_export_failed": "导出失败：{}",
    "app.status_tree_set": "树：{} · {} 个叶 ID · 已校验",
    "app.status_tree_set_no_ids": "树：{} · 未读到叶 ID，跳过校验",
    "app.status_tree_failed": "树文件解析失败：{}",
    "app.status_drop_rejected": "不支持的文件类型（仅支持 .pyitolproj / .txt / Newick 树文件）：{}",
    "app.status_upload_exporting": "正在导出注释单元为模板文件…",
    "app.status_upload_ready": "已就绪：{} 个模板待上传",
    "app.status_upload_export_failed": "模板导出失败，仅上传树文件：{}",
    "app.status_deleted": "已删除注释单元",
    "app.status_generated": "已按当前参数重新生成模板预览",
    "app.status_unknown_type": "未知模板类型：{}（预览与表单不可用）",
    "app.unsaved_title": "有未保存的修改",
    "app.unsaved_msg": "当前工程有未保存的修改。要如何处理？",
    "app.unsaved_save": "保存并继续",
    "app.unsaved_discard": "丢弃修改",
    "app.unsaved_cancel": "取消",
    "app.status_bad_path": "路径无效：目标包含 .. 穿越段，已拒绝",
    "app.status_wizard_added": "向导已生成并加入工程：{}",

    # — welcome page —
    "welcome.new_project": "新建工程",
    "welcome.new_project_desc": "导入 Newick 树与数据表，从零生成注释模板",
    "welcome.open_project": "打开工程",
    "welcome.open_project_desc": "继续编辑 .pyitolproj，恢复全部注释单元",
    "welcome.examples": "模板向导",
    "welcome.examples_desc": "从 31 种官方类型分步新建一个注释模板",
    "welcome.key_new": "⌘N",
    "welcome.key_open": "⌘O",
    "welcome.recent": "最近工程",
    "welcome.unit_count": "{} 个注释单元",
    "welcome.drop_prefix": "将",
    "welcome.drop_tree": "Newick 树",
    "welcome.drop_or": "或",
    "welcome.drop_template": "iTOL 模板文件",
    "welcome.drop_suffix": "拖入窗口即可开始",

    # — navigator —
    "nav.tree": "树：{}",
    "nav.tree_none": "树：（未选择）",
    "nav.units": "注释单元（{}）",
    "nav.units_caption": "注释单元",
    "nav.tree_change": "更换树文件",
    "nav.tree_meta": "{} 个叶节点 · Newick",
    "nav.tree_meta_unknown": "叶节点数未知",
    "nav.tree_match": "{} / {} ID 已匹配",
    "nav.tree_match_none": "未校验",
    "nav.tree_loading": "正在读取叶 ID…",
    "nav.search_placeholder": "搜索注释单元…",
    "nav.hide_unit": "隐藏注释单元",
    "nav.show_unit": "显示注释单元",
    "nav.hidden_summary": "已隐藏 {} 个注释单元，上传时将跳过",
    "nav.collapse_panel": "收起左栏",
    "nav.expand_panel": "展开左栏",
    "nav.delete": "删除注释单元",

    # — toolbar —
    "tb.new": "新建",
    "tb.open": "打开工程",
    "tb.save": "保存工程",
    "tb.wizard": "模板向导",
    "tb.import": "导入模板",
    "tb.preview": "生成预览",
    "tb.export": "导出当前模板",
    "tb.upload": "上传 iTOL",
    "tb.config": "配置文件",
    "tb.more": "更多操作",
    "tb.language": "语言",
    "tb.theme": "外观",
    "tb.toggle_rail": "显示/收起左栏",
    "tb.toggle_inspector": "显示/收起检查器",

    # — appearance menu —
    "theme.system": "跟随系统",
    "theme.dark": "深色",
    "theme.light": "浅色",

    # — preview —
    "preview.placeholder": "# 先在左侧选择或新建注释单元",
    "preview.generate_failed": "# 生成失败：{}",
    "preview.unknown_type": "# 无法为类型 {!r} 生成参数表单：引擎未注册该类型",

    # — inspector —
    "inspector.no_unit": "未选择注释单元",
    "inspector.empty_title": "还没有选择单元",
    "inspector.empty_body": "从左侧选择一个注释单元，或用向导新建一个开始",
    "inspector.empty_cta": "用向导新建",
    "inspector.extra_params": "— 其他参数（learner 发现）—",
    "inspector.search": "搜索参数…",
    "inspector.reset_all": "重置为默认",
    "inspector.more": "更多",
    "inspector.expand_all": "展开全部",
    "inspector.collapse_all": "折叠全部",
    "inspector.copy_params": "复制全部参数",
    "inspector.compact": "紧凑密度",
    "inspector.compact_tip": "将标签与参数键合并、折叠字段说明，宽屏时两列并排",
    "inspector.collapse_panel": "收起检查器",
    "inspector.expand_panel": "展开检查器",
    "inspector.field_required": "必填：{} 为空",
    "inspector.field_number": "格式错误：{} 必须是数字（当前：{}）",
    "inspector.field_range": "超出范围：{} 必须为 {}",
    "inspector.field_color": "格式错误：{} 必须是 #RRGGBB 颜色值",
    "inspector.field_color_list": "格式错误：{} 含非法颜色值（每个须为 #RRGGBB）：{}",
    "inspector.list_add": "添加一项",
    "inspector.list_remove": "移除该项",
    "inspector.field_default": "默认",
    "inspector.field_default_tip": "将 {} 还原为默认值",
    "inspector.generate": "生成模板",
    "inspector.param_count": "{} 个参数",
    "inspector.banner_ok": "参数校验通过",
    "inspector.banner_fields": "{} 个参数需要修正",
    "inspector.banner_unchecked": "未设置参考树，未做 ID 校验",
    "inspector.banner_unmatched": "{} 行 ID 未在树中找到，生成后将被 iTOL 忽略",
    "inspector.group.basic": "基本信息",
    "inspector.group.mapping": "数据映射",
    "inspector.group.appearance": "外观",
    "inspector.group.legend": "图例",
    "inspector.unit.px": "像素",
    "inspector.unit.deg": "度",
    "inspector.unit.percent": "%",
    "inspector.unit.factor": "倍率",

    # — command palette (⌘K) —
    "cmd.title": "命令面板",
    "cmd.open": "命令面板 ⌘K",
    "cmd.placeholder": "搜索注释单元、模板类型或命令…",
    "cmd.kind_unit": "注释单元",
    "cmd.kind_type": "模板类型",
    "cmd.kind_command": "命令",

    # — table editor —
    "table.paste": "粘贴剪贴板数据",
    "table.paste_tsv": "粘贴 TSV",
    "table.paste_hint": "粘贴 Excel / TSV 数据（⌘V），整表替换",
    "table.add_row": "添加行",
    "table.col_status": "状态",
    "table.status_matched": "已匹配",
    "table.status_missing": "树中无此 ID",
    "table.status_unchecked": "未校验",
    "table.footer_count": "{} 行 · {} 通过 · {} 待处理",
    "table.paste_col_mismatch": "期望 {} 列，收到 {} 列",
    "table.paste_empty": "剪贴板没有可粘贴的表格数据",
    "table.readonly_notice": "只读预览：{} 行 × {} 列超出编辑上限（{} 行 / {} 列）",
    "table.empty_title": "还没有数据",
    "table.empty_body": "粘贴 Excel/TSV 数据，或用向导新建注释单元",
    "table.empty_cta": "用向导新建",
    "table.preview_expand": "展开预览",
    "table.preview_collapse": "收起预览",

    # — wizard —
    "wizard.title": "模板向导",
    "wizard.type_search_hint": "搜索类型名称，例如 heatmap、color strip…",
    "wizard.group_basic": "基础注释",
    "wizard.group_basic_desc": "日常分类与单值标记",
    "wizard.group_matrix": "矩阵与热图",
    "wizard.group_matrix_desc": "多列数值、按色阶或形状编码",
    "wizard.group_structure": "结构与连接",
    "wizard.group_structure_desc": "枝上区间、连接关系、外部注释",
    "wizard.group_other": "其他",
    "wizard.group_other_desc": "树操作、扩展与元数据",
    "wizard.step1_label": "选择类型",
    "wizard.step2_label": "导入数据",
    "wizard.step2_sub": "粘贴或导入表格",
    "wizard.step3_label": "配置参数",
    "wizard.step3_sub": "外观、映射与图例",
    "wizard.step4_label": "预览导出",
    "wizard.step4_sub": "核对文本并保存文件",
    "wizard.params_hint": "改一个字段，左边表格里的值会跟着变",
    "wizard.params_summary_title": "这一步只调样式",
    "wizard.params_summary_body": "数据列与映射已在第 2 步设定；这一步改色宽图例等外观。iTOL 的最终渲染效果以 iTOL 端为准。",
    "wizard.column_info": "列结构：{}",
    "wizard.column_info_none": "列结构：—",
    "wizard.separator": "分隔符：",
    "wizard.import_csv": "导入 CSV/TSV…",
    "wizard.paste_sample": "粘贴示例",
    "wizard.back": "上一步",
    "wizard.next": "下一步",
    "wizard.export": "导出模板…",
    "wizard.hint_select": "请先在列表中选择一个模板类型，再点击“下一步”。",
    "wizard.export_title": "导出模板",
    # — shared dialog strings —
    "dialog.close": "关闭",
    "wizard.export_failed": "导出失败",
    "wizard.export_failed_msg": "模板未能写出：\n{}",
    "wizard.read_failed": "读取失败：{}",
    "wizard.bad_columns": "列结构与所选类型不符，无法生成模板：请返回第 2 步核对列数。",
    "wizard.bad_path": "导出被拒绝：目标路径包含 .. 穿越段。",
    "wizard.sep_conflict": "# 数据中存在与分隔符 {!r} 冲突的单元格：\n# iTOL 模板不支持引号转义，请清理数据或更换分隔符后重试",
    "wizard.sep_tooltip": "iTOL 官方规则：SEPARATOR 行恒写作 “SEPARATOR 名称”（单个空格）；此处选择数据列使用的分隔符",
    "wizard.dynamic_hint": "等 动态列 {} 由粘贴数据自动扩展",

    # — file dialogs —
    "fd.open_project": "打开工程",
    "fd.save_project": "保存工程",
    "fd.import_template": "导入 iTOL 模板（learner 反推）",
    "fd.export_template": "导出当前模板",
    "fd.select_tree": "选择树文件",
    "fd.import_data": "导入数据",
    "fd.select_dir": "选择目录",
    "fd.select_file": "选择文件",
    "fd.select_key": "选择 API 密钥文件",
    "fd.export_config": "导出配置",
    "fd.select_templates": "选择 iTOL 模板文件",
    "fd.select_output_dir": "选择导出目录",
    "fd.filter_project": "PyiTOL 工程 (*.pyitolproj)",
    "fd.filter_template": "iTOL 模板 (*.txt);;所有文件 (*)",
    "fd.filter_tree": "树文件 (*.nwk *.newick *.tre *.tree *.txt)",
    "fd.filter_table": "表格文件 (*.csv *.tsv *.txt)",
    "fd.filter_yaml": "YAML (*.yaml *.yml)",

    # — config dialog —
    "config.title": "pyitol 配置文件生成器",
    "config.export_yaml": "导出 YAML…",
    "config.done": "完成",
    "config.done_msg": "配置已导出：\n{}",
    "config.rejected": "导出被拒绝：目标路径包含 .. 穿越段",
    "config.write_failed": "写入失败：{}",

    # — upload dialog —
    "upload.title": "上传 iTOL 并导出",
    "upload.tree_label": "树文件（Newick）",
    "upload.key_label": "API 密钥文件",
    "upload.key_placeholder": "留空则使用环境变量 ITOL_API_KEY；不在此输入 Key 明文",
    "upload.format_label": "导出格式",
    "upload.output_label": "导出目录",
    "upload.force": "覆盖 iTOL 上同名工程（force）",
    "upload.templates_label": "模板文件（与树一起批量上传）：",
    "upload.add_template": "添加模板…",
    "upload.remove": "移除所选",
    "upload.status_pending": "待上传",
    "upload.run": "上传并导出",
    "upload.running": "正在上传…（引擎重试逻辑已启用）",
    "upload.failed": "失败：{}",
    "upload.success": "成功：tree_id = {}；导出：{}",
    "upload.no_files": "（无输出文件）",
    "upload.no_tree": "缺少树文件",
    "upload.no_tree_msg": "请先选择有效的 Newick 树文件",
    "upload.bad_output": "导出目录无效",
    "upload.bad_output_msg": "请选择一个不包含 .. 的导出目录",

    # — color picker —
    "color.pick": "选择颜色",

    # — language menu —
    "lang.zh": "中文",
    "lang.en": "English",
}

_EN: dict[str, str] = {
    # — app / window —
    "app.title": "PyiTOL Studio",
    "app.subtitle": "Desktop companion for iTOL annotation",
    "app.status_ready": "Ready (engine: pyitol)",
    "app.status_new_project": "New project created",
    "app.status_opened": "Opened: {}",
    "app.status_open_failed": "Open failed: {}",
    "app.status_saved": "Saved: {}",
    "app.status_save_failed": "Save failed: {}",
    "app.status_wizard_done": "Wizard complete: template exported",
    "app.status_imported": "Imported {} annotation unit(s) — type/parameters/data back-filled",
    "app.status_import_failed": "Reverse mapping failed: {}",
    "app.status_no_unit": "No unit selected — pick one in the navigator first",
    "app.status_exported": "Exported: {}",
    "app.status_export_failed": "Export failed: {}",
    "app.status_tree_set": "Tree: {} · {} leaf IDs · verified",
    "app.status_tree_set_no_ids": "Tree: {} · no leaf IDs read, validation skipped",
    "app.status_tree_failed": "Tree parse failed: {}",
    "app.status_drop_rejected": "Unsupported file type (only .pyitolproj / .txt / Newick trees): {}",
    "app.status_upload_exporting": "Exporting annotation units to template files…",
    "app.status_upload_ready": "Ready: {} template(s) to upload",
    "app.status_upload_export_failed": "Template export failed — uploading tree only: {}",
    "app.status_deleted": "Annotation unit deleted",
    "app.status_generated": "Template preview regenerated from the current parameters",
    "app.status_unknown_type": "Unknown template type: {} (preview and form unavailable)",
    "app.unsaved_title": "Unsaved changes",
    "app.unsaved_msg": "The current project has unsaved changes. What would you like to do?",
    "app.unsaved_save": "Save and continue",
    "app.unsaved_discard": "Discard changes",
    "app.unsaved_cancel": "Cancel",
    "app.status_bad_path": "Invalid path: target contains a .. segment — refused",
    "app.status_wizard_added": "Wizard generated and added to the project: {}",

    # — welcome page —
    "welcome.new_project": "New Project",
    "welcome.new_project_desc": "Import a Newick tree and data table, build a template from scratch",
    "welcome.open_project": "Open Project",
    "welcome.open_project_desc": "Keep editing a .pyitolproj — every annotation unit is restored",
    "welcome.examples": "Template Wizard",
    "welcome.examples_desc": "Build a new annotation template step by step from the 31 official types",
    "welcome.key_new": "⌘N",
    "welcome.key_open": "⌘O",
    "welcome.recent": "Recent Projects",
    "welcome.unit_count": "{} annotation units",
    "welcome.drop_prefix": "Drop a",
    "welcome.drop_tree": "Newick tree",
    "welcome.drop_or": "or an",
    "welcome.drop_template": "iTOL template file",
    "welcome.drop_suffix": "into the window to begin",

    # — navigator —
    "nav.tree": "Tree: {}",
    "nav.tree_none": "Tree: (none selected)",
    "nav.units": "Annotation Units ({})",
    "nav.units_caption": "Annotation units",
    "nav.tree_change": "Change tree file",
    "nav.tree_meta": "{} leaf nodes · Newick",
    "nav.tree_meta_unknown": "Leaf count unknown",
    "nav.tree_match": "{} / {} IDs matched",
    "nav.tree_match_none": "Not checked",
    "nav.tree_loading": "Reading leaf IDs…",
    "nav.search_placeholder": "Search units…",
    "nav.hide_unit": "Hide annotation unit",
    "nav.show_unit": "Show annotation unit",
    "nav.hidden_summary": "{} hidden annotation unit(s) will be skipped on upload",
    "nav.collapse_panel": "Collapse left rail",
    "nav.expand_panel": "Expand left rail",
    "nav.delete": "Delete Annotation Unit",

    # — toolbar —
    "tb.new": "New",
    "tb.open": "Open Project",
    "tb.save": "Save Project",
    "tb.wizard": "Template Wizard",
    "tb.import": "Import Template",
    "tb.preview": "Generate Preview",
    "tb.export": "Export Current Template",
    "tb.upload": "Upload to iTOL",
    "tb.config": "Config File",
    "tb.more": "More actions",
    "tb.language": "Language",
    "tb.theme": "Appearance",
    "tb.toggle_rail": "Show / hide left rail",
    "tb.toggle_inspector": "Show / hide inspector",

    # — appearance menu —
    "theme.system": "Follow system",
    "theme.dark": "Dark",
    "theme.light": "Light",

    # — preview —
    "preview.placeholder": "# Select or create an annotation unit in the navigator first",
    "preview.generate_failed": "# Generation failed: {}",
    "preview.unknown_type": "# Cannot generate form for type {!r}: engine does not register this type",

    # — inspector —
    "inspector.no_unit": "No annotation unit selected",
    "inspector.empty_title": "No unit selected yet",
    "inspector.empty_body": "Pick an annotation unit from the left rail, or create one with the wizard",
    "inspector.empty_cta": "Open wizard",
    "inspector.extra_params": "— Other parameters (discovered by learner) —",
    "inspector.search": "Search parameters…",
    "inspector.reset_all": "Reset to defaults",
    "inspector.more": "More",
    "inspector.expand_all": "Expand all",
    "inspector.collapse_all": "Collapse all",
    "inspector.copy_params": "Copy all parameters",
    "inspector.compact": "Compact density",
    "inspector.compact_tip": "Merge label & key, fold field notes, two columns on wide panels",
    "inspector.collapse_panel": "Collapse inspector",
    "inspector.expand_panel": "Expand inspector",
    "inspector.field_required": "Required: {} is empty",
    "inspector.field_number": "Format: {} must be a number (got {})",
    "inspector.field_range": "Out of range: {} must be {}",
    "inspector.field_color": "Format: {} must be a #RRGGBB colour",
    "inspector.field_color_list": "Format: {} has an invalid colour (each must be #RRGGBB): {}",
    "inspector.list_add": "Add item",
    "inspector.list_remove": "Remove item",
    "inspector.field_default": "Default",
    "inspector.field_default_tip": "Reset {} to its default",
    "inspector.generate": "Generate template",
    "inspector.param_count": "{} parameters",
    "inspector.banner_ok": "Parameters valid",
    "inspector.banner_fields": "{} parameter(s) need fixing",
    "inspector.banner_unchecked": "No reference tree set — ID validation skipped",
    "inspector.banner_unmatched": "{} row ID(s) not found in the tree — iTOL will ignore them",
    "inspector.group.basic": "Basic",
    "inspector.group.mapping": "Data mapping",
    "inspector.group.appearance": "Appearance",
    "inspector.group.legend": "Legend",
    "inspector.unit.px": "px",
    "inspector.unit.deg": "deg",
    "inspector.unit.percent": "%",
    "inspector.unit.factor": "×",

    # — command palette (⌘K) —
    "cmd.title": "Command palette",
    "cmd.open": "Command palette ⌘K",
    "cmd.placeholder": "Search units, template types or commands…",
    "cmd.kind_unit": "Unit",
    "cmd.kind_type": "Type",
    "cmd.kind_command": "Command",

    # — table editor —
    "table.paste": "Paste clipboard data",
    "table.paste_tsv": "Paste TSV",
    "table.paste_hint": "Paste Excel/TSV data (⌘V) — replaces the whole table",
    "table.add_row": "Add row",
    "table.col_status": "Status",
    "table.status_matched": "Matched",
    "table.status_missing": "Not in tree",
    "table.status_unchecked": "Unchecked",
    "table.footer_count": "{} rows · {} matched · {} pending",
    "table.paste_col_mismatch": "Expected {} columns, received {}",
    "table.paste_empty": "No tabular data on the clipboard",
    "table.readonly_notice": "Read-only: {} × {} exceeds the edit envelope ({} rows / {} cols)",
    "table.empty_title": "No data yet",
    "table.empty_body": "Paste Excel/TSV data, or create an annotation unit with the wizard",
    "table.empty_cta": "Open wizard",
    "table.preview_expand": "Expand preview",
    "table.preview_collapse": "Collapse preview",

    # — wizard —
    "wizard.title": "Template Wizard",
    "wizard.column_info": "Columns: {}",
    "wizard.column_info_none": "Columns: —",
    "wizard.separator": "Separator:",
    "wizard.import_csv": "Import CSV/TSV…",
    "wizard.paste_sample": "Paste Sample",
    "wizard.back": "Back",
    "wizard.next": "Next",
    "wizard.export": "Export Template…",
    "wizard.hint_select": "Please select a template type from the list before clicking \"Next\".",
    "wizard.export_title": "Export Template",
    # — shared dialog strings —
    "dialog.close": "Close",
    "wizard.export_failed": "Export Failed",
    "wizard.export_failed_msg": "Could not write template:\n{}",
    "wizard.read_failed": "Read failed: {}",
    "wizard.bad_columns": "The column layout does not match the chosen type — go back to step 2 and fix the columns.",
    "wizard.bad_path": "Export refused: the path contains a .. segment.",
    "wizard.sep_conflict": "# Data contains a cell conflicting with separator {!r}:\n# iTOL templates do not support quote-escaping — clean the data or switch separator",
    "wizard.sep_tooltip": "iTOL rule: the SEPARATOR line is always written as \"SEPARATOR NAME\" (single space); this selects the separator used in data columns",
    "wizard.step1_label": "Pick a type",
    "wizard.step2_label": "Import data",
    "wizard.step2_sub": "Paste or import a table",
    "wizard.step3_label": "Configure parameters",
    "wizard.step3_sub": "Appearance, mapping, legend",
    "wizard.step4_label": "Preview and export",
    "wizard.step4_sub": "Verify the text and save",
    "wizard.params_hint": "Change a field — the data table on the left stays in sync",
    "wizard.params_summary_title": "This step is about styling",
    "wizard.params_summary_body": "Columns and data mapping were set in step 2; here you adjust widths, colours and legends. The final render lives on iTOL.",
    "wizard.type_search_hint": "Search types by name, e.g. heatmap, color strip…",
    "wizard.group_basic": "Basic",
    "wizard.group_basic_desc": "Everyday classification and single-value marks",
    "wizard.group_matrix": "Matrix & heatmap",
    "wizard.group_matrix_desc": "Multi-column values encoded by colour ramp or shape",
    "wizard.group_structure": "Structure & connections",
    "wizard.group_structure_desc": "Branch intervals, connections, external annotations",
    "wizard.group_other": "Other",
    "wizard.group_other_desc": "Tree operations, extensions, metadata",
    "wizard.dynamic_hint": "dynamic columns ({}) expand from the pasted data",

    # — file dialogs —
    "fd.open_project": "Open Project",
    "fd.save_project": "Save Project",
    "fd.import_template": "Import iTOL template (learner reverse mapping)",
    "fd.export_template": "Export Current Template",
    "fd.select_tree": "Select tree file",
    "fd.import_data": "Import data",
    "fd.select_dir": "Select directory",
    "fd.select_file": "Select file",
    "fd.select_key": "Select API key file",
    "fd.export_config": "Export config",
    "fd.select_templates": "Select iTOL template files",
    "fd.select_output_dir": "Select output directory",
    "fd.filter_project": "PyiTOL project (*.pyitolproj)",
    "fd.filter_template": "iTOL template (*.txt);;All files (*)",
    "fd.filter_tree": "Tree files (*.nwk *.newick *.tre *.tree *.txt)",
    "fd.filter_table": "Table files (*.csv *.tsv *.txt)",
    "fd.filter_yaml": "YAML (*.yaml *.yml)",

    # — config dialog —
    "config.title": "pyitol Configuration Generator",
    "config.export_yaml": "Export YAML…",
    "config.done": "Done",
    "config.done_msg": "Config exported:\n{}",
    "config.rejected": "Export rejected: path contains .. traversal",
    "config.write_failed": "Write failed: {}",

    # — upload dialog —
    "upload.title": "Upload to iTOL & Export",
    "upload.tree_label": "Tree file (Newick)",
    "upload.key_label": "API key file",
    "upload.key_placeholder": "Leave empty to use ITOL_API_KEY env var; key is never entered here",
    "upload.format_label": "Export format",
    "upload.output_label": "Output directory",
    "upload.force": "Overwrite project with same name on iTOL (force)",
    "upload.templates_label": "Template files (batch-uploaded with the tree):",
    "upload.add_template": "Add template…",
    "upload.remove": "Remove selected",
    "upload.status_pending": "Pending upload",
    "upload.run": "Upload & Export",
    "upload.running": "Uploading… (engine retry logic enabled)",
    "upload.failed": "Failed: {}",
    "upload.success": "Success: tree_id = {}; files: {}",
    "upload.no_files": "(no output files)",
    "upload.no_tree": "Missing tree file",
    "upload.no_tree_msg": "Please select a valid Newick tree file first",
    "upload.bad_output": "Invalid output directory",
    "upload.bad_output_msg": "Please choose an output directory without .. segments",

    # — color picker —
    "color.pick": "Select color",

    # — language menu —
    "lang.zh": "中文",
    "lang.en": "English",
}

_TABLES: dict[str, dict[str, str]] = {"zh": _ZH, "en": _EN}

# Fallback to Chinese for unknown locales.
_DEFAULT_LOCALE = "zh"
_SETTINGS_KEY = "ui/language"


class Translator:
    """Singleton translator; ``tr(key, *args)`` returns the active-locale
    string with positional ``str.format`` substitution."""

    def __init__(self) -> None:
        self._locale: str = _DEFAULT_LOCALE
        # Weak references: a locale listener is usually a bound method of a
        # window; holding it strongly would keep the (possibly destroyed) widget
        # alive and fire into a dead C++ object (code review P2-10).
        self._listeners: list = []

    @property
    def locale(self) -> str:
        return self._locale

    def set_locale(self, locale: str) -> None:
        if locale in _TABLES and locale != self._locale:
            self._locale = locale
            QSettings().setValue(_SETTINGS_KEY, locale)
            self._fire_listeners()

    def _fire_listeners(self) -> None:
        """Call every still-alive listener; drop the dead ones as we go."""
        alive = []
        for ref in self._listeners:
            callback = ref()
            if callback is None:
                continue  # the listener object was garbage-collected
            alive.append(ref)
            callback()
        self._listeners = alive

    def load_saved(self) -> None:
        saved = QSettings().value(_SETTINGS_KEY, "", type=str)
        if saved and saved in _TABLES:
            self._locale = saved

    def add_listener(self, cb) -> None:
        """Register a callback fired when the locale changes (no-arg callable).

        Stored weakly: bound methods via ``WeakMethod`` so a destroyed window is
        not kept alive, everything else via ``ref``.  Pair with
        :meth:`remove_listener` on window close (code review P2-10).
        """
        if hasattr(cb, "__self__") and hasattr(cb, "__func__"):
            self._listeners.append(weakref.WeakMethod(cb))
        else:
            self._listeners.append(weakref.ref(cb))

    def remove_listener(self, cb) -> None:
        """Unregister a previously added listener (bound methods compare equal)."""
        self._listeners = [
            ref for ref in self._listeners if ref() is not None and ref() != cb
        ]

    def tr(self, key: str, *args) -> str:
        table = _TABLES.get(self._locale, _ZH)
        text = table.get(key, _ZH.get(key, key))
        if args:
            try:
                text = text.format(*args)
            except (IndexError, KeyError):
                pass
        return text


# Module-level singleton — imported everywhere as ``from ..i18n import tr``.
_translator = Translator()


def tr(key: str, *args) -> str:
    return _translator.tr(key, *args)


def translator() -> Translator:
    return _translator
