"""Hand-written async implementation — the single source of truth.

The synchronous client under ``mawaqit/_sync`` is generated from this package
by unasync; never edit the sync tree by hand.
"""

from .client import AsyncMawaqitClient, login

__all__ = ["AsyncMawaqitClient", "login"]
