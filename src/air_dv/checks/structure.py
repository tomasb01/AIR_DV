"""Checks for document structure that must survive AI chunking."""

from __future__ import annotations

from dataclasses import dataclass

from air_dv.models import (
    Block,
    BlockType,
    Evidence,
    Finding,
    FindingCategory,
    FindingOwner,
    NormalizedDocument,
    Severity,
    SourceLocation,
)


@dataclass(frozen=True)
class StructureCheckConfig:
    """Conservative thresholds for deterministic structure findings."""

    minimum_words_without_headings: int = 200
    maximum_words_per_section: int = 800


class StructureCheck:
    """Find missing semantic headings and sections that are too long for reliable chunking."""

    def __init__(self, config: StructureCheckConfig | None = None) -> None:
        self.config = config or StructureCheckConfig()

    def run(self, document: NormalizedDocument) -> list[Finding]:
        """Return actionable structure findings for a normalized document."""

        if not document.document.extraction_succeeded:
            return []
        if document.document.file_type == "xlsx":
            return []

        findings: list[Finding] = []
        headings = [block for block in document.blocks if block.type is BlockType.HEADING]
        word_count = self._word_count(document.content)

        if not headings and word_count >= self.config.minimum_words_without_headings:
            findings.append(self._missing_headings_finding(document, word_count))
            return findings

        for heading, section_blocks, section_word_count in self._sections(document.blocks):
            if section_word_count > self.config.maximum_words_per_section:
                findings.append(
                    Finding(
                        id="section-exceeds-recommended-length",
                        title="Section is too long to preserve context reliably",
                        severity=Severity.WARNING,
                        category=FindingCategory.CONTENT_ISSUE,
                        owner=FindingOwner.CONTENT_OWNER,
                        why_it_matters=(
                            f"This section contains approximately {section_word_count} words. "
                            "When it is split for AI processing, related details may lose their "
                            "section context."
                        ),
                        recommendation=(
                            "Split the section into smaller semantic subsections with Heading 2 or "
                            "Heading 3 titles."
                        ),
                        evidence=Evidence(
                            excerpt=heading.text,
                            location=heading.location,
                        ),
                    )
                )

        return findings

    def _missing_headings_finding(
        self, document: NormalizedDocument, word_count: int
    ) -> Finding:
        evidence_block = next(
            (block for block in document.blocks if block.type is not BlockType.IMAGE), None
        )
        if evidence_block is None:
            evidence = Evidence(
                excerpt="No semantic headings were found.",
                location=SourceLocation(label="Normalized content"),
            )
        else:
            evidence = Evidence(excerpt=evidence_block.text, location=evidence_block.location)

        return Finding(
            id="missing-semantic-headings",
            title="Sections are not marked with semantic headings",
            severity=Severity.WARNING,
            category=FindingCategory.CONTENT_ISSUE,
            owner=FindingOwner.CONTENT_OWNER,
            why_it_matters=(
                f"The document contains approximately {word_count} words but no semantic headings. "
                "When content is split for AI processing, passages may lose their topic and context."
            ),
            recommendation=(
                "Use Heading 1–3 styles in Word or #, ##, and ### headings in Markdown to mark "
                "the document structure."
            ),
            evidence=evidence,
        )

    @staticmethod
    def _sections(blocks: tuple[Block, ...]) -> list[tuple[Block, list[Block], int]]:
        sections: list[tuple[Block, list[Block], int]] = []
        current_heading: Block | None = None
        current_blocks: list[Block] = []

        for block in blocks:
            if block.type is BlockType.HEADING:
                if current_heading is not None:
                    sections.append(
                        (current_heading, current_blocks, StructureCheck._blocks_word_count(current_blocks))
                    )
                current_heading = block
                current_blocks = []
                continue

            if current_heading is not None:
                current_blocks.append(block)

        if current_heading is not None:
            sections.append(
                (current_heading, current_blocks, StructureCheck._blocks_word_count(current_blocks))
            )

        return sections

    @staticmethod
    def _blocks_word_count(blocks: list[Block]) -> int:
        return sum(StructureCheck._word_count(block.text) for block in blocks)

    @staticmethod
    def _word_count(text: str) -> int:
        return len(text.split())
