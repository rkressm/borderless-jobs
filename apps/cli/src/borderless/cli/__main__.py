"""Allow the CLI to run as ``python -m borderless.cli``."""

from borderless.cli import main

raise SystemExit(main())
