"""v2 support resource."""

from __future__ import annotations

from mawaqit._generated import v2 as models
from mawaqit._transport import query_params

from .._base import Resource


class SupportResource(Resource):
    """Support endpoint of the v2 API."""

    prefix = "2.0/support"

    async def get(self, *, country: str | None = None) -> models.Support:
        """WhatsApp support URLs, optionally for a specific country."""
        return await self._get(
            params=query_params(country=country),
            cast_to=models.Support,
        )
