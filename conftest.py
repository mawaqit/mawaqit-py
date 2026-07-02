"""Present so pytest adds the project root to sys.path (mawaqit importable).

Also neutralises the retry backoff sleep in both clients so tests never wait on
real time, and clears any MAWAQIT_* env vars so settings are hermetic regardless
of the developer's environment.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def _clear_mawaqit_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("MAWAQIT_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _async_noop(_delay: float) -> None:
        return None

    monkeypatch.setattr("mawaqit._async.client.sleep", _async_noop, raising=False)
    monkeypatch.setattr(
        "mawaqit._sync.client.sleep", lambda _delay: None, raising=False
    )
