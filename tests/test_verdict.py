from itertools import product

import pytest
from borderless.domain import DimensionalDecision, GlobalVerdict
from borderless.eligibility import compose_verdict


@pytest.mark.parametrize("dimensions", list(product(DimensionalDecision, repeat=3)))
def test_exhaustive_truth_table(dimensions: tuple[DimensionalDecision, ...]) -> None:
    expected = (
        GlobalVerdict.NO
        if DimensionalDecision.FAIL in dimensions
        else GlobalVerdict.UNCERTAIN
        if DimensionalDecision.UNKNOWN in dimensions
        else GlobalVerdict.YES
    )
    assert compose_verdict(*dimensions) is expected
