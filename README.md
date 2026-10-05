# MAWAQIT Python library

[![CI](https://github.com/mawaqit/mawaqit-py/actions/workflows/ci.yml/badge.svg)](https://github.com/mawaqit/mawaqit-py/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mawaqit)](https://pypi.org/project/mawaqit/)
[![Python](https://img.shields.io/pypi/pyversions/mawaqit)](https://pypi.org/project/mawaqit/)
[![License](https://img.shields.io/pypi/l/mawaqit)](https://github.com/mawaqit/mawaqit-py/blob/main/LICENSE)

> [!CAUTION]
> **Use of the MAWAQIT API is not authorized outside of the official MAWAQIT applications.**
>
> This library is published for transparency and for the projects of MAWAQIT. Do not use it to
> access the API from a third-party application, script or service: the API may block such
> access without notice. Thank you for respecting this.

The official Python library for the [MAWAQIT](https://mawaqit.net) API: search
mosques, and read their prayer times, iqama times, Hijri date and screen
settings.

- **Async and sync** clients, with the same methods.
- **Fully typed**: every argument, response and field, documented in your
  editor.
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
        # Fajr, Shuruq, Dhuhr, Asr, Maghrib and Isha of 1 January.
        print(prayer_times.calendar[0]["1"])


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
| `client.mosques.search(word=...)` or `(lat=..., lon=...)` | A list of `Mosque` |
| `client.mosques.get(mosque_id)` | The `MosqueSummary` of a mosque or a home, with its UUID |
| `client.mosques.prayer_times(uuid)` | The `PrayerTimes` of the year, with iqama |
| `client.mosques.hijri_settings(uuid)` | The `HijriSettings` of the mosque |
| `client.mosques.config(uuid)` | The `MosqueConfig`: the settings of the mosque screens |
| `client.mosques.flash_message(uuid)` | The `FlashMessage` of the mosque screens, or `None` |

Responses are [Pydantic](https://docs.pydantic.dev) models, from
`mawaqit.types`, with snake_case attributes: `mosque.women_space`,
`prayer_times.iqama_calendar`. `model_dump(by_alias=True)` gives back the JSON
of the API, and fields the API adds later are kept in `model_extra`.

### Authentication

Every method but `search()` needs an API token, passed as `token=` or set in
the `MAWAQIT_TOKEN` environment variable.

### Hijri date

`mawaqit.hijri` computes the Hijri date of a mosque from its settings, like the
mosque screens and the app do:

```python
from mawaqit import hijri
from mawaqit.hijri import HijriMonth

settings = await client.mosques.hijri_settings(uuid)
today = hijri.today(settings, "Europe/Paris")  # The time zone of the mosque.
print(today)  # 9 Ramadan 1448
if today.month is HijriMonth.RAMADAN:
    ...
```

The date changes at midnight in the time zone of the mosque. Only today's date
is reliable: mosques change their settings after the moon sighting.
`hijri.from_gregorian(day, settings)` gives the date of another day.

### Errors

Every error inherits from `MawaqitError`:

| Error | When |
| --- | --- |
| `AuthenticationError` | The token is wrong (HTTP 401) |
| `PermissionDeniedError` | The account used all its API calls, or the request was blocked (HTTP 403) |
| `NotFoundError` | No mosque has this UUID (HTTP 404) |
| `RateLimitError`, `BadRequestError`, `InternalServerError` | HTTP 429, 400, 500 and above |
| `APIStatusError` | Any other error status, and base class of the ones above |
| `APIConnectionError`, `APITimeoutError` | MAWAQIT could not be reached, or did not answer in time |
| `APIResponseValidationError` | The response does not match the expected model |

`APIError`, their base class, has the failed `request` and the response
`body`. `APIStatusError` adds the `response` and its `status_code`.

```python
from mawaqit import AuthenticationError, MawaqitError

try:
    prayer_times = await client.mosques.prayer_times(uuid)
except AuthenticationError:
    ...  # Ask for a new token.
except MawaqitError as err:
    print(err)  # Invalid token. (HTTP 401)
```

### Retries and timeouts

Network errors, timeouts and HTTP 408, 429, 500, 502, 503 and 504 are retried
twice, after about 0.5 then 1 second, or after the delay of `Retry-After` when
it is one minute or less. Requests time out after 30 seconds.

```python
client = AsyncMawaqitClient(token="...", max_retries=5, timeout=10)
fast = client.with_options(max_retries=0)
```

### Logging

Responses are logged at the `DEBUG` level of the `mawaqit` logger, and retries
at the `INFO` level. The token is never logged.

### Home Assistant

- Pass the HTTPX client of Home Assistant to share its connection pool. It
  stays open when the MAWAQIT client is closed:

  ```python
  client = AsyncMawaqitClient(token=token, http_client=get_async_client(hass))
  ```

- Pass a `tzinfo` rather than a name to `hijri.today()`, to avoid loading a
  time zone in the event loop: `hijri.today(settings, dt_util.get_time_zone(name))`.

## Versioning

This library follows [Semantic Versioning](https://semver.org). See the
[changelog](https://github.com/mawaqit/mawaqit-py/blob/main/CHANGELOG.md), with the migration guide from 1.x.

## Contributing

See [CONTRIBUTING.md](https://github.com/mawaqit/mawaqit-py/blob/main/CONTRIBUTING.md).

## License

[Apache 2.0](https://github.com/mawaqit/mawaqit-py/blob/main/LICENSE). The license covers the code of this library, not access
to the MAWAQIT API, which requires an authorization from MAWAQIT. Questions:
[support@mawaqit.net](mailto:support@mawaqit.net).
