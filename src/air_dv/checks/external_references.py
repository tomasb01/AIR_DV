"""Checks for references whose necessary context is outside the document."""

from __future__ import annotations

import re

from air_dv.models import (
    Block,
    BlockType,
    Evidence,
    Finding,
    FindingCategory,
    FindingOwner,
    NormalizedDocument,
    Severity,
)


_EXTERNAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:see|refer to|according to|consult|viz)\s+(?:the\s+)?"
    r"(?:attached?\s+(?:file|document)|attachment|email|e-mail|"
    r"jira(?:\s+(?:ticket|issue))?(?:\s+[A-Z][A-Z0-9]+-\d+)?|"
    r"ticket\s+[A-Z][A-Z0-9]+-\d+|příloh\w*|e-?mail\w*)",
    re.IGNORECASE,
)
_WORD_PATTERN = re.compile(r"\b[\w'-]+\b", re.UNICODE)


class ExternalReferenceCheck:
    """Find explicit external references that have no meaningful local summary."""

    minimum_summary_words = 5

    def run(self, document: NormalizedDocument) -> list[Finding]:
        """Return warnings for self-contained content that depends on an external artifact."""

        if not document.document.extraction_succeeded:
            return []

        findings: list[Finding] = []
        for block in document.blocks:
            if block.type not in {BlockType.PARAGRAPH, BlockType.LIST_ITEM}:
                continue
            match = _EXTERNAL_REFERENCE_PATTERN.search(block.text)
            if match is not None and not self._has_local_summary(block.text, match):
                findings.append(self._finding(block, match.group(0)))
        return findings

    def _has_local_summary(self, text: str, reference_match: re.Match[str]) -> bool:
        """Accept a reference when enough independent explanatory text remains locally."""

        without_reference = text[: reference_match.start()] + text[reference_match.end() :]
        return len(_WORD_PATTERN.findall(without_reference)) >= self.minimum_summary_words

    @staticmethod
    def _finding(block: Block, reference: str) -> Finding:
        return Finding(
            id="external-reference-without-local-summary",
            title="External reference has no local summary",
            severity=Severity.WARNING,
            category=FindingCategory.CONTENT_ISSUE,
            owner=FindingOwner.CONTENT_OWNER,
            why_it_matters=(
                "The instruction depends on information outside this document. An AI system may "
                "not receive the referenced ticket, attachment, or email with this content."
            ),
            recommendation=(
                "Add the decision, rule, or key constraints from the external source here, then "
                "keep the reference as supporting context."
            ),
            evidence=Evidence(excerpt=reference, location=block.location),
        )
