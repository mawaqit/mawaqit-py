"""v2 statistic resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class StatisticResource:
    """Statistic endpoints of the v2 API."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self._client = client

    async def favorite(self, uuid: str) -> None:
        """Increment the mosque's subscriber counter."""
        await self._client._post(f"2.0/statistic/mosque/{uuid}/favorite")

    async def unfavorite(self, uuid: str) -> None:
        """Decrement the mosque's subscriber counter."""
        await self._client._delete(f"2.0/statistic/mosque/{uuid}/favorite")
