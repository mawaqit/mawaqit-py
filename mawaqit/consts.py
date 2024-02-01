API_URL_BASE = "https://mawaqit.net/api/2.0"
LOGIN_URL = f"{API_URL_BASE}/me"
SEARCH_MOSQUES_URL = f"{API_URL_BASE}/mosque/search"


def prayer_times_url(mosque_id: int) -> str:
    return f"{API_URL_BASE}/mosque/{mosque_id}/prayer-times"


MAX_LOGIN_RETRIES = 20


class NotAuthenticatedException(Exception):
    pass


class BadCredentialsException(Exception):
    pass


class NoMosqueAround(Exception):
    pass


class MissingCredentials(Exception):
    pass