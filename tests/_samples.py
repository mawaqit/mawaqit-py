"""Build minimal valid payloads for a generated pydantic model.

Fills every *required* field with a type-appropriate dummy value, derived from
the model's own field annotations, so resource tests can exercise real response
parsing without hand-writing large payloads. Rigorous validation of the models
against the real spec is done separately by the schemathesis contract tests.
"""

from __future__ import annotations

import types
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel


def _value_for(annotation: Any) -> Any:
    if annotation is None or annotation is type(None):
        return None
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        return _value_for(non_none[0])
    if origin is list:
        args = get_args(annotation)
        return [_value_for(args[0])] if args else []
    if origin in (dict, tuple):
        return {}
    if annotation is Any:
        return "sample"
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return build_sample(annotation)
    if annotation is bool:
        return True
    if annotation is int:
        return 1
    if annotation is float:
        return 1.0
    return "sample"  # str and anything else


def build_sample(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Return a dict with every required field of ``model_cls`` populated."""
    return {
        name: _value_for(field.annotation)
        for name, field in model_cls.model_fields.items()
        if field.is_required()
    }
