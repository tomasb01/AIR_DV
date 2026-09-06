"""Tests for transparent PDF extraction-quality findings."""

import unittest

from air_dv.checks.extraction import ExtractionCheck
from air_dv.checks.pdf_quality import PdfExtractionQualityCheck
from air_dv.models import Block, BlockType, DocumentSummary, NormalizedDocument, SourceLocation


class PdfExtractionQualityCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = NormalizedDocument(
            document=DocumentSummary(
                filename="report.pdf",
                file_type="pdf",
                extraction_succeeded=True,
                source_metadata=(
                    ("page_count", "17"),
                    ("visual_placeholder_count", "3"),
                    ("ocr_warning_count", "2"),
                ),
            ),
            content="Text\n<!-- image -->\n<!-- image -->\n<!-- image -->",
            blocks=tuple(
                Block(
                    type=BlockType.UNSUPPORTED_OBJECT,
                    text="<!-- image -->",
                    location=SourceLocation(label="PDF document", page_number=4),
                )
                for _ in range(3)
            ),
        )

    def test_reports_ocr_warnings_as_a_single_platform_finding(self) -> None:
        findings = PdfExtractionQualityCheck().run(self.document)

        self.assertEqual([finding.id for finding in findings], ["pdf-ocr-quality-could-not-be-verified"])
        self.assertEqual(findings[0].owner.value, "platform_team")
        self.assertIn("2 OCR warning", findings[0].why_it_matters)

    def test_aggregates_pdf_visual_placeholders_into_one_finding(self) -> None:
        findings = ExtractionCheck().run(self.document)

        self.assertEqual(
            [finding.id for finding in findings], ["pdf-visual-objects-could-not-be-verified"]
        )
        self.assertIn("3 visual-object placeholder", findings[0].why_it_matters)
        self.assertEqual(findings[0].evidence.location.page_number, 4)
