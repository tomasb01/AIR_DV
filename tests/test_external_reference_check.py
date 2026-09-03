"""Tests for conservative external-reference findings."""

import unittest
from pathlib import Path

from air_dv.checks.external_references import ExternalReferenceCheck
from air_dv.normalization import MarkdownNormalizer


class ExternalReferenceCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.check = ExternalReferenceCheck()
        self.normalizer = MarkdownNormalizer()
        self.fixture_directory = Path(__file__).parent / "fixtures" / "markdown"

    def test_reports_a_jira_reference_without_a_local_summary(self) -> None:
        document = self.normalizer.normalize_file(self.fixture_directory / "external_reference.md")

        findings = self.check.run(document)

        self.assertEqual([finding.id for finding in findings], ["external-reference-without-local-summary"])
        self.assertEqual(findings[0].owner.value, "content_owner")
        self.assertEqual(findings[0].evidence.excerpt, "See Jira ticket SEC-142")

    def test_reports_a_czech_attachment_reference_without_a_local_summary(self) -> None:
        document = self.normalizer.normalize_text("guide.md", "Podrobnosti viz přílohu.\n")

        findings = self.check.run(document)

        self.assertEqual([finding.id for finding in findings], ["external-reference-without-local-summary"])

    def test_accepts_a_reference_when_the_rule_is_summarized_locally(self) -> None:
        document = self.normalizer.normalize_text(
            "guide.md",
            "Production access requires approval from two administrators. See Jira ticket SEC-142.\n",
        )

        self.assertEqual(self.check.run(document), [])

    def test_ignores_non_external_navigation_and_ordinary_mentions(self) -> None:
        document = self.normalizer.normalize_text(
            "guide.md",
            "See the deployment section below for the required steps.\n\n"
            "The Jira migration happened last quarter.\n",
        )

        self.assertEqual(self.check.run(document), [])
