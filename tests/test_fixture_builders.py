"""Tests that generated binary fixtures remain valid and purposeful."""

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from air_dv.normalization import ExcelNormalizer
from tests.fixture_builders import create_context_workbook, create_visual_title_only_docx


class FixtureBuilderTests(unittest.TestCase):
    def test_creates_a_reviewable_word_fixture_without_heading_style(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            document_path = Path(temporary_directory, "word_visual_title_only.docx")
            create_visual_title_only_docx(document_path)

            with ZipFile(document_path) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("Visual title only", document_xml)
        self.assertNotIn("w:pStyle", document_xml)

    def test_creates_an_excel_fixture_with_preservable_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workbook_path = Path(temporary_directory, "excel_context_workbook.xlsx")
            create_context_workbook(workbook_path)
            document = ExcelNormalizer().normalize_file(workbook_path)

        self.assertIn("## Sheet: Catalog", document.content)
        self.assertIn("### Table: Essential oils", document.content)
        self.assertIn("## Sheet: Tags", document.content)
