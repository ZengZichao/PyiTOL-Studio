# 贡献指南 / Contributing to PyiTOL Studio

感谢你对 PyiTOL Studio 的兴趣！本文说明如何搭建开发环境、运行测试与提交变更。

Thank you for your interest in PyiTOL Studio! This guide covers setting up a
development environment, running the tests, and submitting changes.

## 项目结构 / Project layout

```
src/pyitolstudio/
  adapter/     # 与 pyitol 引擎对话的唯一层（Qt-free，可无 GUI 测试）
  app/         # PySide6 界面（main_window / wizard / inspector / table_editor …）
  project/     # .pyitolproj 文档模型与原子读写
  theme/       # 视觉令牌 → QSS + QPalette
  i18n.py icons.py tables.py paths.py  # 文案 / 图标 / 纯函数
tests/         # pytest + pytest-qt 套件
fixtures/      # iTOL 官方示例（learner/generator 往返回归用）
packaging/     # PyInstaller spec 与打包/签名说明
```

界面层（`app/`）**不得直接 import `pyitol`**；一切引擎调用都经 `adapter/`。
这条分层纪律有测试锁定，请勿绕过。

## 开发环境 / Development environment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

GUI 测试需要 PySide6 与引擎 `pyitol`。引擎目前以源码形式随 PyiTOL 仓库分发：
把引擎的 `src` 目录加入 `PYTHONPATH`（或安装为可编辑包）后再跑测试。

The engine `pyitol` is distributed as part of the PyiTOL repository. Add the
engine's `src/` to `PYTHONPATH` (or install it editable) before running tests.

## 运行测试 / Running the tests

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH="<path-to>/PyiTOL/PyiTOL-项目代码/src" \
  python -m pytest
```

- 提交前请确保 `pytest` 全绿。
- Before a commit, make sure `pytest` passes.

## 提交变更 / Submitting changes

1. 新建一个从 `main` 切出的功能分支：`git checkout -b feat/<short-name>`。
2. 每个 PR 聚焦一件事；关联对应 issue。
3. 若改动了界面或文案，请附截图，并确保 `tests/test_theme.py`、
   `tests/test_review_fixes.py` 中的可访问性/对比度/i18n 门槛仍然通过。
4. 遵循现有代码风格（类型注解、docstring 用中文业务语、标识符用英文）。

## 报告问题 / Reporting issues

请通过 GitHub Issues 提交，尽量附上：复现步骤、`.pyitolproj`/模板样例（去除敏感数据）、
操作系统与语言环境、应用与引擎版本。请勿在公开 issue 中粘贴 iTOL API Key。

See [SECURITY.md](SECURITY.md) for reporting security issues privately.
