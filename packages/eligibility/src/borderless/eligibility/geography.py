"""Immutable reviewed identities and exact aliases; no I/O or text extraction."""

import re
from dataclasses import dataclass

from borderless.domain import CountryCode, PolicyVersion, Value, require_text

from ._geographic_data import COUNTRY_ROWS, REGION_MEMBERS


def _alias(value: str) -> str:
    return " ".join(value.split()).casefold()


@dataclass(frozen=True, slots=True)
class CountryIdentity(Value):
    code: CountryCode
    alpha3: str
    name: str
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if not re.fullmatch("[A-Z]{3}", self.alpha3):
            raise ValueError("Expected an ISO alpha-3 identity")
        for value in (self.name, *self.aliases):
            require_text(value)


@dataclass(frozen=True, slots=True)
class GeographicRegion(Value):
    identity: str
    aliases: tuple[str, ...]
    members: tuple[CountryCode, ...]

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for value in (self.identity, *self.aliases):
            require_text(value)
        if not self.aliases or not self.members:
            raise ValueError("Region requires aliases and members")
        if len(set(self.members)) != len(self.members):
            raise ValueError("Duplicate region member")


@dataclass(frozen=True, slots=True)
class GeographicReference(Value):
    version: PolicyVersion
    countries: tuple[CountryIdentity, ...]
    regions: tuple[GeographicRegion, ...]
    worldwide_aliases: tuple[str, ...]

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        codes = [country.code for country in self.countries]
        alpha3 = [country.alpha3 for country in self.countries]
        regions = [region.identity for region in self.regions]
        if (
            not codes
            or len(set(codes)) != len(codes)
            or len(set(alpha3)) != len(alpha3)
        ):
            raise ValueError("Duplicate or missing country identities")
        if len(set(regions)) != len(regions) or set(regions) & {
            *alpha3,
            *(c.value for c in codes),
            "worldwide",
        }:
            raise ValueError("Duplicate or conflicting region identities")
        if any(not set(region.members) <= set(codes) for region in self.regions):
            raise ValueError("Unknown region member")
        aliases = [alias for alias, _ in self._aliases()]
        if not self.worldwide_aliases or len(set(aliases)) != len(aliases):
            raise ValueError("Missing worldwide aliases or geographic alias collision")
        for alias in aliases:
            require_text(alias)

    def _aliases(self) -> tuple[tuple[str, str], ...]:
        countries = tuple(
            (_alias(alias), country.code.value)
            for country in self.countries
            for alias in (
                country.code.value,
                country.alpha3,
                country.name,
                *country.aliases,
            )
        )
        regions = tuple(
            (_alias(alias), region.identity)
            for region in self.regions
            for alias in region.aliases
        )
        return (
            countries
            + regions
            + tuple((_alias(alias), "worldwide") for alias in self.worldwide_aliases)
        )

    def resolve(self, alias: str) -> str | None:
        """Resolve an entire extracted value; never match a substring of job text."""
        return dict(self._aliases()).get(_alias(alias))


_REGION_ALIASES = {
    "south-america": ("South America",),
    "latam": ("LATAM", "Latin America", "Latin America and the Caribbean"),
    "americas": ("Americas", "the Americas"),
}
GEOGRAPHIC_REFERENCE = GeographicReference(
    version=PolicyVersion("1.0.0"),
    countries=tuple(
        CountryIdentity(
            CountryCode(code), alpha3, name, ("Bolivia",) if code == "BO" else ()
        )
        for code, alpha3, name in COUNTRY_ROWS
    ),
    regions=tuple(
        GeographicRegion(
            identity,
            _REGION_ALIASES[identity],
            tuple(CountryCode(code) for code in members),
        )
        for identity, members in REGION_MEMBERS
    ),
    worldwide_aliases=("worldwide", "global", "anywhere in the world"),
)
