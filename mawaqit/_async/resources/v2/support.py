"""v2 support resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mawaqit._generated import v2 as models
from mawaqit._transport import query_params

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class SupportResource:
    """Support endpoint of the v2 API."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self._client = client

    async def get(self, *, country: str | None = None) -> models.Support:
        """WhatsApp support URLs, optionally for a specific country."""
        return await self._client._get(
            "2.0/support",
            params=query_params(country=country),
            cast_to=models.Support,
        )
