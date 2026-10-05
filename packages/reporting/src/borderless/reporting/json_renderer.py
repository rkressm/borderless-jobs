"""Deterministic UTF-8 JSON text; stream ownership stays with the caller."""

import json
from typing import TextIO

from .contracts import SearchReport


def render_json(report: SearchReport) -> str:
    """Preserve canonical fields and array order, with sorted keys and one newline."""
    return (
        json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )


def write_json(report: SearchReport, stream: TextIO) -> None:
    """Write only report JSON; propagate errors without closing or flushing the stream."""
    stream.write(render_json(report))
