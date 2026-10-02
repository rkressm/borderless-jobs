"""Small typed example for the offline quality loop."""

from borderless.cli import build_parser


def test_parser_has_program_name() -> None:
    assert build_parser().prog == "borderless"
