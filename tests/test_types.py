"""The models, on every real response of the spec."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import TypeAdapter

from mawaqit.types import Account, HijriSettings, Mosque, PrayerTimes

from .conftest import EXAMPLES, prayer_times_payload

ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "authLogin": TypeAdapter(Account),
    "mosquesHijriSettings": TypeAdapter(HijriSettings),
    "mosquesPrayerTimes": TypeAdapter(PrayerTimes),
    "mosquesSearch": TypeAdapter(list[Mosque]),
}


@pytest.mark.parametrize(
    "path",
    sorted(EXAMPLES.glob("*/*.json")),
    ids=lambda path: f"{path.parent.name}/{path.stem}",
)
def test_examples_round_trip(path: Any) -> None:
    data = json.loads(path.read_text())
    adapter = ADAPTERS[path.parent.name]

    parsed = adapter.validate_python(data)

    # Nothing is lost: the models dump back to the same JSON.
    dumped = adapter.dump_python(parsed, mode="json", by_alias=True, exclude_unset=True)
    assert dumped == data


def test_every_operation_has_examples() -> None:
    assert {path.name for path in EXAMPLES.iterdir()} <= set(ADAPTERS)


def test_unknown_fields_are_kept() -> None:
    settings = HijriSettings.model_validate(
        {"hijriAdjustment": 1, "hijriDateForceTo30": False, "moonSighted": True}
    )

    assert settings.model_extra == {"moonSighted": True}


def test_snake_case_names() -> None:
    settings = HijriSettings(hijri_adjustment=1, hijri_date_force_to_30=False)

    assert settings.model_dump(by_alias=True) == {
        "hijriAdjustment": 1,
        "hijriDateForceTo30": False,
    }


def test_deprecated_field_warns() -> None:
    prayer_times = PrayerTimes.model_validate(prayer_times_payload())
    assert prayer_times.flash is not None

    with pytest.warns(DeprecationWarning, match="expire"):
        assert prayer_times.flash.expire == 1791072000
