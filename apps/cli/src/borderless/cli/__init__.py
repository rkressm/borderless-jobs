"""Thin offline command adapter over search, report building, and rendering."""

import json
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import NoReturn

from borderless.domain import (
    CountryCode,
    GlobalVerdict,
    PolicyVersion,
    SchemaVersion,
    require_text,
)
from borderless.reporting import ReportBuilder, render_html, write_json
from borderless.search import SearchSpecification, SyntheticSearchAdapter

from .output import discard_broken_stdout, publish_html


class _InvalidArguments(ValueError):
    pass


class _Parser(ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse messages can echo arbitrary arguments, including credentials.
        raise _InvalidArguments("Invalid command arguments; use --help.")


def build_parser() -> ArgumentParser:
    """Describe the synthetic offline search adapter without application decisions."""
    parser = _Parser(
        prog="borderless",
        allow_abbrev=False,
        description="Inspect evidence-backed eligibility using synthetic offline jobs.",
    )
    search = parser.add_subparsers(dest="command", required=True).add_parser(
        "search",
        help="Search synthetic jobs and generate a report",
        allow_abbrev=False,
    )
    search.add_argument("--country", required=True, help="Two-letter candidate country")
    search.add_argument(
        "--role", required=True, help="Role category, e.g. data-engineer"
    )
    search.add_argument("--format", choices=("json", "html"), default="json")
    search.add_argument(
        "--output", help="HTML directory; creates report.html exclusively"
    )
    search.add_argument(
        "--as-of", help="Aware ISO-8601 instant; defaults to current UTC time"
    )
    search.add_argument("--offset", type=int, default=0)
    search.add_argument("--limit", type=int, default=10)
    search.add_argument(
        "--source", action="append", default=[], help="Repeatable source filter"
    )
    search.add_argument(
        "--verdict", action="append", default=[], choices=tuple(GlobalVerdict)
    )
    return parser


def _specification(options: Namespace, instant: datetime) -> SearchSpecification:
    if (options.format == "html") != (options.output is not None):
        raise _InvalidArguments("HTML requires --output; JSON is written to stdout.")
    try:
        if options.output is not None:
            require_text(options.output)
        as_of = (
            datetime.fromisoformat(options.as_of)
            if options.as_of is not None
            else instant
        )
        specification = SearchSpecification(
            options.role,
            CountryCode(options.country),
            as_of,
            options.offset,
            options.limit,
            tuple(GlobalVerdict(value) for value in options.verdict),
            tuple(options.source),
        )
        if as_of > instant:
            raise ValueError("Future as-of instant")
        return specification
    except ValueError:
        raise _InvalidArguments("Invalid search filters or as-of timestamp.") from None


def _execute(options: Namespace, instant: datetime) -> None:
    specification = _specification(options, instant)
    report = ReportBuilder(
        SyntheticSearchAdapter(),
        lambda: instant,
        PolicyVersion("1.0.0"),
        SchemaVersion("1.0.0"),
    ).build(specification)
    if options.format == "json":
        write_json(report, sys.stdout)
        sys.stdout.flush()
    else:
        publish_html(render_html(report), options.output)


def _error(code: str, message: str, exit_code: int) -> int:
    sys.stderr.write(json.dumps({"error": {"code": code, "message": message}}) + "\n")
    return exit_code


def main(
    argv: Sequence[str] | None = None,
    *,
    clock: Callable[[], datetime] | None = None,
) -> int:
    """Return documented exit codes; help retains argparse's successful SystemExit."""
    try:
        options = build_parser().parse_args(argv)
        instant = clock() if clock is not None else datetime.now(UTC)
        _execute(options, instant)
    except _InvalidArguments as error:
        return _error("invalid_arguments", str(error), 2)
    except BrokenPipeError:
        discard_broken_stdout()
        return _error("output_error", "Unable to write report output.", 3)
    except OSError:
        return _error("output_error", "Unable to write report output.", 3)
    except ValueError:
        return _error("report_error", "Unable to build or render a valid report.", 4)
    return 0


__all__ = ["build_parser", "main"]
