"""pyitol YAML config bridge (FR-7).

Field definitions mirror ``config.example.yaml`` from the pyitol engine
one-to-one, so the GUI config editor always matches the engine contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .formats import EXPORT_FORMATS

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
MULTI_TREE_MODES = ("ask", "first", "last", "random", "split", "all")
NAME_FORMATS = ("auto", "gtdb", "embedded", "ncbi", "underscore", "mixed")
DELIMITER_MODES = ("segment", "reverse", "greedy")


@dataclass(frozen=True)
class ConfigField:
    key: str
    label: str
    widget: str  # path | dir | choice | text | int
    default: Any
    choices: tuple[str, ...] = ()
    required: bool = False
    help: str = ""


CONFIG_FIELDS: tuple[ConfigField, ...] = (
    ConfigField(
        "api_key_file",
        "API 密钥文件路径",
        "path",
        ".itolapi.key",
        help="内容为纯文本 iTOL API Key 的本地文件；也可用环境变量 ITOL_API_KEY",
    ),
    ConfigField(
        "default_format",
        "默认导出格式",
        "choice",
        "svg",
        choices=EXPORT_FORMATS,
        help="svg / png / pdf / tiff / eps / newick / nexus / phyloxml",
    ),
    ConfigField("output_directory", "输出目录", "dir", ".", help="导出结果保存目录"),
    ConfigField("template_directory", "模板文件目录", "dir", "", help="留空则使用当前目录"),
    ConfigField("tree_directory", "树文件目录", "dir", "", help="留空则使用当前目录"),
    ConfigField("log_level", "日志级别", "choice", "INFO", choices=LOG_LEVELS),
    ConfigField("log_file", "日志文件路径", "text", "", help="留空则仅输出到控制台"),
    ConfigField("multi_tree_mode", "多树处理策略", "choice", "ask", choices=MULTI_TREE_MODES),
    ConfigField("name_format", "分类学命名格式", "choice", "auto", choices=NAME_FORMATS),
    ConfigField("taxonomy_delimiter_mode", "嵌入式格式解析策略", "choice", "segment", choices=DELIMITER_MODES),
)


def config_idl() -> list[dict[str, Any]]:
    """Config editor form description, same shape as template IDL fields."""
    return [
        {
            "key": f.key,
            "label": f.label,
            "widget": f.widget,
            "default": f.default,
            "required": f.required,
            "choices": list(f.choices),
            "help": f.help,
        }
        for f in CONFIG_FIELDS
    ]


def _yaml_scalar(value: Any) -> str:
    """Render a scalar safely: quote anything YAML could misread.

    A JSON double-quoted string is also a valid YAML flow scalar, so
    ``json.dumps`` is used for the quoted form (paths with ``:``/``#`` etc.
    would otherwise corrupt the generated config).
    """
    if isinstance(value, str):
        text = value.strip()
        needs_quoting = (
            text == ""
            or text != value
            or text.lower() in ("null", "true", "false", "yes", "no", "on", "off", "~")
            or any(c in text for c in ":#{}[],&*?|>'\"%@`")
            or text[:1] in "-!&*?|>%@`\"'"
            or text != text.strip()
        )
        return json.dumps(text, ensure_ascii=False) if needs_quoting else text
    return str(value)


def build_config_yaml(values: dict[str, Any]) -> str:
    """Render a pyitol config YAML from form values (comments included)."""
    lines = [
        "# PyiTOL Studio 生成的 pyitol 配置文件",
        "# 用法：pyitol --config <本文件>",
    ]
    for f in CONFIG_FIELDS:
        value = values.get(f.key, f.default)
        if value is None:
            value = ""
        lines.append("")
        if f.help:
            lines.append(f"# {f.help}")
        lines.append(f"{f.key}: {_yaml_scalar(value)}")
    return "\n".join(lines) + "\n"


def validate_config_values(values: dict[str, Any]) -> list[str]:
    """Cross-field validation with friendly messages."""
    errors: list[str] = []
    fmt = str(values.get("default_format", "svg")).lower()
    if fmt not in EXPORT_FORMATS:
        errors.append(f"default_format 无效：{fmt}（可选：{'/'.join(EXPORT_FORMATS)}）")
    level = str(values.get("log_level", "INFO")).upper()
    if level not in LOG_LEVELS:
        errors.append(f"log_level 无效：{level}")
    mode = str(values.get("multi_tree_mode", "ask")).lower()
    if mode not in MULTI_TREE_MODES:
        errors.append(f"multi_tree_mode 无效：{mode}")
    naming = str(values.get("name_format", "auto")).lower()
    if naming not in NAME_FORMATS:
        errors.append(f"name_format 无效：{naming}")
    delimiter = str(values.get("taxonomy_delimiter_mode", "segment")).lower()
    if delimiter not in DELIMITER_MODES:
        errors.append(f"taxonomy_delimiter_mode 无效：{delimiter}")
    return errors
