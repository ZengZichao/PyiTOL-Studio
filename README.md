# PyiTOL Studio / iTOL 注释桌面工作台

**PyiTOL Studio** 是 [PyiTOL](https://github.com/ZengZichao/PyiTOL) 的桌面伴侣：一个基于 PySide6 的 macOS GUI，用于可视化生成、编辑、反推和批量上传 iTOL 注释模板。

> **PyiTOL Studio** is the desktop companion of [PyiTOL](https://github.com/ZengZichao/PyiTOL): a PySide6-based macOS GUI for visually creating, editing, learning from, and batch-uploading iTOL annotation templates.

- 用户手册 / User Guide: [docs/用户手册.md](docs/用户手册.md) · [docs/UserGuide.md](docs/UserGuide.md)
- 更新日志 / Changelog: [CHANGELOG.md](CHANGELOG.md)
- 许可证 / License: [MIT](LICENSE)

---

## 功能 / Features

- **模板向导 / Template Wizard**：类型 → 数据 → 参数 → 预览 → 导出，覆盖 iTOL v7 的 31 种注释类型。  
  *Type → data → parameters → preview → export, covering all 31 iTOL v7 annotation types.*
- **主工作台 / Workbench**：三栏布局（导航、表格+预览、参数检查器），支持 Excel/TSV 粘贴与参考树叶 ID 校验。  
  *Three-pane layout (navigator, table+preview, parameter inspector), with Excel/TSV paste and reference-tree leaf-ID validation.*
- **Learner 反推 / Learner back-fill**：从已有模板一键还原表单，生成后再反推保持一致。  
  *One-click back-fill of the parameter form from an existing template, with generate→learn round-trip consistency.*
- **批量上传 / Batch upload**：工程内注释单元自动导出为模板文件后随树批量上传 iTOL。  
  *Export project annotation units as template files and upload them to iTOL together with the tree.*
- **配置生成器 / Config generator**：与引擎 `config.example.yaml` 字段一一对应的 YAML 配置编辑。  
  *YAML config editor aligned field-by-field with the engine’s `config.example.yaml`.*
- **中英文界面 / Bilingual UI**：工具栏地球图标可实时切换中文 / English。  
  *Live Chinese / English switching via the globe icon in the toolbar.*

---

## 快速开始 / Quick Start

### 源码运行 / Run from source

```bash
# 1. 安装依赖（示例使用 Python 3.11）
#    Install dependencies (example with Python 3.11)
pip install "PySide6>=6.5" "pandas>=2.0" PyYAML pytest pytest-qt

# 2. 安装 pyitol 引擎（在 PyiTOL 仓库中分发）
#    Install the pyitol engine (distributed in the PyiTOL repository)
pip install /path/to/PyiTOL/PyiTOL-项目代码

# 3. 以可编辑模式安装本仓库
#    Install this repository in editable mode
pip install -e .

# 4. 启动
#    Launch
pyitol-studio
```

### 打包为 macOS 应用 / Build the macOS app

```bash
pyinstaller packaging/pyitolstudio.spec
open "dist/PyiTOL Studio.app"
```

> 正式发布前请阅读 [packaging/README.md](packaging/README.md) 进行 Developer ID 签名与公证。  
> *Read [packaging/README.md](packaging/README.md) for Developer ID signing and notarization before public release.*

### 测试 / Tests

```bash
pytest
```

Qt 界面冒烟测试可在无显示器环境运行：  
*Qt smoke tests can run headless with:*

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_app_qt.py
```

---

## 架构要点 / Architecture Highlights

- **分层 / Layering**：GUI 层只依赖适配层，适配层只调用 `pyitol` 公开 API；GUI 层不直接 `import pyitol`。  
  *The GUI layer only depends on the adapter layer; the adapter layer only calls the public `pyitol` API.*
- **声明式表单 / Declarative forms**：`adapter/form_idl.py` 从引擎注册表生成表单 IDL，新增模板类型无需改动 GUI 代码。  
  *Forms are generated from an IDL produced by introspecting the engine registry, so new template types need zero GUI code.*
- **线程安全 / Thread safety**：所有引擎调用都通过 `adapter/tasks.py` 中的 `EngineTask(QThread)` 异步执行。  
  *All engine calls run asynchronously through `EngineTask(QThread)` in `adapter/tasks.py`.*
- **设计系统 / Design system**：`theme/` 是 *Instrument Dark* 视觉令牌的唯一来源，深浅双模、无 widget 内硬编码颜色。  
  *`theme/` is the single source of truth for the *Instrument Dark* token system, with both dark and light modes and no hard-coded widget colours.*

---

## 引用 / Citation

如果在研究或教学中使用了 PyiTOL Studio，请同时引用其底层引擎 PyiTOL：

> 若使用本软件，请引用：  
> **PyiTOL: reproducible Python workflows for iTOL annotation and taxonomic monophyly assessment**  
> GitHub: https://github.com/ZengZichao/PyiTOL  
> DOI: https://doi.org/10.64898/2026.08.27.747471

If you use PyiTOL Studio in your research or teaching, please also cite the underlying PyiTOL engine:

> Please cite:  
> **PyiTOL: reproducible Python workflows for iTOL annotation and taxonomic monophyly assessment**  
> GitHub: https://github.com/ZengZichao/PyiTOL  
> DOI: https://doi.org/10.64898/2026.08.27.747471

仓库根目录也提供了 [`CITATION.cff`](CITATION.cff) 供 GitHub 自动生成引用格式。  
*A [`CITATION.cff`](CITATION.cff) file is included at the repository root for GitHub’s automatic citation format.*

---

## 安全提示 / Security Notes

- iTOL API Key 仅通过环境变量 `ITOL_API_KEY` 或密钥文件读取；界面不存储明文 API Key。  
  *The iTOL API key is read only from the `ITOL_API_KEY` environment variable or a key file; the UI does not store plain-text keys.*
- 文件路径在写入前统一规范化，并在规范化之前拒绝 `..` 穿越段。  
  *File paths are normalized before writes, and `..` traversal segments are rejected before normalization.*

---

## 状态 / Status

当前版本 / Current version: **0.1.0**（初始公开发布 / initial public release）。
