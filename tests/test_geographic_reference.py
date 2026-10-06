"""Reviewed reference invariants and strict alias resolution."""

from dataclasses import replace

import pytest
from borderless.domain import CountryCode, PolicyVersion
from borderless.eligibility import GEOGRAPHIC_REFERENCE, GeographicReference


def test_versioned_reference_round_trip() -> None:
    reference = GEOGRAPHIC_REFERENCE
    assert reference.version == PolicyVersion("1.0.0")
    assert GeographicReference.from_dict(reference.to_dict()) == reference
    assert len(reference.countries) == 248
    assert reference.resolve(" Bolivia ") == "BO"
    assert reference.resolve("bol") == "BO"
    assert reference.resolve("bO") == "BO"


@pytest.mark.parametrize(
    ("alias", "region", "count"),
    [
        ("South America", "south-america", 16),
        ("LATAM", "latam", 52),
        ("Latin America", "latam", 52),
        ("Americas", "americas", 57),
    ],
)
def test_reviewed_membership(alias: str, region: str, count: int) -> None:
    reference = GEOGRAPHIC_REFERENCE
    assert reference.resolve(alias.swapcase()) == region
    members = next(
        item.members for item in reference.regions if item.identity == region
    )
    assert CountryCode("BO") in members
    assert len(members) == count
    assert (CountryCode("US") in members) == (region == "americas")


@pytest.mark.parametrize(
    "alias",
    [
        "Americas-friendly",
        "worldwide-ish",
        "remote",
        "Bolivian",
        "xLATAM",
        "South American",
        "anywhere-ish",
        "ZZ",
    ],
)
def test_alias_boundaries(alias: str) -> None:
    assert GEOGRAPHIC_REFERENCE.resolve(alias) is None


@pytest.mark.parametrize("alias", ["worldwide", "global", "anywhere in the world"])
def test_worldwide_aliases(alias: str) -> None:
    assert GEOGRAPHIC_REFERENCE.resolve(alias.upper()) == "worldwide"


def test_reference_rejects_duplicate_identities_and_alias_collisions() -> None:
    reference = GEOGRAPHIC_REFERENCE
    with pytest.raises(ValueError, match="Duplicate"):
        replace(reference, countries=(*reference.countries, reference.countries[0]))
    region = replace(reference.regions[0], aliases=("Bolivia",))
    with pytest.raises(ValueError, match="alias"):
        replace(reference, regions=(region, *reference.regions[1:]))
    with pytest.raises(ValueError, match="member"):
        replace(reference, regions=(replace(region, members=(CountryCode("ZZ"),)),))
    with pytest.raises(ValueError, match="Duplicate"):
        replace(reference, regions=(reference.regions[0], reference.regions[0]))


def test_reference_rejects_invalid_schema_and_versions() -> None:
    data = GEOGRAPHIC_REFERENCE.to_dict()
    data["extra"] = True
    with pytest.raises(ValueError):
        GeographicReference.from_dict(data)
    with pytest.raises(ValueError):
        replace(GEOGRAPHIC_REFERENCE, version=PolicyVersion("next"))
