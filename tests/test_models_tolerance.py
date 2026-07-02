"""The generated models must never crash on real-world MAWAQIT payloads.

The spec over-marks fields as required and the API routinely returns them
null/absent, so models keep only identity fields required, everything else
optional, and `extra="allow"` for unknown/future fields.
"""

from __future__ import annotations

from mawaqit._generated import v2, v3


def test_sparse_null_and_unknown_fields_do_not_crash() -> None:
    mosque = v2.Mosque.model_validate(
        {"id": 1, "uuid": "u", "name": "Essunna", "phone": None, "brandNewField": 42}
    )
    assert mosque.uuid == "u"  # identity field stays required -> str, not str | None
    assert mosque.phone is None
    assert mosque.brandNewField == 42  # unknown field kept, not rejected


def test_empty_payload_validates() -> None:
    times = v3.Times.model_validate({})
    assert times.times is None
    assert times.shuruq is None


def test_identity_fields_remain_required() -> None:
    required = {n for n, f in v2.Mosque.model_fields.items() if f.is_required()}
    assert required == {"id", "uuid", "name"}
