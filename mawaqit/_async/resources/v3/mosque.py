"""v3 mosque resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mawaqit._generated import v3 as models
from mawaqit._transport import query_params
from mawaqit.responses import AnnouncementsAndEvents

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class MosqueResource:
    """Mosque endpoints of the v3 API."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self._client = client

    async def times(self, uuid: str) -> models.Times:
        """Prayer times, iqama and calendar for a mosque."""
        return await self._client._get(f"3.0/mosque/{uuid}/times", cast_to=models.Times)

    async def info(self, uuid: str) -> models.Info:
        """Descriptive info for a mosque (address, services, flash message)."""
        return await self._client._get(f"3.0/mosque/{uuid}/info", cast_to=models.Info)

    async def by_id(self, mosque_id: str) -> models.InfoById:
        """Minimal mosque info looked up by numeric id."""
        return await self._client._get(
            f"3.0/mosque/{mosque_id}", cast_to=models.InfoById
        )

    async def by_slug(self, slug: str) -> models.InfoById:
        """Minimal mosque info looked up by slug."""
        return await self._client._get(
            f"3.0/mosque/slug/{slug}", cast_to=models.InfoById
        )

    async def config(self, uuid: str) -> models.Config:
        """Big-screen display configuration for a mosque."""
        return await self._client._get(
            f"3.0/mosque/{uuid}/config", cast_to=models.Config
        )

    async def announcements(self, uuid: str) -> AnnouncementsAndEvents:
        """Announcements and events for a mosque."""
        return await self._client._get(
            f"3.0/mosque/{uuid}/announcements", cast_to=AnnouncementsAndEvents
        )

    async def flash_message(self, uuid: str) -> list[models.FlashMessage]:
        """Flash messages for a mosque."""
        return await self._client._get_list(
            f"3.0/mosque/{uuid}/flash-message", cast_to=models.FlashMessage
        )

    async def hijri_date(self, uuid: str) -> models.HijriDate:
        """Hijri date adjustment parameters for a mosque."""
        return await self._client._get(
            f"3.0/mosque/{uuid}/hijri-date", cast_to=models.HijriDate
        )

    async def messages(self, uuid: str) -> models.Messages:
        """Combined announcements/events message feed for a mosque."""
        return await self._client._get(
            f"3.0/mosque/{uuid}/messages", cast_to=models.Messages
        )

    async def androidtv_life_status(
        self,
        uuid: str,
        *,
        device_id: str,
        brand: str | None = None,
        model: str | None = None,
        android_version: str | None = None,
        app_version: str | None = None,
    ) -> None:
        """Report an Android TV box life-status ping for a mosque."""
        await self._client._post(
            f"3.0/mosque/{uuid}/androidtv-life-status",
            json=query_params(
                **{
                    "device-id": device_id,
                    "brand": brand,
                    "model": model,
                    "android-version": android_version,
                    "app-version": app_version,
                }
            ),
        )
