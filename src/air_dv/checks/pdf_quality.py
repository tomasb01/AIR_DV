"""Quality checks specific to PDF extraction."""

from __future__ import annotations

from air_dv.models import (
    Evidence,
    Finding,
    FindingCategory,
    FindingOwner,
    NormalizedDocument,
    Severity,
    SourceLocation,
)


class PdfExtractionQualityCheck:
    """Expose extractor warnings that make PDF text completeness uncertain."""

    def run(self, document: NormalizedDocument) -> list[Finding]:
        """Return quality findings only for successfully extracted PDFs."""

        if document.document.file_type != "pdf" or not document.document.extraction_succeeded:
            return []
        metadata = dict(document.document.source_metadata)
        warning_count = int(metadata.get("ocr_warning_count", "0"))
        if warning_count == 0:
            return []
        page_count = metadata.get("page_count", "unknown")
        return [
            Finding(
                id="pdf-ocr-quality-could-not-be-verified",
                title="PDF OCR quality could not be fully verified",
                severity=Severity.WARNING,
                category=FindingCategory.INGESTION_LIMITATION,
                owner=FindingOwner.PLATFORM_TEAM,
                why_it_matters=(
                    f"Docling reported {warning_count} OCR warning(s) while processing this "
                    f"{page_count}-page PDF. Some visual regions may be missing or unreadable in "
                    "the normalized AI view."
                ),
                recommendation=(
                    "Review the normalized AI view against the affected PDF pages before using it "
                    "as AI input. If important text is missing, provide a text-native source or "
                    "adjust the extraction pipeline."
                ),
                evidence=Evidence(
                    excerpt=f"Docling reported {warning_count} OCR warning(s).",
                    location=SourceLocation(label="PDF extraction status"),
                ),
            )
        ]
