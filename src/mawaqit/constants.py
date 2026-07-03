"""Constants shared across the client: transport tuning and endpoints.

Defined once here (not duplicated in the async/sync trees) and imported by both
the hand-written async client and — unchanged — the unasync-generated sync one.
"""

from __future__ import annotations

#: Default API base URL (trailing slash so relative paths join per RFC 3986).
DEFAULT_API_BASE_URL = "https://mawaqit.net/api/"

#: Default per-request timeout, in seconds, for a client-owned httpx session.
DEFAULT_TIMEOUT = 10.0

#: Default number of retries for a transient request failure.
DEFAULT_MAX_RETRIES = 2

#: Basic-auth login endpoint (relative to the base URL). Login always uses v2.
LOGIN_PATH = "2.0/me"

#: How many times ``login`` retries a *transient* failure before giving up.
#: Bounded so the worst-case backoff stays short (1+2+4+8 = 15s of sleeps).
MAX_LOGIN_RETRIES = 5

#: Response statuses worth retrying (transient server/rate-limit errors).
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

#: Backoff caps, in seconds, for request retries and login retries respectively.
RETRY_BACKOFF_CAP = 8
LOGIN_BACKOFF_CAP = 16
