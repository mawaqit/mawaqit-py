API_URL_BASE = "https://mawaqit.net/api"
V2 = "2.0"
V3 = "3.0"
LOGIN_URL = f"{API_URL_BASE}/{V2}/me"
SEARCH_MOSQUES_URL = f"{API_URL_BASE}/{V2}/mosque/search"


def prayer_times_url(mosque_id: int) -> str:
    return f"{API_URL_BASE}/{V2}/mosque/{mosque_id}/prayer-times"


def mosque_data_url(mosque_id: int) -> str:
    return f"{API_URL_BASE}/{V3}/mosque/{mosque_id}/info"


MAX_LOGIN_RETRIES = 20


class NotAuthenticatedException(Exception):
    pass


class BadCredentialsException(Exception):
    pass


class NoMosqueAround(Exception):
    pass


class NoMosqueFound(Exception):
    pass


class NotFoundException(Exception):
    pass


class MissingCredentials(Exception):
    pass
