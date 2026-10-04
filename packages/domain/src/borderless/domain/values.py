"""Pure immutable contracts and strict JSON-compatible value conversion."""

import re
from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum
from typing import Any, Self, get_args, get_origin, get_type_hints


def _decode(annotation: Any, data: Any, *, strict: bool = False) -> Any:
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is tuple:
        if (
            not isinstance(data, tuple if strict else (list, tuple))
            or len(data) > 10000
        ):
            raise ValueError("Expected a bounded sequence")
        return tuple(_decode(args[0], item, strict=strict) for item in data)
    if origin is type(str | None):
        if data is None and type(None) in args:
            return None
        return _decode(
            next(arg for arg in args if arg is not type(None)), data, strict=strict
        )
    if isinstance(annotation, type) and issubclass(annotation, Value):
        if type(data) is annotation:
            return data
        if strict:
            raise ValueError("Expected the declared immutable value type")
        return annotation.from_dict(data)
    if isinstance(annotation, type) and issubclass(annotation, StrEnum):
        if strict and type(data) is not annotation:
            raise ValueError("Expected the declared enum type")
        return annotation(data)
    if annotation is datetime:
        if strict and not isinstance(data, datetime):
            raise ValueError("Expected a datetime value")
        value = datetime.fromisoformat(data) if isinstance(data, str) else data
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError("Expected a timezone-aware datetime")
        return value
    if type(data) is not annotation:
        raise ValueError(f"Expected {annotation}")
    if isinstance(data, str) and len(data) > 1_000_000:
        raise ValueError("Text exceeds contract limit")
    return data


def _encode(value: Any) -> Any:
    if isinstance(value, Value):
        return value.to_dict()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_encode(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class Value:
    """Base for immutable, strictly typed, JSON-compatible contracts."""

    def __post_init__(self) -> None:
        for name, annotation in get_type_hints(type(self)).items():
            value = getattr(self, name)
            _decode(annotation, value, strict=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            field.name: _encode(getattr(self, field.name)) for field in fields(self)
        }

    @classmethod
    def from_dict(cls, data: Any) -> Self:
        if not isinstance(data, dict) or set(data) != {f.name for f in fields(cls)}:
            raise ValueError("Contract fields must match exactly")
        hints = get_type_hints(cls)
        try:
            return cls(
                **{name: _decode(hints[name], value) for name, value in data.items()}
            )
        except (TypeError, KeyError) as error:
            raise ValueError("Invalid contract data") from error


def require_text(value: str) -> None:
    """Require nonempty text without control characters."""
    if not value.strip() or any(ord(char) < 32 for char in value):
        raise ValueError("Expected nonempty text without control characters")


def require_public_url(value: str) -> None:
    """Accept absolute HTTP(S) source links without credentials or whitespace."""
    if not re.fullmatch(
        r"https?://[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?::[0-9]{1,5})?(?:[/?#][^\s\\]*)?",
        value,
    ):
        raise ValueError("Expected an absolute HTTP(S) URL without credentials")
    if any(ord(char) < 32 for char in value):
        raise ValueError("URL contains control characters")


@dataclass(frozen=True, slots=True)
class CountryCode(Value):
    """ISO alpha-2 syntax; reviewed country membership is owned by D01."""

    value: str

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        value = self.value.strip().upper()
        if not re.fullmatch("[A-Z]{2}", value) or not self.value.strip().isascii():
            raise ValueError("Expected a two-letter ASCII country code")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class PolicyVersion(Value):
    value: str

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if not re.fullmatch(
            r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", self.value
        ):
            raise ValueError("Expected a major.minor.patch version")


@dataclass(frozen=True, slots=True)
class SchemaVersion(PolicyVersion):
    """Separate type for schema evolution, independent of decision policy."""


class DimensionalDecision(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class GlobalVerdict(StrEnum):
    YES = "YES"
    NO = "NO"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True, slots=True)
class Evidence(Value):
    job_version_id: str
    normalization_version: str
    start: int
    end: int
    quote: str
    source_url: str

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        require_text(self.job_version_id)
        require_text(self.normalization_version)
        require_public_url(self.source_url)
        if (
            self.start < 0
            or self.end <= self.start
            or self.end - self.start != len(self.quote)
        ):
            raise ValueError("Evidence requires a nonempty half-open character span")
        if len(self.quote) > 2000:
            raise ValueError("Evidence excerpt exceeds 2000 characters")

    def verify(self, canonical_text: str) -> None:
        """Verify against the exact immutable normalized version, never raw HTML."""
        if canonical_text[self.start : self.end] != self.quote:
            raise ValueError("Evidence does not match canonical text")


@dataclass(frozen=True, slots=True)
class FactProvenance(Value):
    method: str
    provider: str
    extractor_version: str
    schema_version: SchemaVersion
    prompt_version: str | None = None
    model: str | None = None
    model_revision: str | None = None
    runtime_version: str | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if self.method not in {"parser", "model", "synthetic", "reviewed"}:
            raise ValueError("Unknown extraction method")
        for value in (self.provider, self.extractor_version, *self.warnings):
            require_text(value)
        for optional_value in (
            self.prompt_version,
            self.model,
            self.model_revision,
            self.runtime_version,
        ):
            if optional_value is not None:
                require_text(optional_value)
        if (self.model is None) != (self.model_revision is None):
            raise ValueError("Model and immutable revision must be paired")
        if self.method == "model" and (
            self.model is None
            or self.prompt_version is None
            or self.runtime_version is None
        ):
            raise ValueError(
                "Model extraction requires model, prompt, and runtime provenance"
            )
