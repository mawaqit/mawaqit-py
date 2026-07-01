"""Contract tests: the client must stay in sync with the real swagger specs.

These load the checked-in specs with schemathesis and assert the client's
surface matches them. When the backend regenerates a spec (via the cross-repo
dispatch) and it drifts from the hand-written resources, these tests fail —
prompting the resources (and the declaration below) to be updated.
"""

from __future__ import annotations

import pytest
import schemathesis

from mawaqit._transport import API_TOKEN_HEADER

# The (METHOD, path) operations each version's resources implement. This is the
# contract declaration and must mirror mawaqit/_async/v{2,3}.py exactly.
IMPLEMENTED: dict[str, set[tuple[str, str]]] = {
    "2.0": {
        ("GET", "/mosque/search"),
        ("GET", "/mosque/list-uuid"),
        ("GET", "/mosque/{uuid}/prayer-times"),
        ("GET", "/mosque/{uuid}/weather"),
        ("GET", "/mosque/{id}/data"),
        ("GET", "/mosque/map/{countryCode}"),
        ("GET", "/mosque"),
        ("GET", "/hadith/random"),
        ("POST", "/statistic/mosque/{uuid}/favorite"),
        ("DELETE", "/statistic/mosque/{uuid}/favorite"),
        ("GET", "/support"),
        ("GET", "/me"),
    },
    "3.0": {
        ("GET", "/mosque/{uuid}/times"),
        ("GET", "/mosque/{uuid}/info"),
        ("GET", "/mosque/{id}"),
        ("GET", "/mosque/slug/{slug}"),
        ("GET", "/mosque/{uuid}/config"),
        ("GET", "/mosque/{uuid}/announcements"),
        ("GET", "/mosque/{uuid}/flash-message"),
        ("GET", "/mosque/{uuid}/hijri-date"),
        ("GET", "/mosque/{uuid}/messages"),
        ("POST", "/mosque/{uuid}/androidtv-life-status"),
        ("GET", "/statistic/installations"),
    },
}

VERSIONS = list(IMPLEMENTED)


def _load(version: str) -> schemathesis.Schema:
    return schemathesis.openapi.from_path(f"swagger/{version}.yml")


def _spec_operations(schema: schemathesis.Schema) -> set[tuple[str, str]]:
    operations = set()
    for result in schema.get_all_operations():
        operation = result.ok()
        operations.add((operation.method.upper(), operation.path))
    return operations


@pytest.mark.parametrize("version", VERSIONS)
def test_specs_are_loadable(version: str) -> None:
    # A malformed spec (e.g. a bad regeneration) fails here first.
    assert _spec_operations(_load(version))


@pytest.mark.parametrize("version", VERSIONS)
def test_client_implements_exactly_the_spec_operations(version: str) -> None:
    assert _spec_operations(_load(version)) == IMPLEMENTED[version]


@pytest.mark.parametrize("version", VERSIONS)
def test_auth_header_matches_spec(version: str) -> None:
    scheme = _load(version).raw_schema["securityDefinitions"]["APIKeyHeader"]
    assert scheme["in"] == "header"
    assert scheme["name"] == API_TOKEN_HEADER


@pytest.mark.parametrize("version", VERSIONS)
def test_base_path_matches_client_version_prefix(version: str) -> None:
    # The client builds URLs as base_url + "{version}/...", so the spec basePath
    # must be /api/{version}.
    assert _load(version).raw_schema["basePath"] == f"/api/{version}"
