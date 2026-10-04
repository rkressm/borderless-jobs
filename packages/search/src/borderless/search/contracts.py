"""Storage-neutral search input and newest-first ordering contracts."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from borderless.domain import CountryCode, GlobalVerdict, Value, require_text


@dataclass(frozen=True, slots=True)
class SearchSpecification(Value):
    role: str
    country: CountryCode
    as_of: datetime
    offset: int
    limit: int
    verdicts: tuple[GlobalVerdict, ...] = ()
    sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        role = re.sub(r"[\s_-]+", "-", self.role.strip().lower())
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", role) or len(role) > 100:
            raise ValueError("Role must be a nonempty ASCII category or phrase")
        object.__setattr__(self, "role", role)
        if self.offset < 0 or not 1 <= self.limit <= 100:
            raise ValueError("Offset must be nonnegative and limit between 1 and 100")
        for source in self.sources:
            if (
                not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source)
                or len(source) > 100
            ):
                raise ValueError("Source filters must use canonical source identifiers")
        if len(set(self.sources)) != len(self.sources) or len(
            set(self.verdicts)
        ) != len(self.verdicts):
            raise ValueError("Duplicate filters are not allowed")
        object.__setattr__(self, "sources", tuple(sorted(self.sources)))
        object.__setattr__(self, "verdicts", tuple(sorted(self.verdicts)))


@dataclass(frozen=True, slots=True)
class ResultOrderKey(Value):
    """Newest publication first; stable unique job ID breaks equal-time ties."""

    published_at: datetime
    job_id: str

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        require_text(self.job_id)

    def sort_key(self) -> tuple[int, str]:
        delta = self.published_at.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
        microseconds = (
            delta.days * 86400 + delta.seconds
        ) * 1_000_000 + delta.microseconds
        return (-microseconds, self.job_id)
