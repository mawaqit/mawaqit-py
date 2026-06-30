# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`mawaqit-py` is the official async Python client for the [MAWAQIT](https://mawaqit.net) API. The entire public surface is a single class, `AsyncMawaqitClient`, exported from the `mawaqit` package. It fetches mosque information and prayer times over HTTP using `aiohttp`.

## Commands

Tests (configuration lives in `pytest.ini`, `asyncio_mode = auto`):

```bash
pip install -r requirements-test.txt
pytest                       # full suite; enforces 100% coverage
```

- **Coverage is gated at 100%** via `--cov-fail-under=100` in `pytest.ini`. Any new code path must be covered or `pytest` fails.
- Because coverage is in `addopts`, running a subset trips the gate. To run a single test, disable coverage for that run:

  ```bash
  pytest tests/test_client.py::test_keyword_success --no-cov
  ```

Lint, format, and type checks (configured in `ruff.toml` and `mypy.ini`):

```bash
ruff check . && ruff format --check .   # lint + format (format owns line length)
mypy                                     # types (scoped to mawaqit/)
```

Build / editable install — `setup.py` reads the version from the **`VERSION` environment variable** and raises if it is unset, so it is required:

```bash
VERSION=0.0.0 pip install -e .      # local dev install
VERSION=1.2.3 python -m build       # build sdist/wheel
```

## Architecture

- **`mawaqit/mawaqit_async.py` is the library.** `AsyncMawaqitClient` holds all HTTP logic; the other modules are thin support: `consts.py` (API URLs, `MAX_LOGIN_RETRIES`), `utils.py` (URL builders), `exceptions.py` (every error subclasses `MawaqitException`).
- **`mawaqit/mawaqit.py` is an unfinished synchronous stub** — not exported, not used. Do not build on it.
- **Authentication.** Data calls need an API token. `get_api_token()` returns an existing token or calls `login()` (HTTP Basic auth against `LOGIN_URL`), retrying transient `MawaqitException`s up to `MAX_LOGIN_RETRIES` with exponential backoff. The token is then sent as the `Api-Access-Token` header on subsequent requests.
- **Status-to-exception mapping** is centralized in `_raise_for_status`: 401 → `BadCredentialsException`, 404 → `NotFoundException`, any other non-200 → `MawaqitException`.
- **Mosque selection.** `fetch_prayer_times()` uses `client.mosque` (a uuid) when set, otherwise falls back to the nearest mosque from the client's `latitude`/`longitude`. Mosques are discovered with `all_mosques_neighborhood()` (coordinates) or `fetch_mosques_by_keyword()`.
- **Session ownership (subtle, important).** The client accepts an injected `aiohttp.ClientSession`. Ownership is tracked with `_close_session = session is None`, and `close()` only closes a session the client created itself — an injected session is caller-owned and never closed. Keep the session assignment and this flag consistent (both keyed on `is None`). This is what lets consumers such as the Home Assistant integration share a single session.

## Testing approach

HTTP is tested by **injecting a fake session** (`FakeSession` / `FakeResponse` in `tests/test_client.py`), not by mocking `aiohttp` at the transport level — `aioresponses` is incompatible with aiohttp 3.14+. New request-level tests should follow this fake-session pattern. Async tests are plain `async def` (pytest-asyncio auto mode).

## Releases

Publishing is driven by `.github/workflows/python-publish.yml` on a **published GitHub Release**: it validates the tag format, runs the test suite (the release is gated on tests passing), builds with `VERSION` set to the release tag, and publishes to TestPyPI and PyPI via trusted publishing. The test workflow (`.github/workflows/test.yml`) runs the suite across Python 3.10–3.14 plus the latest stable (`3.x`).
