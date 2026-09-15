"""iTOL upload/export bridge (FR-8).

Thin Qt-free wrapper over ``pyitol.api.client.ITOLAPIClient``. The API key
is only ever accepted from the environment or a key file path — never
stored by the GUI.
"""

from __future__ import annotations

from pathlib import Path

from .formats import EXPORT_FORMATS


def resolve_api_key(api_key_file: str | None = None) -> str | None:
    """Key resolution order: environment variable -> key file. Returns None
    when unavailable; callers degrade to offline mode."""
    import os  # noqa: PLC0415

    key = os.environ.get("ITOL_API_KEY")
    if key:
        return key.strip()
    if api_key_file:
        path = Path(api_key_file).expanduser()
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return None


def upload_and_export(
    tree_file: str | Path,
    template_files: list[str | Path],
    output_dir: str | Path,
    fmt: str = "svg",
    api_key_file: str | None = None,
    project_name: str | None = None,
    force: bool = False,
) -> dict:
    """Upload tree + templates, then export in the requested format.

    Returns ``{"tree_id": str, "files": {tree_id: Path}}``.
    Raises engine exceptions (UploadError/ExportError) on failure.
    """
    import os  # noqa: PLC0415

    from pyitol.api.client import ITOLAPIClient  # noqa: PLC0415

    if fmt not in EXPORT_FORMATS:
        raise ValueError(f"不支持的导出格式：{fmt}（可选：{'/'.join(EXPORT_FORMATS)}）")
    key = resolve_api_key(api_key_file)
    if not key:
        raise RuntimeError(
            "未找到 iTOL API Key：请设置环境变量 ITOL_API_KEY，或在设置中指定密钥文件路径"
        )
    out_dir = str(output_dir).strip() or os.getcwd()  # engine treats "" as falsy

    client = ITOLAPIClient(api_key=key, api_key_file=None)
    try:
        tree_id = client.upload(
            str(tree_file),
            [str(t) for t in template_files],
            force=force,
            project_name=project_name,
        )
        files = client.export([tree_id], fmt=fmt, output_dir=out_dir)
    finally:
        client.close()
    return {"tree_id": tree_id, "files": {k: str(v) for k, v in files.items()}}
