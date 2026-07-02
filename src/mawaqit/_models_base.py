"""Base class for the generated pydantic models.

``extra="allow"``: if the API grows a new field, responses keep parsing instead
of crashing, and the unknown field is still accessible. Combined with only
identity fields being required (see the normalizer), parsing never fails on real
MAWAQIT payloads.

``populate_by_name``: fields are snake_case Python names with a camelCase alias
(matching the JSON), so responses parse from camelCase while the models can also
be built with the pythonic snake_case names.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MawaqitModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
