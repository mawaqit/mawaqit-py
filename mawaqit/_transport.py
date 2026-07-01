"""Transport helpers shared by the async and sync clients.

httpx uses a single :class:`httpx.Response` type for both its sync and async
clients, so the status-to-exception mapping and query-param builder are written
once here (top-level, not under ``_async``) and imported by both clients.
"""

from __future__ import annotations

from typing import Any

import httpx

from .exceptions import (
    BadCredentialsException,
    MawaqitException,
    NotFoundException,
)


def raise_for_status(response: httpx.Response) -> None:
    """Translate a non-2xx MAWAQIT response into the matching exception."""
    if response.is_success:
        return
    status = response.status_code
    suffix = f" (HTTP {status})"
    if status == 401:
        raise BadCredentialsException(
            "Authentication failed. Please check your MAWAQIT credentials." + suffix
        )
    if status == 404:
        raise NotFoundException("Resource not found." + suffix)
    raise MawaqitException("Unexpected MAWAQIT API error." + suffix)


def query_params(**params: Any) -> dict[str, Any]:
    """Drop ``None`` values so optional query parameters are omitted."""
    return {key: value for key, value in params.items() if value is not None}
