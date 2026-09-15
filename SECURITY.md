# 安全策略 / Security Policy

## 支持的版本 / Supported versions

| 版本 | 支持 |
|---|---|
| 0.1.x | ✅ |
| < 0.1 | ❌ 请升级到受支持版本 |

## 报告漏洞 / Reporting a vulnerability

请**不要**通过公开 issue 报告安全问题。请通过 GitHub「Security → Advisories」
私下报告，我们将在确认后 5 个工作日内回复。

Please **do not** open a public issue for security problems. Report them
privately via GitHub "Security → Advisories".

## 凭据处理 / Credential handling

- PyiTOL Studio 上传到 iTOL 时**只**从环境变量 `ITOL_API_KEY` 或本地密钥文件读取
  API Key，**不会**在 UI 输入、不写入工程文件、不明文落盘。
- 请勿在 issue、截图、`.pyitolproj` 或日志中粘贴你的 iTOL API Key。

The API key is read only from `ITOL_API_KEY` or a key file; it is never typed
into the UI nor written to project files.
