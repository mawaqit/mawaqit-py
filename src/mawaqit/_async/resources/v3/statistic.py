"""v3 statistic resource."""

from __future__ import annotations

from typing import Any

from .._base import Resource


class StatisticResource(Resource):
    """Statistic endpoints of the v3 API."""

    prefix = "3.0/statistic"

    async def installations(self) -> dict[str, Any]:
        """Number of installed mosques per country (typed as a bare object)."""
        return await self._get_json("installations")
