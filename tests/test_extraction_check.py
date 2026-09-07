"""Tests for visual-content and extraction-status findings."""

import unittest
from pathlib import Path

from air_dv.checks.extraction import ExtractionCheck
from air_dv.models import Block, BlockType, DocumentSummary, NormalizedDocument, SourceLocation
from air_dv.normalization import MarkdownNormalizer


class ExtractionCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.check = ExtractionCheck()
        self.normalizer = MarkdownNormalizer()
        self.fixture_directory = Path(__file__).parent / "fixtures" / "markdown"

    def test_reports_critical_finding_for_an_image_without_alt_text(self) -> None:
        document = self.normalizer.normalize_file(self.fixture_directory / "missing_image_alt.md")

        findings = self.check.run(document)

        self.assertEqual([finding.id for finding in findings], ["image-missing-text-equivalent"])
        self.assertEqual(findings[0].severity.value, "critical")
        self.assertEqual(findings[0].owner.value, "content_owner")

    def test_reports_warning_for_a_generic_image_label(self) -> None:
        document = self.normalizer.normalize_file(self.fixture_directory / "generic_image_alt.md")

        findings = self.check.run(document)

        self.assertEqual(
            [finding.id for finding in findings], ["image-text-equivalent-may-be-insufficient"]
        )

    def test_accepts_a_descriptive_image_label(self) -> None:
        document = self.normalizer.normalize_file(self.fixture_directory / "described_image.md")

        self.assertEqual(self.check.run(document), [])

    def test_reports_visual_object_placeholders_without_guessing_the_root_cause(self) -> None:
        document = self.normalizer.normalize_text("converted.docx", "<!-- image -->\n")

        findings = self.check.run(document)

        self.assertEqual(
            [finding.id for finding in findings], ["object-text-equivalent-could-not-be-verified"]
        )
        self.assertEqual(findings[0].owner.value, "shared")

    def test_reports_failed_extraction_as_a_platform_critical_issue(self) -> None:
        document = NormalizedDocument(
            document=DocumentSummary(
                filename="unreadable.docx",
                file_type="docx",
                extraction_succeeded=False,
                extraction_notes=("Required extractor 'docling' is not available on PATH.",),
            ),
            content="",
            blocks=(),
        )

        findings = self.check.run(document)

        self.assertEqual([finding.id for finding in findings], ["document-extraction-failed"])
        self.assertEqual(findings[0].severity.value, "critical")
        self.assertEqual(findings[0].owner.value, "platform_team")

    def test_aggregates_word_visual_placeholders_with_source_metadata(self) -> None:
        document = NormalizedDocument(
            document=DocumentSummary(
                filename="illustrated.docx",
                file_type="docx",
                extraction_succeeded=True,
                source_metadata=(
                    ("visual_reference_count", "8"),
                    ("unique_media_file_count", "3"),
                ),
            ),
            content="<!-- image -->\n<!-- image -->",
            blocks=(
                Block(
                    type=BlockType.UNSUPPORTED_OBJECT,
                    text="<!-- image -->",
                    location=SourceLocation(label="Word document", paragraph_index=12),
                ),
                Block(
                    type=BlockType.UNSUPPORTED_OBJECT,
                    text="<!-- image -->",
                    location=SourceLocation(label="Word document", paragraph_index=13),
                ),
            ),
        )

        findings = self.check.run(document)

        self.assertEqual(
            [finding.id for finding in findings],
            ["word-visual-objects-unavailable-to-text-only-ingestion"],
        )
        self.assertIn("8 visual reference(s) (3 unique media file(s))", findings[0].why_it_matters)
        self.assertIn("multimodal ingestion pipeline", findings[0].recommendation)
        self.assertEqual(findings[0].evidence.location.paragraph_index, 12)
