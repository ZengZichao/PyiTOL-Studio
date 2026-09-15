"""Adapter layer: the only code that talks to the pyitol engine."""

from .form_idl import SEPARATOR_CHOICES, FieldSpec, build_form_idl, defaults_for_idl
from .generator_bridge import UnitSpec, export_template_file, generate_template_text, validate_separator_line
from .learner_bridge import LearnedUnit, learn_from_file, to_form_values
from .registry import TemplateTypeInfo, get_type_info, list_template_types
from .tree_bridge import tree_leaf_ids

__all__ = [
    "SEPARATOR_CHOICES",
    "FieldSpec",
    "UnitSpec",
    "LearnedUnit",
    "TemplateTypeInfo",
    "build_form_idl",
    "defaults_for_idl",
    "export_template_file",
    "generate_template_text",
    "get_type_info",
    "learn_from_file",
    "list_template_types",
    "to_form_values",
    "tree_leaf_ids",
    "validate_separator_line",
]
