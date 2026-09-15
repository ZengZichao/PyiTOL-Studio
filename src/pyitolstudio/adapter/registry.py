"""Registry introspection: turn the pyitol TemplateRegistry into GUI-facing
type metadata.

This module is Qt-free and safe to use in headless tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Official iTOL grouping used by the template wizard (FR-1).
# Keys are pyitol registry type names (as returned by
# ``TemplateRegistry.list_types()``).
TREE_STRUCTURE_TYPES = frozenset(
    {"dataset_tree_colors", "dataset_labels", "dataset_collapse", "dataset_prune", "dataset_spacing"}
)
METADATA_TYPES = frozenset({"dataset_popup_info"})
EXTENSION_TYPES = frozenset({"dataset_manual", "dataset_meme", "dataset_placement", "dataset_treestyle"})

GROUP_ORDER = ("datasets", "tree", "metadata", "extensions")

GROUP_LABELS_ZH = {
    "datasets": "数据集 Datasets",
    "tree": "树结构 Tree structure",
    "metadata": "元数据 Metadata",
    "extensions": "扩展 Advanced",
}

# Wizard priority from the development plan §4 (P0 first).
PRIORITY_ORDER = {
    "dataset_colorstrip": 0,
    "dataset_simple_bar": 1,
    "dataset_multibar": 1,
    "dataset_heatmap": 1,
    "dataset_binary": 1,
    "dataset_tree_colors": 1,
    "dataset_labels": 1,
}

# Types with no wizard form of their own.
NON_WIZARD_TYPES = frozenset({"dataset_manual", "dataset_treestyle"})


@dataclass(frozen=True)
class TemplateTypeInfo:
    """GUI-facing description of one registered template type."""

    type_name: str
    header: str
    required_columns: tuple[str, ...] = field(default=())
    no_label_color: bool = False
    group: str = "datasets"
    wizard_supported: bool = True
    priority: int = 99

    @property
    def group_label(self) -> str:
        return GROUP_LABELS_ZH.get(self.group, self.group)


def _engine_registry():
    """Import and return the pyitol default registry.

    Import is local so that the rest of the adapter stays importable for
    tooling without pyitol installed (e.g. docs builds).
    """
    from pyitol.templates.schemas.base import default_registry  # noqa: PLC0415

    return default_registry


def _classify(type_name: str) -> str:
    if type_name in TREE_STRUCTURE_TYPES:
        return "tree"
    if type_name in METADATA_TYPES:
        return "metadata"
    if type_name in EXTENSION_TYPES:
        return "extensions"
    return "datasets"


def list_template_types() -> list[TemplateTypeInfo]:
    """Introspect the engine registry into a sorted list of type metadata.

    Sorted by wizard priority, then group order, then type name — the order
    shown in the template wizard.
    """
    registry = _engine_registry()
    infos: list[TemplateTypeInfo] = []
    for type_name in registry.list_types():
        header = registry.get_header(type_name) or type_name.upper()
        no_label_color = registry.is_no_label_color(type_name)
        infos.append(
            TemplateTypeInfo(
                type_name=type_name,
                header=header,
                required_columns=tuple(registry.get_required_columns(type_name)),
                no_label_color=no_label_color,
                group=_classify(type_name),
                wizard_supported=type_name not in NON_WIZARD_TYPES,
                priority=PRIORITY_ORDER.get(type_name, 50),
            )
        )
    infos.sort(key=lambda i: (i.priority, GROUP_ORDER.index(i.group), i.type_name))
    return infos


def get_type_info(type_name: str) -> TemplateTypeInfo:
    """Return metadata for one type; raises KeyError for unknown names."""
    registry = _engine_registry()
    header = registry.get_header(type_name)
    if header is None:
        raise KeyError(f"Unknown template type: {type_name!r}")
    return TemplateTypeInfo(
        type_name=type_name,
        header=header,
        required_columns=tuple(registry.get_required_columns(type_name)),
        no_label_color=registry.is_no_label_color(type_name),
        group=_classify(type_name),
        wizard_supported=type_name not in NON_WIZARD_TYPES,
        priority=PRIORITY_ORDER.get(type_name, 50),
    )
