class MawaqitException(Exception):
    """Base exception for all Mawaqit errors."""

class NotAuthenticatedException(MawaqitException):
    pass


class BadCredentialsException(MawaqitException):
    pass


class NoMosqueAround(MawaqitException):
    pass


class NoMosqueFound(MawaqitException):
    pass


class NotFoundException(MawaqitException):
    pass


class MissingCredentials(MawaqitException):
    pass