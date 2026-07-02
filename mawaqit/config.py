"""Configuration for the MAWAQIT client.

Settings are read (in order of precedence) from explicit constructor arguments,
then ``MAWAQIT_*`` environment variables / ``.env`` file, then the default base
URL. Point the client at a staging/local deployment with ``MAWAQIT_API_BASE_URL``.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

#: Default API base URL (trailing slash so relative paths join per RFC 3986).
DEFAULT_API_BASE_URL = "https://mawaqit.net/api/"


class MawaqitSettings(BaseSettings):
    """Environment-driven client settings (prefix ``MAWAQIT_``)."""

    model_config = SettingsConfigDict(env_prefix="MAWAQIT_", extra="ignore")

    api_base_url: str | None = None
    token: str | None = None
    username: str | None = None
    password: str | None = None

    def resolve_base_url(self) -> str:
        """Return the effective base URL: explicit override or the default."""
        return self.api_base_url or DEFAULT_API_BASE_URL
