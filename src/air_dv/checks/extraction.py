"""Checks for failed extraction and visual content without usable text alternatives."""

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
    SourceLocation,
)


_IMAGE_ALT_TEXT_PATTERN = re.compile(r"!\[([^]]*)\]\([^)]*\)")
_GENERIC_ALT_TEXT = {"image", "picture", "photo", "diagram", "screenshot", "figure"}


class ExtractionCheck:
    """Report extraction failures and visual content that cannot be verified as text-accessible."""

    def run(self, document: NormalizedDocument) -> list[Finding]:
        """Return deterministic findings for extraction status and visual blocks."""

        if not document.document.extraction_succeeded:
            return [self._extraction_failed_finding(document)]

        findings: list[Finding] = []
        unsupported_objects = [
            block for block in document.blocks if block.type is BlockType.UNSUPPORTED_OBJECT
        ]
        for block in document.blocks:
            if block.type is BlockType.IMAGE:
                finding = self._image_finding(block)
                if finding is not None:
                    findings.append(finding)
        if document.document.file_type == "pdf" and unsupported_objects:
            findings.append(self._pdf_visual_objects_finding(unsupported_objects))
        elif document.document.file_type == "docx" and unsupported_objects:
            findings.append(self._word_visual_objects_finding(document, unsupported_objects))
        else:
            findings.extend(self._unsupported_object_finding(block) for block in unsupported_objects)

        return findings

    @staticmethod
    def _extraction_failed_finding(document: NormalizedDocument) -> Finding:
        notes = " ".join(document.document.extraction_notes) or "The extractor returned no details."
        return Finding(
            id="document-extraction-failed",
            title="Document content could not be extracted reliably",
            severity=Severity.CRITICAL,
            category=FindingCategory.INGESTION_LIMITATION,
            owner=FindingOwner.PLATFORM_TEAM,
            why_it_matters=(
                "AIR-DV cannot assess AI readiness when the source content is unavailable to the "
                f"extractor. Details: {notes}"
            ),
            recommendation=(
                "Check the source format and extractor logs. Do not treat this document as "
                "AI-ready until extraction succeeds."
            ),
            evidence=Evidence(
                excerpt=notes,
                location=SourceLocation(label="Extraction status"),
            ),
        )

    def _image_finding(self, block: Block) -> Finding | None:
        alt_text_match = _IMAGE_ALT_TEXT_PATTERN.fullmatch(block.text)
        alt_text = alt_text_match.group(1).strip() if alt_text_match else ""

        if not alt_text:
            return Finding(
                id="image-missing-text-equivalent",
                title="Image has no text equivalent",
                severity=Severity.CRITICAL,
                category=FindingCategory.CONTENT_ISSUE,
                owner=FindingOwner.CONTENT_OWNER,
                why_it_matters=(
                    "Important information may exist only in the image, where text-only AI systems "
                    "cannot retrieve or quote it."
                ),
                recommendation=(
                    "Add a concise text description of the image's purpose, key entities, flow, "
                    "and exceptions next to the image."
                ),
                evidence=Evidence(excerpt=block.text, location=block.location),
            )

        if alt_text.casefold() in _GENERIC_ALT_TEXT:
            return Finding(
                id="image-text-equivalent-may-be-insufficient",
                title="Image description may be too generic",
                severity=Severity.WARNING,
                category=FindingCategory.CONTENT_ISSUE,
                owner=FindingOwner.CONTENT_OWNER,
                why_it_matters=(
                    "A generic image label does not preserve the image's information or explain "
                    "its relevance when visual input is unavailable."
                ),
                recommendation=(
                    "Replace the generic label with a text description of the image's key "
                    "information and its relationship to the surrounding content."
                ),
                evidence=Evidence(excerpt=block.text, location=block.location),
            )

        return None

    @staticmethod
    def _unsupported_object_finding(block: Block) -> Finding:
        return Finding(
            id="object-text-equivalent-could-not-be-verified",
            title="Visual object could not be verified as text-accessible",
            severity=Severity.WARNING,
            category=FindingCategory.INGESTION_LIMITATION,
            owner=FindingOwner.SHARED,
            why_it_matters=(
                "The normalized output contains a visual-object placeholder rather than its "
                "semantic content. AIR-DV cannot determine whether the source includes a usable "
                "text equivalent."
            ),
            recommendation=(
                "Content owner: add a nearby text description if the object is important. "
                "Platform team: verify whether the extractor can retain the object's alt text or "
                "semantic representation."
            ),
            evidence=Evidence(excerpt=block.text, location=block.location),
        )

    @staticmethod
    def _pdf_visual_objects_finding(blocks: list[Block]) -> Finding:
        first_block = blocks[0]
        return Finding(
            id="pdf-visual-objects-unavailable-to-text-only-ingestion",
            title="Text-only ingestion cannot process PDF visual objects",
            severity=Severity.WARNING,
            category=FindingCategory.INGESTION_LIMITATION,
            owner=FindingOwner.SHARED,
            why_it_matters=(
                f"AIR-DV's current AI view is text-only and retains {len(blocks)} visual-object "
                "placeholder(s), not image pixels or their semantic content. A text-only LLM will "
                "not receive information contained only in these PDF visuals."
            ),
            recommendation=(
                "For visuals that carry decisions, values, process steps, or exceptions, add a "
                "nearby text equivalent. Alternatively, configure a multimodal ingestion pipeline "
                "that retains and supplies the source images to the target model."
            ),
            evidence=Evidence(excerpt=first_block.text, location=first_block.location),
        )

    @staticmethod
    def _word_visual_objects_finding(
        document: NormalizedDocument, blocks: list[Block]
    ) -> Finding:
        first_block = blocks[0]
        metadata = dict(document.document.source_metadata)
        reference_count = metadata.get("visual_reference_count", str(len(blocks)))
        media_count = metadata.get("unique_media_file_count")
        unique_media_detail = f" ({media_count} unique media file(s))" if media_count else ""
        return Finding(
            id="word-visual-objects-unavailable-to-text-only-ingestion",
            title="Text-only ingestion cannot process Word visual objects",
            severity=Severity.WARNING,
            category=FindingCategory.INGESTION_LIMITATION,
            owner=FindingOwner.SHARED,
            why_it_matters=(
                f"AIR-DV's current AI view is text-only and retains {len(blocks)} visual-object "
                f"placeholder(s), not image pixels or their semantic content. The Word source "
                f"contains {reference_count} visual reference(s){unique_media_detail}; repeated "
                "references do not necessarily mean separate images. A text-only LLM will not "
                "receive information contained only in these visuals."
            ),
            recommendation=(
                "Review representative visuals, especially diagrams, tables rendered as images, "
                "and screenshots. Add nearby text equivalents where they carry decisions, values, "
                "process steps, or exceptions. Alternatively, configure a multimodal ingestion "
                "pipeline that retains and supplies the source images to the target model."
            ),
            evidence=Evidence(excerpt=first_block.text, location=first_block.location),
        )
