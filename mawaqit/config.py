"""Multi-environment configuration for the MAWAQIT client.

Settings are read (in order of precedence) from explicit constructor arguments,
then ``MAWAQIT_*`` environment variables / ``.env`` file, then per-environment
defaults. ``MAWAQIT_BASE_URL`` overrides the environment's default host, which is
what staging/local deployments use.
"""

from __future__ import annotations

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Named deployment targets."""

    PRODUCTION = "production"
    STAGING = "staging"
    LOCAL = "local"


#: Default API base URL per environment. Every entry ends with a trailing slash
#: so that relative endpoint paths join correctly (RFC 3986).
ENVIRONMENT_BASE_URLS: dict[Environment, str] = {
    Environment.PRODUCTION: "https://mawaqit.net/api/",
    Environment.STAGING: "https://staging.mawaqit.net/api/",
    Environment.LOCAL: "http://localhost:8000/api/",
}


class MawaqitSettings(BaseSettings):
    """Environment-driven client settings (prefix ``MAWAQIT_``)."""

    model_config = SettingsConfigDict(env_prefix="MAWAQIT_", extra="ignore")

    environment: Environment = Environment.PRODUCTION
    base_url: str | None = None
    token: str | None = None
    username: str | None = None
    password: str | None = None

    def resolve_base_url(self) -> str:
        """Return the effective base URL: explicit override or the env default."""
        return self.base_url or ENVIRONMENT_BASE_URLS[self.environment]
