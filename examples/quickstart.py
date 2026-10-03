"""Find the nearest mosque, then print its prayer times and Hijri date.

Run with:
    MAWAQIT_TOKEN=... uv run examples/quickstart.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from mawaqit import AsyncMawaqitClient, hijri


async def main() -> None:
    """Print the prayer times of today at the mosque nearest to Paris."""
    async with AsyncMawaqitClient() as client:
        mosques = await client.mosques.search(lat=48.8414, lon=2.3557)
        if not mosques:
            print("No mosque found around this position.")
            return
        mosque = mosques[0]
        print(f"{mosque.label}, {mosque.proximity} m away")

        prayer_times = await client.mosques.prayer_times(mosque.uuid)
        settings = await client.mosques.hijri_settings(mosque.uuid)
        now = datetime.now(ZoneInfo(prayer_times.timezone))
        times = prayer_times.calendar[now.month - 1][str(now.day)]
        print(f"{hijri.today(settings, prayer_times.timezone)}: {', '.join(times)}")


if __name__ == "__main__":
    asyncio.run(main())
