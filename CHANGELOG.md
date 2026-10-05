# Changelog

All notable changes to this library. It follows
[Semantic Versioning](https://semver.org).

## Unreleased

### Added

- `mawaqit.prayer_times`: `prayer_day()`, the prayers of a day as datetimes, with
  their iqama, Imsak and Jumu'a; `next_prayer()`; and `night()`, the thirds of the
  night. Like `@mawaqit/sdk/prayer-times` in TypeScript.

## 2.0.0 - 2026-10-05

The first stable release of the new library, with no changes since 2.0.0b5.
The changes since 1.x are those of the betas below.

## 2.0.0b5 - 2026-10-04

### Added

- `client.mosques.get()`: the UUID, name and type of a mosque from its ID. Homes
  are found this way: `client.mosques.search()` does not return them.

## 2.0.0b4 - 2026-10-04

### Added

- `client.mosques.flash_message()`: the flash message of a mosque, or `None`,
  from a much smaller response than `client.mosques.prayer_times()`.

## 2.0.0b3 - 2026-10-04

### Changed

- `HijriMonth.JUMADA_AL_AKHIRA`, `DHU_AL_QADA` and `DHU_AL_HIJJA` are renamed
  `JUMADA_AL_AKHIRAH`, `DHU_AL_QIDAH` and `DHU_AL_HIJJAH`, like in the MAWAQIT
  apps, and their labels follow.

## 2.0.0b2 - 2026-10-04

### Changed

- Build with hatchling 1.32.4 or newer.

## 2.0.0b1 - 2026-10-04

A new library, generated from the OpenAPI description of the API.

### Added

- `MawaqitClient`, a sync client with the same methods as the async one.
- Typed models for every response, with the documentation of each field.
- `mawaqit.hijri`, to compute the Hijri date of a mosque like MAWAQIT does.
- `client.mosques.hijri_settings()` and `client.mosques.config()`.
- Retries with backoff for network errors, timeouts and temporary errors.
- `with_options()`, to change the token, timeout or retries of a client.
- Debug logs of every response, without the token.

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
