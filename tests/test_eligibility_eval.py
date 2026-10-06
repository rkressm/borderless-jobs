from pathlib import Path

import pytest

from scripts.eligibility_eval import evaluate_cases, load_cases

CORPUS = Path("evals/cases/m2-core.jsonl")


def test_protected_smoke_is_deterministic() -> None:
    cases = load_cases(CORPUS)
    assert len(cases) == 12
    assert evaluate_cases(cases) == evaluate_cases(cases)


def test_duplicate_and_invalid_annotations_rejected(tmp_path: Path) -> None:
    first = CORPUS.read_text().splitlines()[0]
    duplicate = tmp_path / "duplicate.jsonl"
    duplicate.write_text(first + "\n" + first + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        load_cases(duplicate)
    duplicate.write_text('{"id": "malformed"}\n')
    with pytest.raises(ValueError):
        load_cases(duplicate)


def test_changed_protected_verdict_fails() -> None:
    from dataclasses import replace

    from borderless.domain import GlobalVerdict

    cases = load_cases(CORPUS)
    changed = replace(cases[0], expected_verdict=GlobalVerdict.NO)
    with pytest.raises(AssertionError, match="Protected"):
        evaluate_cases((changed,))
