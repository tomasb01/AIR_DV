"""Tests for readable AIR-DV result presentation."""

import unittest
from pathlib import Path

from air_dv.analysis import analyse_file
from air_dv.reporting import render_markdown_report, render_terminal_summary


class ReportingTests(unittest.TestCase):
    def test_renders_an_actionable_warning_with_check_overview(self) -> None:
        result = analyse_file(Path(__file__).parent / "fixtures" / "markdown" / "missing_image_alt.md")

        terminal = render_terminal_summary(result, ["Report: report.md"])
        report = render_markdown_report(result)

        self.assertIn("AIR-DV RESULT — NEEDS ATTENTION", terminal)
        self.assertIn("CHECK OVERVIEW", terminal)
        self.assertIn("Where: Source Markdown, line: 3", terminal)
        self.assertIn("Evidence: ![](architecture.png)", terminal)
        self.assertIn("SAVED EXPORTS", terminal)
        self.assertIn("## Overall status: NEEDS ATTENTION", report)
        self.assertIn("## Main next step", report)
        self.assertIn("### 1. Image has no text equivalent", report)

    def test_renders_a_review_status_when_checks_pass(self) -> None:
        result = analyse_file(Path(__file__).parent / "fixtures" / "markdown" / "described_image.md")

        terminal = render_terminal_summary(result)

        self.assertIn("AIR-DV RESULT — READY FOR REVIEW", terminal)
        self.assertIn("No deterministic AI-readiness issues were identified.", terminal)
