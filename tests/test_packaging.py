"""Packaging guards that run in CI and the pre-push hook."""

from importlib.resources import files


def test_py_typed_marker_is_shipped():
    """The PEP 561 marker must sit inside the package.

    Without it, downstream projects (e.g. the Home Assistant integration)
    cannot type-check against this library, even though it is fully typed.
    """
    marker = files("mawaqit").joinpath("py.typed")
    assert marker.is_file(), "PEP 561 marker mawaqit/py.typed is missing"
