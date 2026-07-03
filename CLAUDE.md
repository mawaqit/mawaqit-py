# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`mawaqit-py` is the official Python client for the [MAWAQIT](https://mawaqit.net) API. It exposes
two clients with an identical, version-namespaced surface — `AsyncMawaqitClient` (async, for Home
Assistant and other async consumers) and `MawaqitClient` (sync, for scripts/notebooks) — both
exported from the `mawaqit` package. The **v2 and v3** APIs are reachable side by side via
`client.v2.<resource>.<op>()` and `client.v3....`. HTTP is `httpx`; models are `pydantic` v2.

The core principle is **derive, don't duplicate**: types are generated from the real swagger specs
and the sync client is generated from the async source, so nothing is typed or maintained twice.

## Generated code (important)

Two trees are **gitignored** and rebuilt from source — never edit them by hand, and never commit them:

- `mawaqit/_generated/v2.py`, `v3.py` — pydantic models from `swagger/{2.0,3.0}.yml`
  (`datamodel-code-generator`, one module per API version).
- `mawaqit/_sync/` — the sync client, transformed from `mawaqit/_async/` by `unasync`.

Regenerate both with `python scripts/generate.py`. It also runs in the Hatch build hook
(`hatch_build.py`), the CI test/lint jobs, pre-commit, and the pre-push hook. To add an endpoint or a
new API version, edit only `mawaqit/_async/` (and `scripts/generate.py` for a new version), then
regenerate — see the README's "Extending" section.

## Commands

```bash
pip install -e ".[dev]"        # install with all dev/test/codegen extras
python scripts/generate.py     # (re)build the gitignored generated trees — required before tests
pytest                         # full suite; enforces 100% coverage on hand-written code
ruff check . && ruff format --check .
mypy                           # strict; also type-checks the generated sync tree
```

- **Coverage is gated at 100%** (`--cov-fail-under=100` in `pyproject.toml`), scoped to hand-written
  code — both generated trees are omitted. The async client is the source of truth and stays at 100%;
  the sync client is covered by a smoke suite (`tests/test_sync.py`).
- Because coverage is in `addopts`, run a single test with `--no-cov`:
  `pytest tests/test_async_core.py::test_login_success_caches_token --no-cov`.

Build (version comes from the `VERSION` env var, defaulting to `0.0.0` locally):

```bash
VERSION=3.0.0 python -m build      # build hook regenerates + force-includes generated code
```

## Architecture

- **`mawaqit/_async/` is the hand-written source of truth.** `client.py` holds the transport, auth,
  retries, and cached `.v2`/`.v3` namespace properties plus typed request helpers
  (`_get`/`_get_list`/`_get_json`/`_post`/`_delete(cast_to=...)`); `v2.py`/`v3.py` hold resource
  methods that are each one typed line calling a helper. Adding an endpoint is a ~3-line method.
- **Robustness (like OpenAI/Anthropic SDKs).** Generated models subclass `MawaqitModel`
  (`extra="allow"`) and keep only identity fields (`uuid`/`name`/`slug`) required — the
  normalizer in `scripts/generate.py` demotes the rest — so responses never crash on null/absent/new
  fields. `_request` retries transient failures (network + `429/500/502/503/504`) with backoff.
- **Shared, non-transformed modules** live at `mawaqit/` top-level: `config.py` (pydantic-settings,
  `MAWAQIT_API_BASE_URL`), `constants.py` (transport tuning + endpoints, defined once and imported by
  both trees), `exceptions.py`, `_transport.py` (status→exception mapping, `query_params`,
  `API_TOKEN_HEADER` — httpx uses one `Response` type for sync and async, so these are written once),
  `responses.py` (the one inline-schema response model).
- **Authentication is token-only on the client.** The client holds a single API token (as a
  `SecretStr`, from `token=` or `MAWAQIT_TOKEN`), shared by v2 and v3 and sent as the
  `Api-Access-Token` header; an authenticated request with no token raises `MissingCredentials`.
  Exchanging username/password for a token is a **separate concern**: the standalone `login()`
  function (basic-auth against `/2.0/me`, with retry/backoff) never stores the credentials on the
  client. Only 2xx pass; 401→`BadCredentialsException`, 404→`NotFoundException`,
  other→`MawaqitException`.
- **Session ownership (subtle).** The client accepts an injected `httpx.(Async)Client`; ownership is
  tracked with `_close_http = http_client is None`, and `close()` only closes a client we created.
  URLs are built absolutely from the resolved base URL, so an injected client is used untouched —
  this is what lets Home Assistant share one client.
- **Adding a v4** is additive: new spec + `_async/v4.py` + a `.v4` property; nothing existing is rewritten.

## Testing approach

HTTP is mocked with **respx** (no real network). Response payloads for resource tests are built from
each model's own required fields (`tests/_samples.py`). **schemathesis** contract tests
(`tests/test_contract.py`) load the real specs and assert the client's operations, auth header, and
base paths stay aligned — they fail when a regenerated spec drifts from the resources.

## Releases

`.github/workflows/python-publish.yml` runs on a **published GitHub Release**: it validates the tag
(PEP 440 `X.Y.Z` with optional `rc`/`b`/`a`/`.dev`/`.post` suffix), runs the suite, builds with
`VERSION` set to the tag, **smoke-installs the wheel in a clean venv** (guards against a wheel missing
the generated code), then publishes to **PyPI only** via trusted publishing. Pre-release version tags
publish to PyPI too (like Django/pydantic/numpy) — `pip` ignores them unless `--pre` is passed, so
there is no separate TestPyPI channel in the release path. `publish-testpypi.yml` is a **separate,
opt-in packaging rehearsal** (manual `workflow_dispatch`, or the `test-publish` label on a PR) that
stamps a disposable, unique `<base>.dev<run_number>` version and pushes it to TestPyPI with
`skip-existing`. `regenerate-on-api-release.yml` reacts to the backend's `repository_dispatch`
(`api-spec-updated`) to refresh specs, regenerate, run the suite, and open a PR. `test.yml` runs
across Python 3.10–3.14 plus latest stable.
