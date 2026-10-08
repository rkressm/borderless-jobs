"""Governance rejects unsupported permissions and unusable public metadata."""

import json
from dataclasses import replace

import pytest
from borderless.connectors.policy import JOBICY_POLICY, Redistribution, SourcePolicy
from borderless.reporting import SourceAttribution


def test_jobicy_policy_is_versioned_serializable_and_renderer_compatible() -> None:
    policy = SourcePolicy.from_dict(json.loads(json.dumps(JOBICY_POLICY.to_dict())))
    assert policy == JOBICY_POLICY
    assert policy.minimum_poll_interval_seconds == 3600
    assert policy.raw_private and policy.raw_retention_days == 30
    assert policy.canonical_link_required
    attribution = SourceAttribution(
        policy.source_id,
        policy.attribution_name,
        policy.attribution_url,
        policy.attribution_notice,
    )
    assert attribution.name == "Jobicy"


def test_unspecified_redistribution_stays_private() -> None:
    data = JOBICY_POLICY.to_dict()
    del data["redistribution"]
    policy = SourcePolicy(**{field: getattr(JOBICY_POLICY, field) for field in data})
    assert policy.redistribution is Redistribution.PRIVATE


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("policy_url", ""),
        ("policy_url", "javascript:alert(1)"),
        ("reviewed_on", "2026-02-30"),
        ("reviewed_on", "20261008"),
        ("review_notes", ""),
        ("attribution_name", ""),
        ("attribution_notice", ""),
        ("attribution_url", "javascript:alert(1)"),
        ("minimum_poll_interval_seconds", 0),
        ("minimum_poll_interval_seconds", True),
        ("raw_retention_days", 0),
        ("raw_retention_days", 366),
        ("raw_private", False),
        ("canonical_link_required", False),
    ],
)
def test_invalid_policy_rejected(field: str, value: object) -> None:
    data = JOBICY_POLICY.to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        SourcePolicy.from_dict(data)


def test_missing_provenance_and_unknown_permission_rejected() -> None:
    data = JOBICY_POLICY.to_dict()
    del data["policy_url"]
    with pytest.raises(ValueError):
        SourcePolicy.from_dict(data)
    with pytest.raises(ValueError):
        replace(JOBICY_POLICY, redistribution="full_raw")  # type: ignore[arg-type]
