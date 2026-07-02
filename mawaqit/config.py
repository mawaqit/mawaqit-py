"""Configuration for the MAWAQIT client.

Settings resolve in order of precedence: explicit constructor arguments, then
``MAWAQIT_*`` environment variables / a ``.env`` file, then the defaults here.
Point the client at a staging/local deployment with ``MAWAQIT_API_BASE_URL``.
"""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import DEFAULT_API_BASE_URL


class MawaqitSettings(BaseSettings):
    """Environment-driven client settings (prefix ``MAWAQIT_``).

    Credentials are wrapped in :class:`~pydantic.SecretStr` so they never leak
    into logs or ``repr`` output; read them back with ``.get_secret_value()``.
    """

    model_config = SettingsConfigDict(env_prefix="MAWAQIT_", extra="ignore")

    api_base_url: str = DEFAULT_API_BASE_URL
    token: SecretStr | None = None
    username: str | None = None
    password: SecretStr | None = None

    @field_validator("api_base_url")
    @classmethod
    def _ensure_trailing_slash(cls, value: str) -> str:
        """Normalise the base URL so relative paths join per RFC 3986."""
        return value if value.endswith("/") else value + "/"

    @classmethod
    def load(cls, **overrides: Any) -> MawaqitSettings:
        """Build settings from ``overrides`` layered on env vars and defaults.

        Only non-``None`` overrides are forwarded, so an omitted constructor
        argument falls back to the ``MAWAQIT_*`` environment instead of
        shadowing it with an explicit ``None``.
        """
        provided = {key: value for key, value in overrides.items() if value is not None}
        return cls(**provided)
