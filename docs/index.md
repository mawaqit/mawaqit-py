# mawaqit-py

The official Python client for the [MAWAQIT](https://mawaqit.net) API — **async
and sync**, fully typed, with the **v2 and v3** APIs reachable side by side.

- Models are generated from the real swagger specs (`datamodel-code-generator`).
- The sync client is generated from the async one (`unasync`) — no duplicated
  business logic.
- Versions are namespaced: `client.v2.<resource>.<op>()` / `client.v3....`.

## Quickstart

```python
import asyncio
from mawaqit import AsyncMawaqitClient


async def main():
    async with AsyncMawaqitClient(token="YOUR_TOKEN") as client:
        mosques = await client.v2.mosque.search(lat=48.8582, lon=2.2945)
        times = await client.v3.mosque.times(mosques[0].uuid)
        print(times.shuruq)


asyncio.run(main())
```

The synchronous client is identical without `await`:

```python
from mawaqit import MawaqitClient

with MawaqitClient(token="YOUR_TOKEN") as client:
    print(client.v3.mosque.info(uuid))
```

See the [API reference](reference.md) for every resource and model, and
[Extending](extending.md) to add a resource or a new API version.
