"""The models, on every real response of the spec."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from pydantic import TypeAdapter

from mawaqit.types import Account, FlashMessage, HijriSettings, Mosque, PrayerTimes

from .conftest import EXAMPLES, UUID

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
    flash = FlashMessage.model_validate(
        {
            "content": "Iftar at the mosque",
            "uuid": UUID,
            "expire": 1791072000,
            "startDate": "2026-10-01",
            "endDate": "2026-10-04",
            "color": "#d9ad0f",
            "orientation": "ltr",
        }
    )

    assert flash.end_date == date(2026, 10, 4)
    with pytest.warns(DeprecationWarning, match="Use `end_date`"):
        assert flash.expire == 1791072000
