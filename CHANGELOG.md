# Changelog

All notable changes to PyiTOL Studio are documented here.  
本文件记录 PyiTOL Studio 的所有重要变更。

The `pyitol` engine is an external dependency distributed with the [PyiTOL](https://github.com/ZengZichao/PyiTOL) repository and is never modified by this project.  
`pyitol` 引擎是外部依赖，随 [PyiTOL](https://github.com/ZengZichao/PyiTOL) 仓库分发，本项目不对引擎代码做任何修改。

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
