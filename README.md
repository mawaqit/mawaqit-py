# MAWAQIT Python Library

‏السلام عليكم ورحمة الله وبركاته

Official async Python client for the [MAWAQIT](https://mawaqit.net) API — fetch mosque information and prayer times.

## Getting an API token

1. Create a free account on [mawaqit.net](https://mawaqit.net).
2. The client logs in with your email and password and obtains an API token for you (`get_api_token()`).
3. Already have a token? Pass it directly with `token=...` and skip the login.

## Installation

```bash
pip install mawaqit
```

## Usage

```python
import asyncio
from mawaqit import AsyncMawaqitClient


async def main():
    client = AsyncMawaqitClient(
        username=USERNAME, password=PASSWORD, latitude=LATITUDE, longitude=LONGITUDE
    )
    await client.get_api_token()

    # Find mosques near the coordinates, then pick one:
    mosques = await client.all_mosques_neighborhood()
    client.mosque = mosques[0]["uuid"]
    # Or search by keyword: await client.fetch_mosques_by_keyword("paris")

    print(await client.fetch_prayer_times())
    await client.close()


asyncio.run(main())
```

Full example: [examples/async_example.py](examples/async_example.py).

## Exceptions

All inherit from `MawaqitException`:

- `BadCredentialsException` — wrong login credentials.
- `MissingCredentials` — required credentials not provided.
- `NoMosqueAround` — no mosque near the given location.
- `NoMosqueFound` — no mosque matches the keyword.
- `NotFoundException` — resource not found.

## Contributing

[Fork](https://github.com/mawaqit/mawaqit-py/fork) the repo and open a pull request, or open an [issue](https://github.com/mawaqit/mawaqit-py/issues/new).

```bash
pip install -r requirements-test.txt   # test dependencies
pytest                                  # full suite (must stay at 100% coverage)
pytest tests/test_client.py::test_keyword_success --no-cov   # a single test
```

Enable the pre-push hook to run tests automatically before each push:

```bash
git config core.hooksPath .githooks
```

HTTP is tested with an injected fake session (see `tests/test_client.py`), not by mocking aiohttp — follow that pattern for new tests.

## License

Released under the license in the [LICENSE](LICENSE) file.

## Questions

Reach us at [support@mawaqit.net](mailto:support@mawaqit.net). May Allah reward you!
