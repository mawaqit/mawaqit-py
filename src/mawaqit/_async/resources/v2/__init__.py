"""v2 API namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .hadith import HadithResource
from .me import MeResource
from .mosque import MosqueResource
from .support import SupportResource

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class AsyncV2:
    """Namespace grouping every v2 resource under ``client.v2``."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self.mosque = MosqueResource(client)
        self.hadith = HadithResource(client)
        self.support = SupportResource(client)
        self.me = MeResource(client)


__all__ = ["AsyncV2"]
