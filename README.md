# MAWAQIT Python library

[![CI](https://github.com/mawaqit/mawaqit-py/actions/workflows/ci.yml/badge.svg)](https://github.com/mawaqit/mawaqit-py/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mawaqit)](https://pypi.org/project/mawaqit/)
[![Python](https://img.shields.io/pypi/pyversions/mawaqit)](https://pypi.org/project/mawaqit/)

> [!CAUTION]
> **Use of the MAWAQIT API is currently not authorized outside of official MAWAQIT applications.**
> This library is published for transparency and for MAWAQIT's own projects. Please do not use it
> to access the API from third-party applications, scripts, or services. Thank you for respecting this.

The official Python library for the [MAWAQIT](https://mawaqit.net) API: search
mosques, and read their prayer times, iqama times and Hijri date.

- **Async and sync** clients, with the same methods.
- **Fully typed**: every argument, response and field, with its documentation
  in your editor.
- **Robust**: retries with backoff, timeouts, and one exception per kind of
  error.
- **Generated from the OpenAPI description of the API**, so the methods and
  models follow it exactly.

## Installation

```sh
pip install mawaqit
```

Python 3.10 or newer.

## Usage

```python
import asyncio

from mawaqit import AsyncMawaqitClient


async def main() -> None:
    async with AsyncMawaqitClient(token="...") as client:
        mosques = await client.mosques.search(lat=48.8414, lon=2.3557)
        prayer_times = await client.mosques.prayer_times(mosques[0].uuid)
        print(prayer_times.name, prayer_times.calendar[0]["1"])


asyncio.run(main())
```

The sync client has the same methods, without `await`:

```python
from mawaqit import MawaqitClient

with MawaqitClient(token="...") as client:
    mosques = client.mosques.search(word="grande mosquée de paris")
```

| Method | Returns |
| --- | --- |
| `client.auth.login(email=..., password=...)` | The `Account` of these credentials, with its API token |
| `client.mosques.search(word=...)` or `(lat=..., lon=...)` | A list of `Mosque` |
| `client.mosques.prayer_times(uuid)` | The `PrayerTimes` of the year, with iqama |
| `client.mosques.hijri_settings(uuid)` | The `HijriSettings` of the mosque |

Responses are [Pydantic](https://docs.pydantic.dev) models, from
`mawaqit.types`, with snake_case attributes: `mosque.women_space`,
`prayer_times.iqama_calendar`. `model_dump(by_alias=True)` gives back the JSON
of the API. Fields the API adds later are kept in `model_extra`.

### Authentication

Every method but `search()` and `login()` needs an API token. Get it once from
an email and password, and keep it rather than the password:

```python
account = await client.auth.login(email="...", password="...")
client = client.with_options(token=account.api_access_token)
```

The token can also come from the `MAWAQIT_TOKEN` environment variable.

### Hijri date

MAWAQIT computes the Hijri date of a mosque from its Hijri settings, like the
mosque screens and the app do:

```python
from mawaqit import hijri
from mawaqit.hijri import HijriMonth

settings = await client.mosques.hijri_settings(uuid)
today = hijri.today(settings, prayer_times.timezone)
print(today)  # 9 Ramadan 1448
if today.month is HijriMonth.RAMADAN:
    ...
```

`hijri.from_gregorian(day, settings)` gives the date of another day, but only
today's is reliable: mosques change their settings after the moon sighting.

### Errors

Every error inherits from `MawaqitError`:

| Error | When |
| --- | --- |
| `AuthenticationError` | Wrong token, email or password (HTTP 401) |
| `PermissionDeniedError` | The account used all its API calls (HTTP 403) |
| `NotFoundError` | No mosque has this UUID (HTTP 404) |
| `RateLimitError`, `BadRequestError`, `InternalServerError` | HTTP 429, 400, 500 and above |
| `APIStatusError` | Any other error status. Base class of the ones above |
| `APIConnectionError`, `APITimeoutError` | MAWAQIT could not be reached, or did not answer in time |
| `APIResponseValidationError` | The response does not match the expected model |

`APIError`, their base class, has the failed `request` and the response
`body`; `APIStatusError` adds the `response` and its `status_code`.

### Retries and timeouts

Network errors, timeouts and HTTP 408, 429, 500, 502, 503 and 504 are retried
twice, after about 0.5 then 1 second, or after the delay of `Retry-After`. Requests
time out after 30 seconds.

```python
client = AsyncMawaqitClient(token="...", max_retries=5, timeout=10)
fast = client.with_options(max_retries=0)
```

### Sharing an HTTPX client

Pass your [HTTPX](https://www.python-httpx.org) client to share its connection
pool, as in Home Assistant. It stays open when the MAWAQIT client is closed.

```python
client = AsyncMawaqitClient(token=token, http_client=get_async_client(hass))
```

### Logging

Retries are logged at the `INFO` level of the `mawaqit` logger.

## Versioning

This library follows [Semantic Versioning](https://semver.org). See the
[changelog](CHANGELOG.md), with the migration guide from 1.x.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[Apache 2.0](LICENSE). The license covers the code of this library, not access
to the MAWAQIT API, which requires an authorization from MAWAQIT. Questions:
[support@mawaqit.net](mailto:support@mawaqit.net).
