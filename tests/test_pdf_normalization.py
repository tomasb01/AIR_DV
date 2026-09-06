"""Tests for PDF normalization with placeholder images and source-page locations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from air_dv.models import BlockType
from air_dv.normalization import DoclingPdfNormalizer


class _FakePage:
    def __init__(self, text: str) -> None:
        self.text = text

    def extract_text(self) -> str:
        return self.text


class _FakePdfReader:
    def __init__(self, _: object) -> None:
        self.pages = [_FakePage("Report title\nThe first source paragraph."), _FakePage("Second page.")]


class DoclingPdfNormalizerTests(unittest.TestCase):
    def test_normalizes_pdf_with_placeholders_and_page_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory, "report.pdf")
            source_path.touch()

            def fake_run(command: list[str], **_: object) -> object:
                output_directory = Path(command[command.index("--output") + 1])
                Path(output_directory, "report.md").write_text(
                    "# Report title\n\nThe first source paragraph.\n\n<!-- image -->\n\n## Second page\n",
                    encoding="utf-8",
                )
                return type(
                    "Completed",
                    (),
                    {"returncode": 0, "stdout": "RapidOCR returned empty result", "stderr": ""},
                )()

            with (
                patch("air_dv.normalization.shutil.which", return_value="/usr/local/bin/docling"),
                patch("air_dv.normalization.subprocess.run", side_effect=fake_run),
                patch("air_dv.normalization.PdfReader", _FakePdfReader),
            ):
                document = DoclingPdfNormalizer().normalize_file(source_path)

        self.assertTrue(document.document.extraction_succeeded)
        self.assertEqual(document.document.file_type, "pdf")
        self.assertEqual(
            dict(document.document.source_metadata),
            {"page_count": "2", "visual_placeholder_count": "1", "ocr_warning_count": "1"},
        )
        self.assertEqual(
            [block.type for block in document.blocks],
            [BlockType.HEADING, BlockType.PARAGRAPH, BlockType.UNSUPPORTED_OBJECT, BlockType.HEADING],
        )
        self.assertTrue(all(block.location.label == "PDF document" for block in document.blocks))
        self.assertEqual([block.location.page_number for block in document.blocks], [1, 1, 1, 2])

    def test_returns_explicit_failure_when_docling_is_unavailable(self) -> None:
        with patch("air_dv.normalization.shutil.which", return_value=None):
            document = DoclingPdfNormalizer().normalize_file("report.pdf")

        self.assertFalse(document.document.extraction_succeeded)
        self.assertIn("not available", document.document.extraction_notes[0])

    def test_rejects_non_pdf_files(self) -> None:
        with self.assertRaisesRegex(ValueError, "only accepts .pdf"):
            DoclingPdfNormalizer().normalize_file("report.docx")
