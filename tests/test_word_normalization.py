"""Tests for Word normalization through the Docling command-line extractor."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from air_dv.models import BlockType
from air_dv.normalization import DoclingWordNormalizer


class DoclingWordNormalizerTests(unittest.TestCase):
    def test_normalizes_docling_output_and_keeps_docx_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory, "guide.docx")
            source_path.touch()

            def fake_run(command: list[str], **_: object) -> object:
                output_directory = Path(command[command.index("--output") + 1])
                Path(output_directory, "guide.md").write_text(
                    "# Guide\n\nA normalized paragraph.\n", encoding="utf-8"
                )
                return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            with (
                patch("air_dv.normalization.shutil.which", return_value="/usr/local/bin/docling"),
                patch("air_dv.normalization.subprocess.run", side_effect=fake_run),
            ):
                document = DoclingWordNormalizer().normalize_file(source_path)

        self.assertTrue(document.document.extraction_succeeded)
        self.assertEqual(document.document.file_type, "docx")
        self.assertEqual(document.document.filename, "guide.docx")
        self.assertEqual(document.document.extraction_notes, ("Extracted with Docling.",))
        self.assertEqual([block.type for block in document.blocks], [BlockType.HEADING, BlockType.PARAGRAPH])
        self.assertEqual(document.blocks[0].location.label, "Normalized Word content")

    def test_returns_an_explicit_failure_when_docling_is_unavailable(self) -> None:
        with patch("air_dv.normalization.shutil.which", return_value=None):
            document = DoclingWordNormalizer().normalize_file("guide.docx")

        self.assertFalse(document.document.extraction_succeeded)
        self.assertEqual(document.content, "")
        self.assertIn("not available", document.document.extraction_notes[0])

    def test_rejects_non_word_files(self) -> None:
        with self.assertRaisesRegex(ValueError, "only accepts .docx"):
            DoclingWordNormalizer().normalize_file("guide.md")
