"""Present so pytest adds the project root to sys.path (mawaqit importable).

Also neutralises the retry backoff sleep in both clients so tests never wait on
real time; retry tests re-patch it locally when they assert on the delays.
"""

import pytest


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _async_noop(_delay: float) -> None:
        return None

    monkeypatch.setattr("mawaqit._async.client.sleep", _async_noop, raising=False)
    monkeypatch.setattr(
        "mawaqit._sync.client.sleep", lambda _delay: None, raising=False
    )
