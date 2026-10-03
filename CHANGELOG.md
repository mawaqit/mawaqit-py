# Changelog

All notable changes to this library. It follows
[Semantic Versioning](https://semver.org).

## 2.0.0 - Unreleased

A new library, generated from the OpenAPI description of the API.

### Added

- `MawaqitClient`, a sync client with the same methods as the async one.
- Typed models for every response, with the documentation of each field.
- `mawaqit.hijri`, to compute the Hijri date of a mosque like MAWAQIT does.
- `client.mosques.hijri_settings()` and `client.mosques.config()`.
- Retries with backoff for network errors, timeouts and temporary errors.
- `with_options()`, to change the token, timeout or retries of a client.

### Changed

- Requests are sent with HTTPX instead of aiohttp.
- A client no longer stores a mosque, a position or credentials: they are
  arguments of the methods.
- Methods return models instead of dictionaries.
- A search that finds nothing returns an empty list instead of raising.

### Migrating from 1.x

| 1.x | 2.0 |
| --- | --- |
| `AsyncMawaqitClient(session=session)` | `AsyncMawaqitClient(http_client=httpx_client)` |
| `await client.all_mosques_neighborhood()` | `await client.mosques.search(lat=..., lon=...)` |
| `await client.fetch_mosques_by_keyword(word, page, size)` | `await client.mosques.search(word=word, page=page, items_per_page=size)` |
| `await client.fetch_prayer_times()` | `await client.mosques.prayer_times(uuid)` |
| `data["iqamaCalendar"]` | `prayer_times.iqama_calendar` |
| `MawaqitException` | `MawaqitError` |
| `BadCredentialsException`, `NotAuthenticatedException` | `AuthenticationError` |
| `NotFoundException` | `NotFoundError` |
| `MissingCredentials` | `MawaqitError` |
| `NoMosqueAround`, `NoMosqueFound` | An empty list |

### Removed

- `fetch_mosque_by_id()`.
