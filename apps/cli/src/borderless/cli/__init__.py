"""Command-line adapter for Borderless Jobs."""

from argparse import ArgumentParser
from collections.abc import Sequence


def build_parser() -> ArgumentParser:
    """Build the root parser without coupling it to application behavior."""
    return ArgumentParser(
        prog="borderless",
        description="Inspect evidence-backed remote-job eligibility.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Parse root options; subcommands arrive with the walking skeleton."""
    build_parser().parse_args(argv)
    return 0


__all__ = ["build_parser", "main"]
