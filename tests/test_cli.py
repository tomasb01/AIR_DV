"""End-to-end tests for CLI output and local exports."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from air_dv.cli import main


class CliTests(unittest.TestCase):
    def test_analyse_writes_all_requested_exports(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "markdown" / "missing_image_alt.md"
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            report_path = output_directory / "report.md"
            ai_view_path = output_directory / "ai-view.md"
            json_path = output_directory / "result.json"
            standard_output = io.StringIO()

            with redirect_stdout(standard_output):
                exit_code = main(
                    [
                        "analyse",
                        str(fixture_path),
                        "--report",
                        str(report_path),
                        "--ai-view",
                        str(ai_view_path),
                        "--json",
                        str(json_path),
                    ]
                )

            serialized = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(exit_code, 0)
            self.assertIn("AIR-DV RESULT — NEEDS ATTENTION", standard_output.getvalue())
            self.assertIn(f"Report: {report_path}", standard_output.getvalue())
            self.assertIn("## Issues to fix", report_path.read_text(encoding="utf-8"))
            self.assertIn("![](architecture.png)", ai_view_path.read_text(encoding="utf-8"))
            self.assertEqual(serialized["findings"][0]["id"], "image-missing-text-equivalent")

    def test_analyse_returns_a_clear_error_for_an_unsupported_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory, "unsupported.pdf")
            source_path.write_text("Not a supported source.", encoding="utf-8")
            standard_error = io.StringIO()
            with redirect_stderr(standard_error):
                exit_code = main(["analyse", str(source_path)])

        self.assertEqual(exit_code, 2)
        self.assertIn("Unsupported source format '.pdf'", standard_error.getvalue())

    def test_analyse_returns_a_clear_error_for_a_missing_source(self) -> None:
        standard_error = io.StringIO()
        with redirect_stderr(standard_error):
            exit_code = main(["analyse", "missing.md"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Source file does not exist", standard_error.getvalue())
