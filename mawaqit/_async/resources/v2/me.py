"""v2 authenticated-user resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mawaqit._generated import v2 as models

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class MeResource:
    """Authenticated-user endpoint of the v2 API."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self._client = client

    async def get(self) -> models.Me:
        """The authenticated user's id, token and API quota."""
        return await self._client._get("2.0/me", cast_to=models.Me)
