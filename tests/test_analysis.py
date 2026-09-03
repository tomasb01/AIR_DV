"""Tests for the public analysis orchestration."""

import tempfile
import unittest
from pathlib import Path

from air_dv.analysis import UnsupportedSourceFormatError, analyse_file


class AnalysisTests(unittest.TestCase):
    def test_analyses_markdown_and_runs_all_relevant_checks(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "markdown" / "missing_image_alt.md"

        result = analyse_file(fixture_path)

        self.assertEqual(result.document.filename, "missing_image_alt.md")
        self.assertEqual([finding.id for finding in result.findings], ["image-missing-text-equivalent"])
        self.assertIn("![](architecture.png)", result.normalized_content)

    def test_rejects_an_unsupported_source_format(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory, "notes.txt")
            source_path.write_text("Notes", encoding="utf-8")

            with self.assertRaisesRegex(UnsupportedSourceFormatError, "Unsupported source format '.txt'"):
                analyse_file(source_path)
