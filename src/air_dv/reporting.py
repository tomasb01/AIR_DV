"""Presentation-neutral renderers for AIR-DV analysis results."""

from __future__ import annotations

from collections import Counter

from air_dv.models import AnalysisResult, Finding, Severity, SourceLocation


def render_markdown_report(result: AnalysisResult) -> str:
    """Render a portable Markdown report with all findings and their evidence."""

    counts = Counter(finding.severity for finding in result.findings)
    lines = [
        "# AIR-DV analysis report",
        "",
        f"- **File:** `{result.document.filename}`",
        f"- **Type:** `{result.document.file_type}`",
        f"- **Extraction succeeded:** `{result.document.extraction_succeeded}`",
        f"- **Findings:** {len(result.findings)} "
        f"({counts[Severity.CRITICAL]} critical, {counts[Severity.WARNING]} warning, "
        f"{counts[Severity.INFO]} info)",
    ]
    if result.document.extraction_notes:
        lines.extend(["- **Extraction notes:**", *[f"  - {note}" for note in result.document.extraction_notes]])

    lines.extend(["", "## Findings"])
    if not result.findings:
        lines.append("\nNo deterministic AI-readiness findings were identified.")
        return "\n".join(lines) + "\n"

    for finding in result.findings:
        lines.extend(_render_finding(finding))
    return "\n".join(lines) + "\n"


def render_terminal_summary(result: AnalysisResult) -> str:
    """Render a concise, readable command-line summary."""

    counts = Counter(finding.severity for finding in result.findings)
    lines = [
        f"Analysed: {result.document.filename} ({result.document.file_type})",
        f"Extraction succeeded: {result.document.extraction_succeeded}",
        f"Findings: {len(result.findings)} "
        f"({counts[Severity.CRITICAL]} critical, {counts[Severity.WARNING]} warning, "
        f"{counts[Severity.INFO]} info)",
    ]
    lines.extend(
        f"- [{finding.severity.value.upper()}] {finding.title} ({finding.owner.value})"
        for finding in result.findings
    )
    return "\n".join(lines)


def _render_finding(finding: Finding) -> list[str]:
    return [
        "",
        f"### {finding.title}",
        "",
        f"- **Severity:** `{finding.severity.value}`",
        f"- **Category:** `{finding.category.value}`",
        f"- **Owner:** `{finding.owner.value}`",
        f"- **Why it matters:** {finding.why_it_matters}",
        f"- **Recommendation:** {finding.recommendation}",
        f"- **Evidence location:** {_format_location(finding.evidence.location)}",
        "",
        "```text",
        finding.evidence.excerpt,
        "```",
    ]


def _format_location(location: SourceLocation) -> str:
    parts = [location.label]
    if location.sheet_name:
        parts.append(f"sheet: {location.sheet_name}")
    if location.line_start:
        line_range = str(location.line_start)
        if location.line_end and location.line_end != location.line_start:
            line_range = f"{line_range}-{location.line_end}"
        parts.append(f"line: {line_range}")
    return ", ".join(parts)
