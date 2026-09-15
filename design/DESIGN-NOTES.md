# 视觉稿定稿记录

## v1.0（旧版基线）

- 源文件：`PyiTOL-Studio-视觉稿.html`（主工作台 + 欢迎页两视图，含深色模式切换）。
- 流程：HTML 中视觉迭代 → 确认锁定 → 逐块翻译为 Qt Widgets（开发方案 §5.7）。
- 已转换的令牌（`src/pyitolstudio/theme/__init__.py`）：
  - 间距体系：4 / 8 / 12 / 16 / 24 px（SPACE_XS…SPACE_XL）；
  - 强调色：浅色 `#1f8a5d`，深色 `#3ecf8e`；
  - 圆角：4 / 6 / 10 px；字体：系统 SF Pro / PingFang SC，13px 正文。
- 验收：Qt 实现与本视觉稿并排比对（浅色/深色两模式），作为真机验收的视觉基准。

## v2.0（已定稿，已落地）

- 源文件：`PyiTOL-Studio-设计方案-v2.md` + `PyiTOL-Studio-界面原型-v2.html`（**不在仓库内**；令牌已落地代码，v2 设计意图以 `src/pyitolstudio/theme/__init__.py` 为事实来源，并辅以 `PyiTOL-Studio-UI设计评审.md` 作为可访问性结论与候选值的权威记录）。
- 主题代号 *Instrument Dark*，深色为默认模式，浅色为一等模式（不再是降级）。
- 5 级表面层级（`canvas / bg / panel / panel_alt / hover / active`）+ 3 级描边（`line / line2 / line3`）+ 4 级文字 + 品牌色双值（深 `#35e0a1`、浅 `#0e9c68`）+ 语义色三件套（`info / warn / danger`，含 `*_soft`）+ 8 色数据可视化（`dv1…dv8`）。
- 间距扩为 2/4/8/12/16/20/24/32；圆角 4/6/8/12/16。
- 布局重构：左栏（树卡片 + 注释单元列表，可拖拽排序）、中栏（数据网格 + 预览，IDL 驱动的列与状态芯片）、右栏（搜索 + 分组折叠 + 字段级默认还原 + 吸底生成按钮）。标题栏中部为 `⌘K` 命令面板。
- 7 项落地（T1–T7）见 CHANGELOG 0.3.0；视觉验收通过离屏 `QWidget.grab()` 截图与设计原型并排比对（`tools/screenshots.py`、`tools/inspector_screenshot.py`）。
- 已知偏差（0.3.1 后状态）：
  - ~~①浅色下 `accent`/`warn`/`on_accent` 作正文低于 4.5:1~~ → **0.3.1 已闭合**（`text_tertiary`/`warn`/`on_accent`/`accent_link` 均按评审第八节候选值实测达标）；
  - ~~②表头标签在 QSS 下居中而非左对齐~~ → **0.3.1 已闭合**（数据网格 `horizontalHeader().setDefaultAlignment(AlignLeft|AlignVCenter)`，见 `app/table_editor.py`）；
  - ③显隐状态未持久化（受「`.pyitolproj` schema 不要改」约束）——**未修**，UI-only 状态，属既有约束。
- 0.3.1 评审 P1/P2 追加落地（与 0.3.1 同一发布，见 CHANGELOG）：
  - 三栏折叠：rail / inspector 各自 `QToolButton` 折叠入口 + 工具栏 `panel-left/right` 复选切换，中心栏可回收宽度（`app/main_window.py`、`app/unit_list.py`、`app/inspector.py`）。
  - 工具栏主次：仅「新建」为主操作，QSS `QToolButton#primaryTool` 以 `accent_lo` 填充，其余按钮保持中性（`theme/__init__.py`）。
  - Inspector 密度开关：紧凑密度把 label+key 合并一行、note 折叠进 tooltip、宽屏两列并排，偏好存 `QSettings`（`app/inspector.py`）。
  - 参数级字段校验：必填/数值范围/颜色格式就地报错（label 转 danger），footer 横幅聚合「N 个参数需要修正」并优先于树匹配提示（`app/inspector.py`、`app/main_window.py`）。
  - 微交互：分组折叠 140ms `OutCubic` 高度动画、欢迎页动作卡 hover 3px 抬升、⌘K 140ms 淡入（`app/inspector.py`、`app/welcome.py`、`app/command_palette.py`）。

## v2.1（0.5.0 界面评审修订）

- 起因：0.4.0 交付版做了一轮界面评审（离屏渲染 + 像素采样 + 控件自省），报告在
  `../../UI评审-2026-09-13/index.html`。**令牌体系本身合格，未推翻**；改动集中在落地层。
- **令牌新增**：`CONTROL_HEIGHT`(28) / `CONTROL_HEIGHT_COMPACT`(24) / `ICON_BUTTON`(24) /
  `TOOLBAR_BUTTON`(32) / `TOOLBAR_ICON`(18) / `FONT_WEIGHT_STRONG`(500)。
- **`FONT_WEIGHT_BOLD` 的适用范围收窄到 ≥16px**：11–13px 中文用合成粗体（PingFang SC 在该
  字号无 bold 母版）会糊成一团；层级改用字号与文字三级色（`text`/`text_dim`/`text_tertiary`）承担。
- **新增 `theme_mode.build_palette(dark)`**：QSS 与 QPalette 是两条独立通路，只设样式表时
  深色窗口会漏出系统浅色（实测 `palette.Window = #efefef`）。凡漏白处（自绘控件的未绘制区、
  未覆盖的滚动区 viewport）由此一并闭合。
- **已闭合的偏差**（0.4.0 及以前遗留）：
  - 表头右侧 428×32 px `#efefef` 白块（`GridHeader.paintSection` 只填 section）；
  - 输入控件常年顶着聚焦态（`A, B, C:focus` 只对 C 生效）；
  - 全部 31 张向导卡片图标压在品牌绿上（祖先伪态后代选择器在 Qt 中不可达）；
  - 色值以自身色作前景（浅色下 `#ffff00` 对比度 1.07:1）→ 改为 chip；
  - 表格列宽固定导致 61% 死区 → 数据列均分可用宽度。
- 验收：`tests/test_theme.py` 固化两条选择器纪律；`pytest` 125 passed / 1 skipped。
- 剩余已知事项：`UI评审-2026-09-13/index.html` §04 中"命令面板信息重复"一条经复核不成立
  （右侧第二段是该条目所属分组/类型，非重复信息），未改动。
