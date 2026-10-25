# Changelog

All notable changes to PyiTOL Studio are documented here.  
本文件记录 PyiTOL Studio 的所有重要变更。

The `pyitol` engine is an external dependency distributed with the [PyiTOL](https://github.com/ZengZichao/PyiTOL) repository and is never modified by this project.  
`pyitol` 引擎是外部依赖，随 [PyiTOL](https://github.com/ZengZichao/PyiTOL) 仓库分发，本项目不对引擎代码做任何修改。

## [0.2.0] - 2026-10-26

Visual redesign and first-run improvements.  
视觉重设计与首次使用体验改进。

### Changed

- Black & white minimal identity: new squircle app icon (white tile, near-black phylogeny) and a monochrome welcome mark; the green brand tile is gone.  
  黑白简约视觉：全新圆角方形应用图标（白色底、黑色系统发生树）与单色欢迎页标志，移除绿色品牌底色。
- Palette re-anchored on black/white/grey with a Klein-blue accent (`#002fa7` light / `#2e5cff` dark); success states follow the brand hue instead of green.  
  配色以黑白灰为基底，点缀克莱因蓝（浅色 `#002fa7` / 深色 `#2e5cff`）；成功状态改用品牌色而非绿色。
- English is now the default UI language; a saved language preference still wins.  
  界面默认语言改为英文；已保存的语言偏好仍然优先。
- The parameter catalog is bilingual — field labels, help texts, data-grid column headers and enum choices translate with the locale, live.  
  参数目录双语化——字段标签、帮助文本、表格列头与枚举选项随语言实时切换。
- Every toolbar action holds a permanent slot: preview, upload, config, pane toggles, language and appearance are no longer folded into an overflow menu.  
  工具栏按钮全部常驻：生成预览、上传、配置、面板开关、语言与外观不再收进溢出菜单。

### Added

- Bundled example project (8-species tree + colour strip + heatmap) with a one-click entry on the welcome page; packaged inside the app.  
  内置示例工程（8 物种树 + 色带 + 热图），欢迎页一键打开，并随应用打包分发。

### Fixed

- Welcome action cards no longer overlap when the window is narrow; card titles and the drop-zone hint wrap instead of clipping.  
  缩小窗口时欢迎页三张卡片不再相互重叠；卡片标题与拖放提示改为自动换行，不再截断。

## [0.1.0] - 2026-09-15

Initial public release of PyiTOL Studio.  
PyiTOL Studio 的初始公开发布版本。

### Added

- macOS desktop GUI workbench for iTOL annotation templates.  
  用于 iTOL 注释模板的 macOS 桌面 GUI 工作台。
- Visual template wizard covering all 31 iTOL v7 annotation types.  
  覆盖 iTOL v7 全部 31 种注释类型的可视化模板向导。
- Workbench with three-pane layout: unit navigator, data grid + preview, and parameter inspector.  
  三栏主工作台：注释单元导航、数据表格+预览、参数检查器。
- Learner back-fill: restore parameter forms from existing iTOL template files.  
  Learner 反推：从已有 iTOL 模板文件还原参数表单。
- Batch upload to iTOL with background export of project annotation units.  
  后台导出工程注释单元并批量上传至 iTOL。
- Config generator aligned with the engine’s `config.example.yaml`.  
  与引擎 `config.example.yaml` 字段对齐的配置生成器。
- Bilingual Chinese / English UI with live language switching.  
  中英文双语界面，支持实时语言切换。
- Light and dark themes based on the *Instrument Dark* token system.  
  基于 *Instrument Dark* 令牌系统的浅色/深色主题。
- Citation information for the underlying PyiTOL engine.  
  补充底层 PyiTOL 引擎的引用信息。
