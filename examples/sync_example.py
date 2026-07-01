"""Synchronous usage example for the MAWAQIT client.

Identical to examples/async_example.py, just without async/await — the sync
client is generated from the async one by unasync.
"""

import os

from mawaqit import MawaqitClient


def main() -> None:
    with MawaqitClient(
        token=os.getenv("MAWAQIT_TOKEN"),
        username=os.getenv("MAWAQIT_USERNAME"),
        password=os.getenv("MAWAQIT_PASSWORD"),
    ) as client:
        mosques = client.v2.mosque.search(lat=48.8582, lon=2.2945)
        uuid = mosques[0].uuid

        prayer_times = client.v2.mosque.prayer_times(uuid)
        print(prayer_times.times)

        times = client.v3.mosque.times(uuid)
        print(times.shuruq)


if __name__ == "__main__":
    main()
