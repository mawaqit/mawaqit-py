"""Print the API token of a MAWAQIT account.

Only the token goes to stdout, so it can be exported:
    export MAWAQIT_TOKEN=$(uv run examples/get_token.py)

The email and password come from MAWAQIT_EMAIL and MAWAQIT_PASSWORD, or are
prompted for, without echoing the password.
"""

from __future__ import annotations

import os
import sys
from getpass import getpass

from mawaqit import AuthenticationError, MawaqitClient, MawaqitError


def main() -> None:
    """Log in and print the token."""
    email = os.environ.get("MAWAQIT_EMAIL") or input("MAWAQIT email: ").strip()
    password = os.environ.get("MAWAQIT_PASSWORD") or getpass("MAWAQIT password: ")
    with MawaqitClient() as client:
        account = client.auth.login(email=email, password=password)
    print(account.api_access_token)


if __name__ == "__main__":
    try:
        main()
    except AuthenticationError:
        sys.exit("Wrong email or password.")
    except MawaqitError as err:
        sys.exit(f"Could not log in: {err}")
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nAborted.")
