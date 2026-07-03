"""v3 mosque resource."""

from __future__ import annotations

from mawaqit._generated import v3 as models
from mawaqit._transport import query_params
from mawaqit.responses import AnnouncementsAndEvents

from .._base import Resource


class MosqueResource(Resource):
    """Mosque endpoints of the v3 API."""

    prefix = "3.0/mosque"

    async def times(self, uuid: str) -> models.Times:
        """Prayer times, iqama and calendar for a mosque.

        Args:
            uuid: The mosque uuid returned by the search API.
        """
        return await self._get(f"{uuid}/times", cast_to=models.Times)

    async def info(self, uuid: str) -> models.Info:
        """Descriptive info for a mosque (address, services, flash message).

        Args:
            uuid: The mosque uuid returned by the search API.
        """
        return await self._get(f"{uuid}/info", cast_to=models.Info)

    async def by_id(self, mosque_id: str) -> models.InfoById:
        """Minimal mosque info looked up by numeric id.

        Args:
            mosque_id: The numeric id of the mosque.
        """
        return await self._get(mosque_id, cast_to=models.InfoById)

    async def by_slug(self, slug: str) -> models.InfoById:
        """Minimal mosque info looked up by slug.

        Args:
            slug: The mosque slug (e.g. ``"mosquee-essunna-houilles"``).
        """
        return await self._get(f"slug/{slug}", cast_to=models.InfoById)

    async def config(self, uuid: str) -> models.Config:
        """Big-screen display configuration for a mosque.

        Args:
            uuid: The mosque uuid returned by the search API.
        """
        return await self._get(f"{uuid}/config", cast_to=models.Config)

    async def announcements(self, uuid: str) -> AnnouncementsAndEvents:
        """Announcements and events for a mosque.

        Args:
            uuid: The mosque uuid returned by the search API.
        """
        return await self._get(f"{uuid}/announcements", cast_to=AnnouncementsAndEvents)

    async def flash_message(self, uuid: str) -> list[models.FlashMessage]:
        """Flash messages for a mosque.

        Args:
            uuid: The mosque uuid returned by the search API.
        """
        return await self._get_list(
            f"{uuid}/flash-message", cast_to=models.FlashMessage
        )

    async def hijri_date(self, uuid: str) -> models.HijriDate:
        """Hijri date adjustment parameters for a mosque.

        Args:
            uuid: The mosque uuid returned by the search API.
        """
        return await self._get(f"{uuid}/hijri-date", cast_to=models.HijriDate)

    async def messages(self, uuid: str) -> models.Messages:
        """Combined announcements/events message feed for a mosque.

        Args:
            uuid: The mosque uuid returned by the search API.
        """
        return await self._get(f"{uuid}/messages", cast_to=models.Messages)

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
        """Report an Android TV box life-status ping for a mosque.

        Args:
            uuid: The mosque uuid returned by the search API.
            device_id: Unique identifier of the Android TV box (required).
            brand: Device brand.
            model: Device model.
            android_version: Android OS version running on the device.
            app_version: MAWAQIT app version running on the device.
        """
        await self._post(
            f"{uuid}/androidtv-life-status",
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
