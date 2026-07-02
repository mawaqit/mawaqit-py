"""v2 mosque resource."""

from __future__ import annotations

from typing import Any

from mawaqit._generated import v2 as models
from mawaqit._transport import query_params

from .._base import Resource


class MosqueResource(Resource):
    """Mosque endpoints of the v2 API."""

    prefix = "2.0/mosque"

    async def search(
        self,
        *,
        word: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        page: int | None = None,
        items_per_page: int | None = None,
        radius: float | None = None,
    ) -> list[models.Mosque]:
        """Search mosques by keyword, or by coordinates when ``lat``/``lon`` are set."""
        return await self._get_list(
            "search",
            params=query_params(
                word=word,
                lat=lat,
                lon=lon,
                page=page,
                itemsPerPage=items_per_page,
                radius=radius,
            ),
            cast_to=models.Mosque,
        )

    async def list_uuid(self, *, page: int | None = None) -> list[str]:
        """List every mosque uuid (paginated)."""
        response = await self._client._request(
            "GET", self._path("list-uuid"), params=query_params(page=page)
        )
        uuids: list[str] = response.json()
        return uuids

    async def prayer_times(
        self,
        uuid: str,
        *,
        calendar: bool | None = None,
        updated_at: int | None = None,
    ) -> models.PrayerTimes:
        """Prayer times and mosque info; pass ``calendar`` for the full year."""
        return await self._get(
            f"{uuid}/prayer-times",
            params=query_params(calendar=calendar, updatedAt=updated_at),
            cast_to=models.PrayerTimes,
        )

    async def weather(self, uuid: str) -> models.Weather:
        """Weather for the mosque's city."""
        return await self._get(f"{uuid}/weather", cast_to=models.Weather)

    async def data(self, mosque_id: str) -> dict[str, Any]:
        """Full offline-sync payload (typed as a bare object by the swagger)."""
        return await self._get_json(f"{mosque_id}/data")

    async def map(self, country_code: str) -> models.MosqueForMap:
        """Mosques shown on the homepage map for a country code (FR, DZ, ...)."""
        return await self._get(f"map/{country_code}", cast_to=models.MosqueForMap)

    async def list(
        self, *, order: str | None = None, page: int | None = None
    ) -> list[models.Mosque]:
        """List all mosques (paginated)."""
        return await self._get_list(
            params=query_params(order=order, page=page),
            cast_to=models.Mosque,
        )

    async def favorite(self, uuid: str) -> None:
        """Increment the mosque's subscriber counter."""
        # Lives under the statistic path, outside this resource's prefix.
        await self._client._post(f"2.0/statistic/mosque/{uuid}/favorite")

    async def unfavorite(self, uuid: str) -> None:
        """Decrement the mosque's subscriber counter."""
        await self._client._delete(f"2.0/statistic/mosque/{uuid}/favorite")
