"""v2 hadith resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mawaqit._generated import v2 as models
from mawaqit._transport import query_params

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class HadithResource:
    """Hadith endpoints of the v2 API."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self._client = client

    async def random(
        self, *, lang: str | None = None, max_length: int | None = None
    ) -> models.Hadith:
        """A random hadith, optionally filtered by language and max length."""
        return await self._client._get(
            "2.0/hadith/random",
            params=query_params(lang=lang, maxLength=max_length),
            cast_to=models.Hadith,
        )
