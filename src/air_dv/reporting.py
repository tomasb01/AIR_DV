"""Readable terminal and Markdown renderers for AIR-DV analysis results."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from air_dv.models import AnalysisResult, Finding, Severity, SourceLocation
from air_dv.remediation import suggested_change


@dataclass(frozen=True)
class CheckOutcome:
    """A user-facing result for one group of deterministic checks."""

    name: str
    status: str
    finding_count: int = 0


_CHECKS = (
    ("Extraction", {"document-extraction-failed"}, {"md", "docx", "pdf", "xlsx"}),
    (
        "Document structure",
        {"missing-semantic-headings", "section-exceeds-recommended-length"},
        {"md", "docx", "pdf"},
    ),
    (
        "Visual text alternatives",
        {
            "image-missing-text-equivalent",
            "image-text-equivalent-may-be-insufficient",
            "object-text-equivalent-could-not-be-verified",
            "word-visual-objects-unavailable-to-text-only-ingestion",
            "pdf-visual-objects-unavailable-to-text-only-ingestion",
        },
        {"md", "docx", "pdf"},
    ),
    ("PDF extraction quality", {"pdf-ocr-quality-could-not-be-verified"}, {"pdf"}),
    ("External references", {"external-reference-without-local-summary"}, {"md", "docx", "pdf"}),
    (
        "Excel table context",
        {
            "excel-table-missing-sheet-context",
            "excel-table-has-no-detectable-purpose",
            "excel-row-exceeds-recommended-density",
        },
        {"xlsx"},
    ),
)
_MAX_EVIDENCE_CHARACTERS = 280


def render_markdown_report(result: AnalysisResult) -> str:
    """Render a compact, actionable Markdown analysis report."""

    counts = _finding_counts(result.findings)
    outcomes = check_outcomes(result)
    lines = [
        "# AIR-DV result",
        "",
        f"## Overall status: {_overall_status(result)}",
        "",
        _status_explanation(result),
        "",
        "## Document scanned",
        "",
        f"- **File:** `{result.document.filename}`",
        f"- **Format:** `{_format_name(result.document.file_type)}`",
        f"- **Extraction:** {'Successful' if result.document.extraction_succeeded else 'Failed'}",
        f"- **Issues found:** {len(result.findings)} "
        f"({counts[Severity.CRITICAL]} critical, {counts[Severity.WARNING]} warning, "
        f"{counts[Severity.INFO]} info)",
        f"- **Checks passed:** {sum(outcome.status == 'Passed' for outcome in outcomes)}",
    ]
    if result.document.extraction_notes:
        lines.extend(["- **Extraction notes:**", *[f"  - {note}" for note in result.document.extraction_notes]])

    lines.extend(["", "## Check overview", "", "| Check | Result |", "| --- | --- |"])
    lines.extend(f"| {outcome.name} | {_markdown_check_result(outcome)} |" for outcome in outcomes)
    lines.extend(["", "## Main next step", "", _main_next_step(result)])
    lines.extend(["", "## Issues to fix", ""])
    if not result.findings:
        lines.append("No deterministic AI-readiness issues were identified.")
    else:
        for number, finding in enumerate(result.findings, start=1):
            lines.extend(_render_markdown_finding(number, finding))

    lines.extend(
        [
            "",
            "## Scope of locations",
            "",
            "Locations identify original Markdown lines, Word paragraphs, PDF pages, and Excel "
            "sheets/cell ranges when AIR-DV can map the extracted block back to its source. A Word "
            "page number is not reported because a DOCX file does not store stable pagination.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_terminal_summary(result: AnalysisResult, saved_exports: Iterable[str] = ()) -> str:
    """Render the same actionable hierarchy in a terminal-friendly form."""

    counts = _finding_counts(result.findings)
    outcomes = check_outcomes(result)
    lines = [
        f"AIR-DV RESULT — {_overall_status(result)}",
        "",
        f"Document: {result.document.filename}",
        f"Format: {_format_name(result.document.file_type)}",
        f"Extraction: {'Successful' if result.document.extraction_succeeded else 'Failed'}",
        f"Issues: {len(result.findings)} "
        f"({counts[Severity.CRITICAL]} critical, {counts[Severity.WARNING]} warning, "
        f"{counts[Severity.INFO]} info)",
        "",
        "CHECK OVERVIEW",
    ]
    lines.extend(f" {_terminal_marker(outcome)} {outcome.name} — {_terminal_check_result(outcome)}" for outcome in outcomes)
    lines.extend(["", "MAIN NEXT STEP", f" {_main_next_step(result)}", "", "ISSUES TO FIX"])
    if not result.findings:
        lines.append(" No deterministic AI-readiness issues were identified.")
    else:
        for number, finding in enumerate(result.findings, start=1):
            lines.extend(
                [
                    f" {number}. {finding.title} [{finding.severity.value.upper()}]",
                    f"    Where: {_format_location(finding.evidence.location)}",
                    f"    Owner: {_owner_name(finding)}",
                    f"    Why: {finding.why_it_matters}",
                    f"    Change: {suggested_change(finding)}",
                    f"    Evidence: {_one_line_evidence(finding.evidence.excerpt)}",
                ]
            )

    exports = list(saved_exports)
    if exports:
        lines.extend(["", "SAVED EXPORTS", *[f" - {export}" for export in exports]])
    return "\n".join(lines)


def check_outcomes(result: AnalysisResult) -> list[CheckOutcome]:
    """Summarize passed, flagged, and non-applicable checks for a result."""

    finding_ids = [finding.id for finding in result.findings]
    outcomes = []
    for name, related_ids, supported_formats in _CHECKS:
        if result.document.file_type not in supported_formats:
            outcomes.append(CheckOutcome(name, "Not assessed"))
            continue
        count = sum(finding_id in related_ids for finding_id in finding_ids)
        outcomes.append(CheckOutcome(name, "Passed" if count == 0 else "Needs attention", count))
    return outcomes


def _render_markdown_finding(number: int, finding: Finding) -> list[str]:
    return [
        f"### {number}. {finding.title}",
        "",
        f"- **Status:** `{finding.severity.value}`",
        f"- **Owner:** {_owner_name(finding)}",
        f"- **Where:** {_format_location(finding.evidence.location)}",
        f"- **Why it matters:** {finding.why_it_matters}",
        f"- **Recommended approach:** {finding.recommendation}",
        f"- **Suggested change for this document:** {suggested_change(finding)}",
        "",
        "**Evidence**",
        "```text",
        _short_evidence(finding.evidence.excerpt),
        "```",
        "",
    ]


def _finding_counts(findings: list[Finding]) -> Counter[Severity]:
    return Counter(finding.severity for finding in findings)


def _overall_status(result: AnalysisResult) -> str:
    if not result.document.extraction_succeeded:
        return "BLOCKED"
    if result.findings:
        return "NEEDS ATTENTION"
    return "READY FOR REVIEW"


def _status_explanation(result: AnalysisResult) -> str:
    status = _overall_status(result)
    if status == "BLOCKED":
        return "The document cannot be assessed until extraction succeeds."
    if status == "NEEDS ATTENTION":
        return "Resolve the issues below before relying on this document as AI input."
    return "No deterministic issues were identified. Review the AI view before production use."


def _main_next_step(result: AnalysisResult) -> str:
    if not result.findings:
        return "Review the normalized AI view and confirm that the extracted content is complete."
    finding = next(
        (item for item in result.findings if item.severity is Severity.CRITICAL), result.findings[0]
    )
    return f"{finding.title}: {suggested_change(finding)}"


def _markdown_check_result(outcome: CheckOutcome) -> str:
    if outcome.status == "Needs attention":
        return f"Needs attention ({outcome.finding_count})"
    return outcome.status


def _terminal_marker(outcome: CheckOutcome) -> str:
    return {"Passed": "✓", "Needs attention": "!", "Not assessed": "–"}[outcome.status]


def _terminal_check_result(outcome: CheckOutcome) -> str:
    if outcome.status == "Needs attention":
        return f"{outcome.finding_count} issue(s)"
    return outcome.status


def _format_location(location: SourceLocation) -> str:
    parts = [location.label]
    if location.paragraph_index:
        parts.append(f"paragraph: {location.paragraph_index}")
    if location.page_number:
        parts.append(f"page: {location.page_number}")
    if location.sheet_name:
        parts.append(f"sheet: {location.sheet_name}")
    if location.cell_range:
        parts.append(f"cells: {location.cell_range}")
    if location.line_start:
        line_range = str(location.line_start)
        if location.line_end and location.line_end != location.line_start:
            line_range = f"{line_range}-{location.line_end}"
        parts.append(f"line: {line_range}")
    return ", ".join(parts)


def _short_evidence(excerpt: str) -> str:
    excerpt = excerpt.strip()
    if len(excerpt) <= _MAX_EVIDENCE_CHARACTERS:
        return excerpt
    return excerpt[:_MAX_EVIDENCE_CHARACTERS].rstrip() + "…"


def _one_line_evidence(excerpt: str) -> str:
    return " ".join(_short_evidence(excerpt).splitlines())


def _format_name(file_type: str) -> str:
    return {"md": "Markdown (.md)", "docx": "Word (.docx)", "pdf": "PDF (.pdf)", "xlsx": "Excel (.xlsx)"}.get(
        file_type, file_type
    )


def _owner_name(finding: Finding) -> str:
    return {
        "content_owner": "Content owner",
        "platform_team": "Platform team",
        "shared": "Content owner and platform team",
    }[finding.owner.value]
