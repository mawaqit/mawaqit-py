"""The official MAWAQIT API wrapper.

Two clients with an identical, version-namespaced surface:

    from mawaqit import AsyncMawaqitClient, MawaqitClient

    async with AsyncMawaqitClient(token="...") as client:
        times = await client.v3.mosque.times(uuid)

    with MawaqitClient(token="...") as client:
        times = client.v3.mosque.times(uuid)

The sync client is generated from the async one by unasync, so the two never
drift. Reach each API version through ``client.v2`` / ``client.v3``.
"""

from ._async import AsyncMawaqitClient
from ._async import login as login
from ._sync import MawaqitClient
from ._sync import login as login_sync
from .config import MawaqitSettings
from .exceptions import (
    BadCredentialsException,
    MawaqitException,
    MissingCredentials,
    NotFoundException,
)

__all__ = [
    "AsyncMawaqitClient",
    "MawaqitClient",
    "login",
    "login_sync",
    "MawaqitSettings",
    "MawaqitException",
    "BadCredentialsException",
    "NotFoundException",
    "MissingCredentials",
]
