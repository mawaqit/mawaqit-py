"""Base class for API resources: a shared path prefix + typed request sugar."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..client import AsyncMawaqitClient

ModelT = TypeVar("ModelT", bound=BaseModel)


class Resource:
    """A group of endpoints sharing a path ``prefix`` (e.g. ``3.0/mosque``).

    The ``_get``/``_get_list``/``_get_json``/``_post`` helpers prepend
    :attr:`prefix`, so each method only names the part below it
    (``self._get(f"{uuid}/times", ...)``) — call with no path for the prefix
    itself. For the rare endpoint outside the prefix, reach through
    ``self._client`` with an absolute path instead.
    """

    #: Path prefix shared by this resource's endpoints (no trailing slash).
    prefix: str

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self._client = client

    def _path(self, path: str) -> str:
        return f"{self.prefix}/{path}" if path else self.prefix

    async def _get(
        self,
        path: str = "",
        *,
        params: dict[str, Any] | None = None,
        cast_to: type[ModelT],
    ) -> ModelT:
        """GET below the prefix and parse the JSON object into ``cast_to``."""
        return await self._client._get(self._path(path), params=params, cast_to=cast_to)

    async def _get_list(
        self,
        path: str = "",
        *,
        params: dict[str, Any] | None = None,
        cast_to: type[ModelT],
    ) -> list[ModelT]:
        """GET below the prefix and parse a JSON array into ``list[cast_to]``."""
        return await self._client._get_list(
            self._path(path), params=params, cast_to=cast_to
        )

    async def _get_json(
        self, path: str = "", *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET below the prefix and return the raw JSON object (untyped)."""
        return await self._client._get_json(self._path(path), params=params)

    async def _post(self, path: str = "", *, json: Any | None = None) -> None:
        """POST below the prefix (endpoints with no response body)."""
        await self._client._post(self._path(path), json=json)
