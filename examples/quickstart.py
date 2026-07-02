"""Quickstart: search a mosque, then read its v2 and v3 prayer times.

Auth resolves from the environment:
  MAWAQIT_TOKEN - read directly by AsyncMawaqitClient()

No token yet? Get one without writing any code:
    export MAWAQIT_TOKEN=$(mawaqit-py login)

Run with:
    MAWAQIT_TOKEN=... python examples/quickstart.py
"""

from __future__ import annotations

import asyncio

from mawaqit import AsyncMawaqitClient, MawaqitException


async def main() -> None:
    # AsyncMawaqitClient() with no args reads MAWAQIT_TOKEN from the environment.
    # If you only have credentials, exchange them for a token first:
    #     from mawaqit import async_login
    #     token = await async_login("me@example.com", "password")
    #     client = AsyncMawaqitClient(token=token)
    async with AsyncMawaqitClient() as client:
        # v2: search mosques near a location (Paris, here)
        mosques = await client.v2.mosque.search(lat=48.8582, lon=2.2945)
        if not mosques:
            print("No mosque found near that location.")
            return
        mosque = mosques[0]
        print(f"Nearest mosque: {mosque.name} ({mosque.uuid})")

        # v2 and v3 share the same client/token; call either by uuid.
        prayer_times = await client.v2.mosque.prayer_times(mosque.uuid)
        times = await client.v3.mosque.times(mosque.uuid)
        print("v2 prayer_times:", prayer_times.times)
        print("v3 times.shuruq:", times.shuruq)

        # Results are pydantic models with snake_case attributes
        # (mosque.women_space, not mosque["womenSpace"]).
        info = await client.v3.mosque.info(mosque.uuid)
        print("Women's space available:", info.women_space)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except MawaqitException as exc:
        raise SystemExit(f"MAWAQIT API error: {exc}") from exc
