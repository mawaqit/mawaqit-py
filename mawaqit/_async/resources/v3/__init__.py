"""v3 API namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .mosque import MosqueResource
from .statistic import StatisticResource

if TYPE_CHECKING:
    from ...client import AsyncMawaqitClient


class AsyncV3:
    """Namespace grouping every v3 resource under ``client.v3``."""

    def __init__(self, client: AsyncMawaqitClient) -> None:
        self.mosque = MosqueResource(client)
        self.statistic = StatisticResource(client)


__all__ = ["AsyncV3"]
