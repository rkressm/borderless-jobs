"""Versioned source governance, independent of transports and renderers."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from borderless.domain import PolicyVersion, Value, require_public_url, require_text


class Redistribution(StrEnum):
    PRIVATE = "private"
    ATTRIBUTED_SUMMARIES = "attributed_summaries"


class RemovalRule(StrEnum):
    HIDE_CLOSED_PURGE_ON_REQUEST = "hide_closed_purge_on_request"


@dataclass(frozen=True, slots=True)
class SourcePolicy(Value):
    source_id: str
    version: PolicyVersion
    policy_url: str
    reviewed_on: str
    review_notes: str
    minimum_poll_interval_seconds: int
    attribution_name: str
    attribution_url: str
    attribution_notice: str
    canonical_link_required: bool
    raw_retention_days: int
    removal_rule: RemovalRule
    redistribution: Redistribution = Redistribution.PRIVATE
    raw_private: bool = True

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for text in (
            self.source_id,
            self.review_notes,
            self.attribution_name,
            self.attribution_notice,
        ):
            require_text(text)
        for url in (self.policy_url, self.attribution_url):
            require_public_url(url)
        if date.fromisoformat(self.reviewed_on).isoformat() != self.reviewed_on:
            raise ValueError("Review date must use YYYY-MM-DD")
        if (
            self.minimum_poll_interval_seconds <= 0
            or not 1 <= self.raw_retention_days <= 365
        ):
            raise ValueError("Polling and bounded retention must be positive")
        if not self.raw_private or not self.canonical_link_required:
            raise ValueError("Policy requires private raw data and canonical links")


JOBICY_POLICY = SourcePolicy(
    source_id="jobicy",
    version=PolicyVersion("1.0.0"),
    policy_url="https://jobicy.com/jobs-rss-feed",
    reviewed_on="2026-10-08",
    review_notes=(
        "Fair use permits attributed integrations and summaries. New automated "
        "passes must be at least one hour apart; cursor pages are sequential. "
        "Raw retention duration and deletion SLA are unspecified: private raw "
        "storage for 30 days and purge on request are local safeguards. "
        "Feed absence does not prove closure; use explicit source status."
    ),
    minimum_poll_interval_seconds=3600,
    attribution_name="Jobicy",
    attribution_url="https://jobicy.com",
    attribution_notice="Jobs supplied by Jobicy; follow the original listing for details.",
    canonical_link_required=True,
    raw_retention_days=30,
    removal_rule=RemovalRule.HIDE_CLOSED_PURGE_ON_REQUEST,
    redistribution=Redistribution.ATTRIBUTED_SUMMARIES,
)
