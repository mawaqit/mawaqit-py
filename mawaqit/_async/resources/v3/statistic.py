"""v3 statistic resource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class StatisticResource:
    """Statistic endpoints of the v3 API."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self._client = client

    async def installations(self) -> dict[str, Any]:
        """Number of installed mosques per country (typed as a bare object)."""
        return await self._client._get_json("3.0/statistic/installations")
