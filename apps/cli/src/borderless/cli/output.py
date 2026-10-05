"""Publish one complete UTF-8 HTML artifact without replacing existing files."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def publish_html(document: str, directory: str) -> None:
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=output,
        prefix=".report-",
    ) as temporary:
        temporary.write(document)
        temporary.flush()
        # Hard-link publication is atomic and fails if the final name already exists,
        # including symlinks. The temporary file is removed on success or failure.
        os.link(temporary.name, output / "report.html")


def discard_broken_stdout() -> None:
    """Prevent a buffered broken pipe from changing the exit code at shutdown."""
    import sys

    try:
        with open(os.devnull, "w", encoding="utf-8") as sink:
            os.dup2(sink.fileno(), sys.stdout.fileno())
    except (AttributeError, OSError):
        # Injected/non-file streams have no usable descriptor to redirect.
        pass
