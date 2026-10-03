"""The errors raised for each kind of failed response."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mawaqit import (
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

from .conftest import UUID, Client, resolve

if TYPE_CHECKING:
    import respx

PRAYER_TIMES = f"/2.0/mosque/{UUID}/prayer-times"


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (302, APIStatusError),
        (400, BadRequestError),
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (409, APIStatusError),
        (429, RateLimitError),
        (500, InternalServerError),
        (502, InternalServerError),
    ],
)
async def test_status_errors(
    api: respx.MockRouter,
    client: Client,
    status: int,
    error: type[APIStatusError],
) -> None:
    body = {"message": "Invalid token.", "code": status}
    api.get(PRAYER_TIMES).respond(status, json=body)

    with pytest.raises(error) as caught:
        await resolve(client.with_options(max_retries=0).mosques.prayer_times(UUID))

    assert type(caught.value) is error
    assert caught.value.message == "Invalid token."
    assert str(caught.value) == f"Invalid token. (HTTP {status})"
    assert caught.value.status_code == status
    assert caught.value.body == body
    assert caught.value.response.status_code == status
    assert caught.value.request.url.path == f"/api{PRAYER_TIMES}"


async def test_error_with_an_html_page(api: respx.MockRouter, client: Client) -> None:
    api.get(PRAYER_TIMES).respond(401, html="<p>error401</p>")

    with pytest.raises(AuthenticationError) as caught:
        await resolve(client.mosques.prayer_times(UUID))

    assert caught.value.message == "Unauthorized"
    assert str(caught.value) == "Unauthorized (HTTP 401)"
    assert caught.value.body == "<p>error401</p>"


async def test_error_without_a_message(api: respx.MockRouter, client: Client) -> None:
    api.get(PRAYER_TIMES).respond(404, json={"message": ""})

    with pytest.raises(NotFoundError, match=r"^Not Found \(HTTP 404\)$"):
        await resolve(client.mosques.prayer_times(UUID))


async def test_response_that_is_not_json(api: respx.MockRouter, client: Client) -> None:
    api.get(PRAYER_TIMES).respond(200, text="maintenance")

    with pytest.raises(APIResponseValidationError, match="not answer with JSON") as e:
        await resolve(client.mosques.prayer_times(UUID))

    assert e.value.body == "maintenance"
    assert e.value.status_code == 200


async def test_response_with_unexpected_data(
    api: respx.MockRouter, client: Client
) -> None:
    api.get(f"/3.0/mosque/{UUID}/hijri-date").respond(json={"hijriAdjustment": "x"})

    with pytest.raises(APIResponseValidationError, match="unexpected data") as e:
        await resolve(client.mosques.hijri_settings(UUID))

    assert e.value.body == {"hijriAdjustment": "x"}


def test_error_hierarchy() -> None:
    for error in (
        AuthenticationError,
        BadRequestError,
        InternalServerError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
    ):
        assert issubclass(error, APIStatusError)
    assert issubclass(APITimeoutError, APIConnectionError)
    for base in (APIStatusError, APIConnectionError, APIResponseValidationError):
        assert issubclass(base, APIError)
    assert issubclass(APIError, MawaqitError)
