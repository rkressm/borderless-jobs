"""A live smoke command cannot access the network without explicit opt-in."""

import pytest

from scripts.jobicy_smoke import main


def test_smoke_requires_live_opt_in() -> None:
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2


def test_smoke_help_is_available_offline(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0
    assert "--live" in capsys.readouterr().out
