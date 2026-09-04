"""Tests that generated binary fixtures remain valid and purposeful."""

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from air_dv.models import BlockType
from air_dv.normalization import ExcelNormalizer, MarkdownNormalizer, WordSourceLocator
from tests.fixture_builders import create_context_workbook, create_visual_title_only_docx


class FixtureBuilderTests(unittest.TestCase):
    fixture_directory = Path(__file__).parent / "fixtures"

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

    def test_committed_word_fixture_is_a_valid_visual_title_example(self) -> None:
        document_path = self.fixture_directory / "word" / "visual_title_only.docx"

        with ZipFile(document_path) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("Visual title only", document_xml)
        self.assertNotIn("w:pStyle", document_xml)

    def test_committed_excel_fixture_preserves_workbook_context(self) -> None:
        workbook_path = self.fixture_directory / "excel" / "context_workbook.xlsx"

        document = ExcelNormalizer().normalize_file(workbook_path)

        self.assertTrue(document.document.extraction_succeeded)
        self.assertIn("## Sheet: Catalog", document.content)
        self.assertIn("### Table: Essential oils", document.content)
        self.assertIn("## Sheet: Tags", document.content)

    def test_maps_word_fixture_text_to_its_original_paragraphs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            document_path = Path(temporary_directory, "word_visual_title_only.docx")
            create_visual_title_only_docx(document_path)
            blocks = MarkdownNormalizer().normalize_text(
                "word_visual_title_only.docx",
                "**Visual title only**\n\nBody content without a semantic heading style.\n",
            ).blocks
            located_blocks = WordSourceLocator().attach_locations(document_path, blocks)

        self.assertEqual([block.type for block in located_blocks], [BlockType.PARAGRAPH] * 2)
        self.assertEqual([block.location.label for block in located_blocks], ["Word document"] * 2)
        self.assertEqual([block.location.paragraph_index for block in located_blocks], [1, 2])
