"""Python wrapper to access the MAWAQIT API."""

from __future__ import annotations
from asyncio import sleep
import json
from types import TracebackType
from typing import Any
import aiohttp
from aiohttp import ClientSession

from .consts import MAX_LOGIN_RETRIES, SEARCH_MOSQUES_URL, LOGIN_URL
from .utils import prayer_times_url, mosque_data_url
from .exceptions import (
    BadCredentialsException,
    NotFoundException,
    MawaqitException,
    MissingCredentials,
    NoMosqueAround,
    NoMosqueFound,
)


class AsyncMawaqitClient:
    """Interface async class for the MAWAQIT official API."""

    def __init__(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        mosque: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        session: ClientSession | None = None,
    ) -> None:
        self.username = username
        self.password = password
        self.latitude = latitude
        self.longitude = longitude
        self.mosque = mosque
        self.token = token
        self.session = session if session is not None else ClientSession()
        # Only close the session if the client created it, so an injected
        # (externally owned) session is never closed by this client.
        self._close_session = session is None

    async def __aenter__(self) -> AsyncMawaqitClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    def _raise_for_status(
        self, response: aiohttp.ClientResponse, context: str = ""
    ) -> None:
        """Raise the appropriate exception based on the HTTP status code."""
        if response.status == 200:
            return
        suffix = f" Response.status: {response.status}"
        if response.status == 401:
            raise BadCredentialsException(
                "Authentication failed. Please check your MAWAQIT credentials." + suffix
            )
        if response.status == 404:
            raise NotFoundException(f"{context or 'Resource'} not found." + suffix)
        raise MawaqitException("Unexpected error. Please retry." + suffix)

    async def close(self) -> None:
        """Close the session if it was created by the client."""
        if self._close_session:
            await self.session.close()

    async def get_api_token(self) -> str:
        """Return a valid API token, retrying on transient login failures."""
        if self.token is not None:
            return self.token

        for attempt in range(MAX_LOGIN_RETRIES):
            try:
                await self.login()
            except (BadCredentialsException, MissingCredentials):
                raise
            except MawaqitException:
                if attempt == MAX_LOGIN_RETRIES - 1:
                    raise
                await sleep(min(16, 2**attempt))
            else:
                if self.token is not None:
                    return self.token

        raise MawaqitException("Could not obtain an API token.")  # pragma: no cover

    async def _search_mosques(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        headers = {
            "Authorization": format(self.token),
            "Content-Type": "application/json",
        }

        async with self.session.get(
            SEARCH_MOSQUES_URL, params=params, data=None, headers=headers
        ) as response:
            self._raise_for_status(response, context="Mosque")
            data: list[dict[str, Any]] = await response.json()

        return data

    async def all_mosques_neighborhood(self) -> list[dict[str, Any]]:
        """Get the five nearest mosques from the Client coordinates.
        Returns a list of dicts with info on the mosques."""

        if (self.latitude is None) or (self.longitude is None):
            raise MissingCredentials(
                "Please provide a latitude and a longitude in your MawaqitClient object."
            )

        payload = {"lat": self.latitude, "lon": self.longitude}

        data = await self._search_mosques(payload)

        if not data:
            raise NoMosqueAround(
                "No mosque found around your location. Please check your coordinates."
            )

        return data

    async def fetch_mosques_by_keyword(
        self, keyword: str | None, page: int = 1, items_per_page: int = 10
    ) -> list[dict[str, Any]]:
        """Get the mosques from the specified keyword.
        Returns a list of dicts with info on the mosques."""

        if keyword is None:
            raise MissingCredentials(
                "Please provide a Keyword  when calling the fetch_mosques_by_keyword method."
            )

        payload = {
            "word": keyword,
            "page": page,
            "itemsPerPage": items_per_page,
        }

        data = await self._search_mosques(payload)

        if not data:
            raise NoMosqueFound(
                "No mosque found with the keyword. Please check with another keyword"
            )

        return data

    async def fetch_prayer_times(self) -> dict[str, Any]:
        """Fetch the prayer times calendar for self.mosque,
        Returns a dict with info on the mosque and the year-calendar prayer times."""

        if self.mosque is None:
            mosques = await self.all_mosques_neighborhood()
            mosque_id: str = mosques[0]["uuid"]
        else:
            mosque_id = self.mosque

        headers = {
            "Content-Type": "application/json",
            "Api-Access-Token": format(self.token),
        }

        endpoint_url = prayer_times_url(mosque_id)

        async with self.session.get(
            endpoint_url, data=None, headers=headers
        ) as response:
            self._raise_for_status(response, context="Mosque")
            data: dict[str, Any] = await response.json()

        return data

    async def fetch_mosque_by_id(self, uuid: str | None) -> dict[str, Any]:
        """Fetch the prayer times calendar for self.mosque,
        Returns a dict with info on the mosque and the year-calendar prayer times."""

        if uuid is None:
            raise ValueError("Please provide a mosque uuid.")

        headers = {
            "Content-Type": "application/json",
            "Api-Access-Token": format(self.token),
        }

        endpoint_url = mosque_data_url(uuid)

        async with self.session.get(
            endpoint_url, data=None, headers=headers
        ) as response:
            self._raise_for_status(response, context="Mosque")
            data: dict[str, Any] = await response.json()

        return data

    async def login(self) -> None:
        """Log into the MAWAQIT website."""

        if (self.username is None) or (self.password is None):
            raise MissingCredentials("Please provide a MAWAQIT login and password.")

        auth = aiohttp.BasicAuth(self.username, self.password)

        endpoint_url = LOGIN_URL

        async with await self.session.post(endpoint_url, auth=auth) as response:
            self._raise_for_status(response, context="User")

            data = await response.text()

            self.token = json.loads(data)["apiAccessToken"]
