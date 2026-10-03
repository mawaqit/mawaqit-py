"""The public interface of the package."""

from __future__ import annotations

import re

import mawaqit


def test_public_names() -> None:
    for name in mawaqit.__all__:
        assert getattr(mawaqit, name) is not None


def test_version() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+((a|b|rc)\d+)?", mawaqit.__version__)
