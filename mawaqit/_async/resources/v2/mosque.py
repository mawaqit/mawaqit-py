"""v2 mosque resource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mawaqit._generated import v2 as models
from mawaqit._transport import query_params

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class MosqueResource:
    """Mosque endpoints of the v2 API."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self._client = client

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
        return await self._client._get_list(
            "2.0/mosque/search",
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
            "GET", "2.0/mosque/list-uuid", params=query_params(page=page)
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
        return await self._client._get(
            f"2.0/mosque/{uuid}/prayer-times",
            params=query_params(calendar=calendar, updatedAt=updated_at),
            cast_to=models.PrayerTimes,
        )

    async def weather(self, uuid: str) -> models.Weather:
        """Weather for the mosque's city."""
        return await self._client._get(
            f"2.0/mosque/{uuid}/weather", cast_to=models.Weather
        )

    async def data(self, mosque_id: str) -> dict[str, Any]:
        """Full offline-sync payload (typed as a bare object by the swagger)."""
        return await self._client._get_json(f"2.0/mosque/{mosque_id}/data")

    async def map(self, country_code: str) -> models.MosqueForMap:
        """Mosques shown on the homepage map for a country code (FR, DZ, ...)."""
        return await self._client._get(
            f"2.0/mosque/map/{country_code}", cast_to=models.MosqueForMap
        )

    async def list(
        self, *, order: str | None = None, page: int | None = None
    ) -> list[models.Mosque]:
        """List all mosques (paginated)."""
        return await self._client._get_list(
            "2.0/mosque",
            params=query_params(order=order, page=page),
            cast_to=models.Mosque,
        )

    async def favorite(self, uuid: str) -> None:
        """Increment the mosque's subscriber counter.

        Convenience alias for ``client.v2.statistic.favorite``.
        """
        await self._client._post(f"2.0/statistic/mosque/{uuid}/favorite")

    async def unfavorite(self, uuid: str) -> None:
        """Decrement the mosque's subscriber counter.

        Convenience alias for ``client.v2.statistic.unfavorite``.
        """
        await self._client._delete(f"2.0/statistic/mosque/{uuid}/favorite")
