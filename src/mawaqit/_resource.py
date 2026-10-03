"""The base classes of the resources, the groups of operations of a client."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base_client import AsyncAPIClient, SyncAPIClient

__all__ = ["AsyncAPIResource", "SyncAPIResource"]


class AsyncAPIResource:
    """A group of operations of the async client."""

    def __init__(self, client: AsyncAPIClient) -> None:
        """Bind the operations to a client."""
        self._client = client


class SyncAPIResource:
    """A group of operations of the sync client."""

    def __init__(self, client: SyncAPIClient) -> None:
        """Bind the operations to a client."""
        self._client = client
