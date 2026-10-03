"""The base class of the models of the API responses."""

from __future__ import annotations

from typing import ClassVar

import pydantic

__all__ = ["BaseModel"]


class BaseModel(pydantic.BaseModel):
    """A model of the API, with snake_case attributes.

    Models are parsed from the camelCase JSON of the API, and can also be built
    with their snake_case names. Fields the API adds later are kept, so a new
    field never breaks parsing: read them with `model_extra`.
    """

    model_config: ClassVar[pydantic.ConfigDict] = pydantic.ConfigDict(
        extra="allow", populate_by_name=True
    )
