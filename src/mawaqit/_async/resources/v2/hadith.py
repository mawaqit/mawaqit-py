"""v2 hadith resource."""

from __future__ import annotations

from mawaqit._generated import v2 as models
from mawaqit._transport import query_params

from .._base import Resource


class HadithResource(Resource):
    """Hadith endpoints of the v2 API."""

    prefix = "2.0/hadith"

    async def random(
        self, *, lang: str | None = None, max_length: int | None = None
    ) -> models.Hadith:
        """A random hadith, optionally filtered by language and max length.

        Args:
            lang: Hadith language — one of ``"ar"``, ``"en"``, ``"fr"``, ``"tr"``,
                ``"en-ar"``, ``"fr-ar"``, ``"tr-ar"`` (default ``"ar"``).
            max_length: Max hadith length in characters (default 500).
        """
        return await self._get(
            "random",
            params=query_params(lang=lang, maxLength=max_length),
            cast_to=models.Hadith,
        )
