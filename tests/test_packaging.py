"""Packaging guards that run in CI and the pre-push hook."""

from pathlib import Path

import mawaqit


def test_py_typed_marker_is_shipped():
    """The PEP 561 marker must sit inside the package.

    Without it, downstream projects (e.g. the Home Assistant integration)
    cannot type-check against this library, even though it is fully typed.
    """
    package_dir = Path(mawaqit.__file__).resolve().parent
    assert (package_dir / "py.typed").is_file()
