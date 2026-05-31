from .consts import API_URL_BASE,V2, V3


def prayer_times_url(mosque_id: int) -> str:
    return f"{API_URL_BASE}/{V2}/mosque/{mosque_id}/prayer-times"


def mosque_data_url(mosque_id: int) -> str:
    return f"{API_URL_BASE}/{V3}/mosque/{mosque_id}/info"


