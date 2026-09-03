"""Tests for the public analysis-result contract."""

import json
import unittest

from air_dv.models import (
    AnalysisResult,
    DocumentSummary,
    Evidence,
    Finding,
    FindingCategory,
    FindingOwner,
    Severity,
    SourceLocation,
)


class SourceLocationTests(unittest.TestCase):
    def test_rejects_reversed_line_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "line_end cannot be earlier"):
            SourceLocation(label="Normalized content", line_start=8, line_end=7)


class AnalysisResultTests(unittest.TestCase):
    def test_serializes_to_json_and_filters_findings(self) -> None:
        finding = Finding(
            id="missing-semantic-headings",
            title="Sections are not marked with semantic headings",
            severity=Severity.WARNING,
            category=FindingCategory.CONTENT_ISSUE,
            owner=FindingOwner.CONTENT_OWNER,
            why_it_matters="Section context may be lost when the document is split.",
            recommendation="Use Heading 1–3 styles in Word.",
            evidence=Evidence(
                excerpt="**Plant signatures**",
                location=SourceLocation(label="Normalized content", line_start=12),
            ),
        )
        result = AnalysisResult(
            document=DocumentSummary(
                filename="plants.docx",
                file_type="docx",
                extraction_succeeded=True,
            ),
            normalized_content="**Plant signatures**",
            findings=[finding],
        )

        serialized = result.to_dict()

        self.assertEqual(serialized["findings"][0]["severity"], "warning")
        self.assertEqual(serialized["findings"][0]["owner"], "content_owner")
        self.assertEqual(result.findings_by_severity(Severity.WARNING), [finding])
        json.dumps(serialized)

