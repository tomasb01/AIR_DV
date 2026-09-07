"""Tests for deterministic semantic-heading and section-length checks."""

import unittest
from dataclasses import replace

from air_dv.checks.structure import StructureCheck, StructureCheckConfig
from air_dv.normalization import MarkdownNormalizer
from air_dv.remediation import suggested_change


class StructureCheckTests(unittest.TestCase):
    def test_reports_missing_headings_for_a_long_document(self) -> None:
        content = "\n\n".join(["A paragraph without a semantic heading." for _ in range(12)])
        document = MarkdownNormalizer().normalize_text("legacy.md", content)

        findings = StructureCheck(
            StructureCheckConfig(minimum_words_without_headings=20)
        ).run(document)

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.id, "missing-semantic-headings")
        self.assertEqual(finding.owner.value, "content_owner")
        self.assertIn("Heading 1–3", finding.recommendation)

    def test_does_not_report_missing_headings_for_short_content(self) -> None:
        document = MarkdownNormalizer().normalize_text("note.md", "A short note without a heading.")

        findings = StructureCheck().run(document)

        self.assertEqual(findings, [])

    def test_reports_an_overlong_section_with_its_heading_as_evidence(self) -> None:
        content = "# Long section\n\n" + " ".join(["word"] * 30)
        document = MarkdownNormalizer().normalize_text("guide.md", content)

        findings = StructureCheck(StructureCheckConfig(maximum_words_per_section=20)).run(document)

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.id, "section-exceeds-recommended-length")
        self.assertEqual(finding.evidence.excerpt, "Long section")
        self.assertIn("approximately 30 words", finding.why_it_matters)
        change = suggested_change(finding)
        self.assertIn("Heading 2 for a new major topic", change)
        self.assertIn("Heading 3 only for a subtopic", change)
        self.assertIn("Do not nest unrelated topics", change)

    def test_does_not_report_section_length_when_extraction_failed(self) -> None:
        document = MarkdownNormalizer().normalize_text("guide.md", "# Heading\n\nText")
        failed_document = document.__class__(
            document=document.document.__class__(
                filename=document.document.filename,
                file_type=document.document.file_type,
                extraction_succeeded=False,
            ),
            content=document.content,
            blocks=document.blocks,
        )

        self.assertEqual(StructureCheck().run(failed_document), [])

    def test_defers_excel_density_to_the_specialized_excel_check(self) -> None:
        document = MarkdownNormalizer().normalize_text("workbook.md", "# Sheet: Data\n\n" + "word " * 30)
        excel_document = replace(document, document=replace(document.document, file_type="xlsx"))

        findings = StructureCheck(StructureCheckConfig(maximum_words_per_section=20)).run(excel_document)

        self.assertEqual(findings, [])
