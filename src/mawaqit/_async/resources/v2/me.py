"""v2 authenticated-user resource."""

from __future__ import annotations

from mawaqit._generated import v2 as models

from .._base import Resource


class MeResource(Resource):
    """Authenticated-user endpoint of the v2 API."""

    prefix = "2.0/me"

    async def get(self) -> models.Me:
        """The authenticated user's id, token and API quota."""
        return await self._get(cast_to=models.Me)
