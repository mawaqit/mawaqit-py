"""Tests for the aiohttp session lifecycle of AsyncMawaqitClient.

The client must only close a session it created itself. A session provided by
the caller (an "injected" session) is owned by the caller and must never be
closed by the client.
"""

import asyncio

import aiohttp

from mawaqit import AsyncMawaqitClient


def test_injected_session_is_not_closed():
    """A caller-provided session is left open after close()."""

    async def _run():
        session = aiohttp.ClientSession()
        try:
            client = AsyncMawaqitClient(session=session)
            await client.close()
            assert session.closed is False
        finally:
            await session.close()

    asyncio.run(_run())


def test_internal_session_is_closed():
    """A session created by the client is closed by close()."""

    async def _run():
        client = AsyncMawaqitClient()
        internal_session = client.session
        await client.close()
        assert internal_session.closed is True

    asyncio.run(_run())


def test_context_manager_does_not_close_injected_session():
    """Exiting the async context manager does not close an injected session."""

    async def _run():
        session = aiohttp.ClientSession()
        try:
            async with AsyncMawaqitClient(session=session):
                pass
            assert session.closed is False
        finally:
            await session.close()

    asyncio.run(_run())
