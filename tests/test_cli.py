"""Behavior checks for the command-line help contract."""

import io
import unittest
from contextlib import redirect_stdout

from borderless.cli import main


class CliHelpTests(unittest.TestCase):
    def test_help_exits_successfully_and_names_the_program(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout), self.assertRaises(SystemExit) as exit_context:
            main(["--help"])

        self.assertEqual(exit_context.exception.code, 0)
        self.assertIn("usage: borderless", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
