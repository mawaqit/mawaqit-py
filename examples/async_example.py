"""Async usage example for the MAWAQIT client."""

import asyncio
import os

from mawaqit import AsyncMawaqitClient


async def main() -> None:
    # Authenticate with an API token, or with username/password (basic-auth
    # login is performed lazily on the first authenticated call).
    async with AsyncMawaqitClient(
        token=os.getenv("MAWAQIT_TOKEN"),
        username=os.getenv("MAWAQIT_USERNAME"),
        password=os.getenv("MAWAQIT_PASSWORD"),
    ) as client:
        # v2: search mosques near a location.
        mosques = await client.v2.mosque.search(lat=48.8582, lon=2.2945)
        uuid = mosques[0].uuid

        # v2: prayer times for that mosque.
        prayer_times = await client.v2.mosque.prayer_times(uuid)
        print(prayer_times.times)

        # v3: the same mosque through the v3 namespace.
        times = await client.v3.mosque.times(uuid)
        print(times.shuruq)


if __name__ == "__main__":
    asyncio.run(main())
