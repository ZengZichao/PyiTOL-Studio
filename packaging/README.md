# 打包与分发（M3）

PyiTOL Studio 使用 PyInstaller 打包为独立 macOS `.app`（内含 Python、PySide6
与 pyitol 引擎，无需用户配置环境）。

## 1. 构建

```bash
# 干净环境建议：python=3.11/3.12 + pip install -e . + pyinstaller
pyinstaller packaging/pyitolstudio.spec --noconfirm
# 产物：dist/PyiTOL Studio.app（arm64，ad-hoc 签名，含应用图标）
```

spec 要点（`packaging/pyitolstudio.spec`）：

- 入口为 `src/pyitolstudio/__main__.py`（内部必须是**绝对导入**——PyInstaller
  以顶层脚本执行入口，相对导入会在启动瞬间崩溃）；
- `hiddenimports` 覆盖引擎的 schemas/presets 子模块与 scipy/dendropy，
  以及 `PySide6.QtSvg`/`PySide6.QtSvgWidgets`（SVG 图标渲染所需）；
- 参数目录 `param_ranges.json` 以 `pyitolstudio/resources/` 布入包内，
  SVG 图标以 `pyitolstudio/resources/icons/` 布入包内，
  运行期经 `resource_path` 的 `sys._MEIPASS` 回退读取；
- `EXE → COLLECT → BUNDLE` 三段：**没有 BUNDLE 步骤就没有 .app**（`app_bundle`
  之类的 EXE 关键字并不存在，传了也会被静默忽略）。
- `excludes` 剔除引擎与 Studio 均不使用的重型库（matplotlib/IPython/sphinx/
  mypy/black/numba/pytest 等），否则共享开发环境里的 hook 会把它们捎带进包
  （实测 504 MB → 274 MB）。

## 2. 验证

```bash
# 逐层自检（不开窗）：引擎注册表 → 表单 IDL → 参数目录 → 模板生成 → learner 往返
PYITOLSTUDIO_SMOKE=1 "dist/PyiTOL Studio.app/Contents/MacOS/PyiTOL Studio"
# 预期输出：PyiTOL Studio smoke OK — 31 template types, …

# GUI 启动
open "dist/PyiTOL Studio.app"
```

## 3. 签名与公证（对外分发）

本地构建使用 ad-hoc 签名（`codesign_identity=None`）：**占位符证书
（如 "Developer ID Application: <你的证书>"）会让构建在 codesign 步骤直接失败**。
公开分发时再换成真实身份：

```bash
codesign --deep --force --options runtime --timestamp \
  --sign "Developer ID Application: <证书>" "dist/PyiTOL Studio.app"
xcrun notarytool submit PyiTOL-Studio.dmg --keychain-profile pyitol --wait
xcrun stapler staple PyiTOL-Studio.dmg
```

未公证构建首启被 Gatekeeper 拦截时的临时解法：右键 →「打开」，或
`xattr -cr "/Applications/PyiTOL Studio.app"`。

## 4. 已知坑（方案 R3）

- scipy/dendropy 需 hidden imports（已写入 spec）；
- `target_arch="universal2"` 需所有依赖提供双架构 wheel，缺失时构建失败或退回
  单架构——默认不指定，按原生 arm64 出包；
- 首次启动若被 Gatekeeper 拦截，检查公证票据是否 staple；
- 无障碍/屏幕录制未授权时无法用系统 API 截取窗口，可用 §2 的自检命令代替
  人工点验。

## 5. 验收

干净 macOS 12/13/14/15（arm64）双击可用；`PYITOLSTUDIO_SMOKE=1` 自检通过；
断网/无 Key 时降级路径可用（§10.4，开发方案）。
