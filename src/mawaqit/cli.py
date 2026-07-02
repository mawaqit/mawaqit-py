"""Command-line interface: ``mawaqit-py`` (currently a single ``login`` command).

Hand-written and sync (it drives the generated sync :func:`login`), so it is not
part of the async→sync transform.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from ._sync.client import login
from .config import MawaqitSettings


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``mawaqit-py`` console script."""
    parser = argparse.ArgumentParser(
        prog="mawaqit-py", description="MAWAQIT API command-line tools."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "login", help="Log in with your MAWAQIT credentials and print an API token."
    )
    args = parser.parse_args(argv)
    if args.command == "login":  # the only command for now
        _login()


def _login() -> None:
    """Resolve credentials (env first, prompt for what's missing) and print a token.

    The base URL comes from ``MAWAQIT_API_BASE_URL`` (or the default) and is never
    prompted; ``MAWAQIT_USERNAME`` / ``MAWAQIT_PASSWORD`` skip their prompt when
    set. Prompts go to stderr so stdout carries only the token, e.g.
    ``export MAWAQIT_TOKEN=$(mawaqit-py login)``.
    """
    settings = MawaqitSettings()
    username = settings.username or _prompt("MAWAQIT username: ")
    password = (
        settings.password.get_secret_value()
        if settings.password is not None
        else getpass.getpass("MAWAQIT password: ", stream=sys.stderr)
    )
    print(f"\nYour token for {settings.api_base_url} is:", file=sys.stderr, flush=True)
    print(login(username, password))


def _prompt(label: str) -> str:
    """Read a line, writing the label to stderr (keeps stdout token-only)."""
    print(label, end="", file=sys.stderr, flush=True)
    return input()
