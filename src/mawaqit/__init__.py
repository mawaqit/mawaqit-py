"""The official Python library for the MAWAQIT API.

Example:
    ```python
    from mawaqit import AsyncMawaqitClient, hijri

    async with AsyncMawaqitClient(token="...") as client:
        mosques = await client.mosques.search(lat=48.84, lon=2.35)
        settings = await client.mosques.hijri_settings(mosques[0].uuid)
        print(hijri.today(settings, "Europe/Paris"))
    ```
"""

from . import hijri, types
from ._base_client import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from ._client import AsyncMawaqitClient, MawaqitClient
from ._exceptions import (
    APIConnectionError,
    APIError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    MawaqitError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from ._version import __version__

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "APIConnectionError",
    "APIError",
    "APIResponseValidationError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncMawaqitClient",
    "AuthenticationError",
    "BadRequestError",
    "InternalServerError",
    "MawaqitClient",
    "MawaqitError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "__version__",
    "hijri",
    "types",
]
