"""Public orchestration for normalizing a document and running all readiness checks."""

from __future__ import annotations

from pathlib import Path

from air_dv.checks.excel import ExcelCheck
from air_dv.checks.external_references import ExternalReferenceCheck
from air_dv.checks.extraction import ExtractionCheck
from air_dv.checks.pdf_quality import PdfExtractionQualityCheck
from air_dv.checks.structure import StructureCheck
from air_dv.models import AnalysisResult, NormalizedDocument
from air_dv.normalization import DoclingPdfNormalizer, DoclingWordNormalizer, ExcelNormalizer, MarkdownNormalizer


class UnsupportedSourceFormatError(ValueError):
    """Raised when AIR-DV has no normalizer for a source file extension."""


def analyse_file(path: str | Path) -> AnalysisResult:
    """Normalize a supported file and return all deterministic readiness findings."""

    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Source file does not exist: {source_path}")

    document = _normalizer_for(source_path).normalize_file(source_path)
    findings = []
    for check in (
        StructureCheck(),
        ExtractionCheck(),
        PdfExtractionQualityCheck(),
        ExternalReferenceCheck(),
        ExcelCheck(),
    ):
        findings.extend(check.run(document))
    return AnalysisResult(
        document=document.document,
        normalized_content=document.content,
        findings=findings,
    )


def _normalizer_for(
    path: Path,
) -> MarkdownNormalizer | DoclingWordNormalizer | DoclingPdfNormalizer | ExcelNormalizer:
    suffix = path.suffix.casefold()
    if suffix == ".md":
        return MarkdownNormalizer()
    if suffix == ".docx":
        return DoclingWordNormalizer()
    if suffix == ".pdf":
        return DoclingPdfNormalizer()
    if suffix == ".xlsx":
        return ExcelNormalizer()
    raise UnsupportedSourceFormatError(
        f"Unsupported source format '{suffix or 'without an extension'}'. "
        "Supported formats: .md, .docx, .pdf, .xlsx."
    )
