"""Deterministic, source-specific edit plans for AIR-DV findings."""

from __future__ import annotations

from air_dv.models import Finding


def suggested_change(finding: Finding) -> str:
    """Return a concrete edit plan without inventing domain content."""

    location = _location_reference(finding)
    if finding.id == "section-exceeds-recommended-length":
        return (
            f"Review the content after “{finding.evidence.excerpt}” and add a semantic heading at "
            "each actual topic boundary. Use Heading 2 for a new major topic and Heading 3 only "
            "for a subtopic that belongs under the current section. Do not nest unrelated topics "
            "under this title."
        )
    if finding.id == "missing-semantic-headings":
        return (
            f"At {location}, apply Heading 1 to the document title if it is a title, then use "
            "Heading 2 for each major topic and Heading 3 for its subtopics. Do not rely on bold "
            "text alone to mark a section."
        )
    if finding.id == "image-missing-text-equivalent":
        return (
            f"Immediately after the image at {location}, add a short paragraph beginning “Image "
            "description:” that states what it shows, the key entities or steps, and any important "
            "exception."
        )
    if finding.id == "image-text-equivalent-may-be-insufficient":
        return (
            f"Replace the label “{_image_label(finding.evidence.excerpt)}” at {location} with a "
            "description of the image's key information and why it matters to the surrounding text."
        )
    if finding.id == "external-reference-without-local-summary":
        return (
            f"At {location}, replace “{finding.evidence.excerpt}” with one or two sentences that "
            "state the decision, rule, or constraint locally; keep the external reference afterwards."
        )
    if finding.id == "excel-row-exceeds-recommended-density":
        return (
            f"In {location}, move the long narrative value into a separately titled note or split "
            "this record into multiple rows with one topic per row. Keep the identifier fields in "
            "each resulting row."
        )
    if finding.id == "excel-table-has-no-detectable-purpose":
        return (
            f"Add a one-line title directly above the table at {location}. The title should say "
            "what the records represent, not merely repeat a column name."
        )
    if finding.id == "excel-table-missing-sheet-context":
        return (
            "No content edit is required. Preserve the worksheet name with this table in the "
            "normalization/export path, then re-run the analysis."
        )
    if finding.id == "document-extraction-failed":
        return (
            "No content edit is recommended until extraction succeeds. Open the source file, check "
            "the extractor requirement, then re-run AIR-DV."
        )
    if finding.id == "pdf-ocr-quality-could-not-be-verified":
        return (
            "Compare the normalized AI view with the original PDF, especially visual regions. "
            "Do not rely on the extracted text alone until the OCR warnings are resolved or "
            "accepted after review."
        )
    if finding.id == "pdf-visual-objects-unavailable-to-text-only-ingestion":
        return (
            f"Starting at {location}, review each visual placeholder. Add a text description next "
            "to every visual that carries a decision, value, process step, or exception; or use a "
            "multimodal ingestion pipeline that supplies the images to the target model."
        )
    if finding.id == "word-visual-objects-unavailable-to-text-only-ingestion":
        return (
            f"Starting at {location}, review representative visuals rather than treating every "
            "reference as a separate task. Add text descriptions beside visuals that carry decisions, "
            "values, process steps, or exceptions; or use a multimodal ingestion pipeline that "
            "supplies the images to the target model."
        )
    if finding.id == "object-text-equivalent-could-not-be-verified":
        return (
            f"At {location}, add a nearby text description of the object's purpose and key "
            "information, then verify that the extractor retains it."
        )
    return finding.recommendation


def _location_reference(finding: Finding) -> str:
    location = finding.evidence.location
    if location.cell_range and location.sheet_name:
        return f"sheet “{location.sheet_name}”, cells {location.cell_range}"
    if location.paragraph_index:
        return f"Word paragraph {location.paragraph_index}"
    if location.page_number:
        return f"PDF page {location.page_number}"
    if location.line_start:
        return f"line {location.line_start}"
    return location.label


def _image_label(markdown_image: str) -> str:
    match = re.fullmatch(r"!\[([^]]*)\]\([^)]*\)", markdown_image)
    return match.group(1) if match else markdown_image
