"""The errors raised by the clients."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import httpx

__all__ = [
    "APIConnectionError",
    "APIError",
    "APIResponseValidationError",
    "APIStatusError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "InternalServerError",
    "MawaqitError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
]


class MawaqitError(Exception):
    """Base class of every error raised by this library."""


class APIError(MawaqitError):
    """A request to the MAWAQIT API failed.

    Attributes:
        message: What went wrong.
        request: The request that failed.
        body: The decoded JSON body of the response, its text when it is not
            JSON, or `None` without a response.
    """

    message: str
    request: httpx.Request
    body: Any

    def __init__(self, message: str, request: httpx.Request, *, body: Any) -> None:
        """Create the error of a failed request."""
        super().__init__(message)
        self.message = message
        self.request = request
        self.body = body


class APIConnectionError(APIError):
    """The API could not be reached."""

    def __init__(
        self, request: httpx.Request, message: str = "Could not reach MAWAQIT."
    ) -> None:
        """Create the error of a request that got no response."""
        super().__init__(message, request, body=None)


class APITimeoutError(APIConnectionError):
    """The API did not answer in time."""

    def __init__(self, request: httpx.Request) -> None:
        """Create the error of a request that timed out."""
        super().__init__(request, "MAWAQIT did not answer in time.")


class _ResponseError(APIError):
    """An error with a response."""

    response: httpx.Response
    status_code: int

    def __init__(self, message: str, response: httpx.Response, *, body: Any) -> None:
        super().__init__(message, response.request, body=body)
        self.response = response
        self.status_code = response.status_code


class APIResponseValidationError(_ResponseError):
    """The API answered with data that does not match the expected model.

    Attributes:
        response: The response.
        status_code: The HTTP status code of the response.
    """


class APIStatusError(_ResponseError):
    """The API answered with an error status code.

    Attributes:
        response: The response.
        status_code: The HTTP status code of the response.
    """

    def __str__(self) -> str:
        """Return the message, with the status code."""
        return f"{self.message} (HTTP {self.status_code})"


class BadRequestError(APIStatusError):
    """The API rejected the request as invalid (HTTP 400)."""


class AuthenticationError(APIStatusError):
    """The API token, or the email and password, are wrong (HTTP 401)."""


class PermissionDeniedError(APIStatusError):
    """The account used all its API calls, or the request was blocked (HTTP 403)."""


class NotFoundError(APIStatusError):
    """The resource does not exist (HTTP 404)."""


class RateLimitError(APIStatusError):
    """Too many requests were sent (HTTP 429)."""


class InternalServerError(APIStatusError):
    """The API failed to answer (HTTP 500 and above)."""


_FIRST_SERVER_ERROR = 500
_STATUS_ERRORS: dict[int, type[APIStatusError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    429: RateLimitError,
}


def status_error(response: httpx.Response) -> APIStatusError:
    """Return the error matching the status code of an error response."""
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text
    message: object = None
    if isinstance(body, dict):
        message = cast("dict[str, object]", body).get("message")
    if not isinstance(message, str) or not message:
        message = response.reason_phrase or "Unknown error"
    if response.status_code >= _FIRST_SERVER_ERROR:
        return InternalServerError(message, response, body=body)
    error = _STATUS_ERRORS.get(response.status_code, APIStatusError)
    return error(message, response, body=body)
