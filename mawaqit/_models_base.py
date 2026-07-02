"""Base class for the generated pydantic models.

``extra="allow"`` mirrors what the best-in-class SDKs (OpenAI, Anthropic) do:
if the API grows a new field, responses keep parsing instead of crashing, and
the unknown field is still accessible. Combined with the null-hinted fields
being demoted to optional at generation time, parsing never fails on real
MAWAQIT payloads.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MawaqitModel(BaseModel):
    model_config = ConfigDict(extra="allow")
