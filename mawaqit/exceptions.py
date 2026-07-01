"""Exception hierarchy — every error subclasses :class:`MawaqitException`."""


class MawaqitException(Exception):
    """Base exception for all MAWAQIT errors."""


class BadCredentialsException(MawaqitException):
    """Authentication was rejected by the API (HTTP 401)."""


class NotFoundException(MawaqitException):
    """The requested resource does not exist (HTTP 404)."""


class MissingCredentials(MawaqitException):
    """A token or username/password is required but was not provided."""
