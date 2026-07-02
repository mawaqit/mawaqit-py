# MAWAQIT Python Library

‏السلام عليكم ورحمة الله وبركاته

Official Python client for the [MAWAQIT](https://mawaqit.net) API. Async **and**
sync, fully typed, with the **v2 and v3** APIs reachable side by side. The models
are generated from the real swagger specs and the sync client is generated from
the async one, so nothing is typed or maintained twice.

## Installation

```bash
pip install mawaqit
```

## Getting an API token

1. Create a free account on [mawaqit.net](https://mawaqit.net).
2. Pass `token=...` if you already have one, or pass `username=`/`password=` and
   the client performs a basic-auth login lazily on the first authenticated call.

## Usage

The surface is namespaced by API version: `client.v2.<resource>.<operation>()`
and `client.v3.<resource>.<operation>()`. The async and sync clients are
identical apart from `await`.

```python
import asyncio
from mawaqit import AsyncMawaqitClient


async def main():
    async with AsyncMawaqitClient(token="YOUR_TOKEN") as client:
        # v2: search mosques near a location
        mosques = await client.v2.mosque.search(lat=48.8582, lon=2.2945)
        uuid = mosques[0].uuid

        # v2 and v3, same client, same token
        prayer_times = await client.v2.mosque.prayer_times(uuid)
        times = await client.v3.mosque.times(uuid)
        print(prayer_times.times, times.shuruq)


asyncio.run(main())
```

Synchronous, same API without `await`:

```python
from mawaqit import MawaqitClient

with MawaqitClient(token="YOUR_TOKEN") as client:
    mosques = client.v2.mosque.search(word="paris")
    print(client.v3.mosque.info(mosques[0].uuid))
```

Results are pydantic models (e.g. `client.v3.mosque.times(uuid)` returns a
`Times`), so attributes are typed and validated.

### Robustness

Built to behave like the best-in-class SDKs:

- **Never crashes on real data.** Models allow unknown/future fields
  (`extra="allow"`) and treat everything except identity fields (`id`, `uuid`,
  `name`) as optional, because the API routinely returns fields null or absent.
- **Automatic retries** with exponential backoff on transient failures (network
  errors and `429/500/502/503/504`); tune with `max_retries=`.

### Configuration

Environment and credentials can come from `MAWAQIT_*` environment variables (via
`pydantic-settings`) instead of constructor arguments:

```bash
export MAWAQIT_TOKEN=...            # or MAWAQIT_USERNAME / MAWAQIT_PASSWORD
export MAWAQIT_ENVIRONMENT=staging  # production (default) | staging | local
export MAWAQIT_BASE_URL=...         # override the environment's base URL
```

Home Assistant and other consumers can inject a shared client:
`AsyncMawaqitClient(http_client=my_httpx_client)` — an injected client is never
closed by this library.

## Exceptions

All inherit from `MawaqitException`: `BadCredentialsException` (401),
`NotFoundException` (404), `MissingCredentials` (no token/credentials provided).

## Documentation

Full API reference and guides are built with MkDocs:

```bash
pip install -e ".[docs,codegen]"
python scripts/generate.py   # docs introspect the generated code
mkdocs serve
```

## Contributing

Generated code (`mawaqit/_generated`, `mawaqit/_sync`) is **not** committed; it is
rebuilt from the swagger specs and the async source:

```bash
pip install -e ".[dev]"
pre-commit install            # regenerates code + lints on commit
python scripts/generate.py    # or regenerate manually
ruff check . && ruff format --check .
mypy
pytest                        # must stay at 100% coverage
```

### Adding a new Resource or operation

Everything hand-written lives in `mawaqit/_async`:

1. Add the method to the relevant resource class in `mawaqit/_async/v2.py` or
   `v3.py` (or add a new `SomethingResource` class and expose it on the
   `AsyncV2` / `AsyncV3` namespace). It is a single typed line via a request
   helper (`_get` / `_get_list` / `_get_json` / `_post` / `_delete`):

   ```python
   async def config(self, uuid: str) -> Config:
       return await self._client._get(f"3.0/mosque/{uuid}/config", cast_to=Config)
   ```
2. Run `python scripts/generate.py` to regenerate the sync mirror.
3. Add the `(METHOD, path)` to `IMPLEMENTED` in `tests/test_contract.py` and a
   respx test in `tests/test_resources_async.py`.

You never write sync code by hand — unasync derives it.

### Adding a new API version (e.g. v4)

1. Drop the spec at `swagger/4.0.yml` and add `"4.0": "v4"` to `VERSIONS` in
   `scripts/generate.py`.
2. Add `mawaqit/_async/v4.py` with an `AsyncV4` namespace (model it on `v3.py`),
   and expose a cached `v4` property on the client in `mawaqit/_async/client.py`.
3. Add `"AsyncV4": "SyncV4"` to `SYNC_REPLACEMENTS` in `scripts/generate.py`.
4. Regenerate, then add `"4.0"` to `IMPLEMENTED` and tests.

No existing code is rewritten — versions are additive.

## License

Released under the license in the [LICENSE](LICENSE) file.

## Questions

Reach us at [support@mawaqit.net](mailto:support@mawaqit.net). May Allah reward you!
