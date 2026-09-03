"""Checks for Excel context and rows that are hard to use as AI input."""

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
)


@dataclass(frozen=True)
class ExcelCheckConfig:
    """Thresholds for deterministic Excel findings."""

    maximum_characters_per_table_row: int = 1500


class ExcelCheck:
    """Report missing table context and exceptionally dense Excel rows."""

    def __init__(self, config: ExcelCheckConfig | None = None) -> None:
        self.config = config or ExcelCheckConfig()

    def run(self, document: NormalizedDocument) -> list[Finding]:
        """Return findings only for successfully extracted Excel workbooks."""

        if document.document.file_type != "xlsx" or not document.document.extraction_succeeded:
            return []

        findings: list[Finding] = []
        for index, block in enumerate(document.blocks):
            if block.type is not BlockType.TABLE:
                continue
            if block.location.sheet_name is None:
                findings.append(self._missing_sheet_context_finding(block))
            if not self._has_table_title(document.blocks, index):
                findings.append(self._missing_table_purpose_finding(block))
            findings.extend(self._dense_row_findings(block))
        return findings

    @staticmethod
    def _has_table_title(blocks: tuple[Block, ...], table_index: int) -> bool:
        if table_index == 0:
            return False
        preceding_block = blocks[table_index - 1]
        return (
            preceding_block.type is BlockType.HEADING
            and preceding_block.heading_level == 3
            and preceding_block.text.startswith("Table: ")
        )

    @staticmethod
    def _missing_sheet_context_finding(block: Block) -> Finding:
        return Finding(
            id="excel-table-missing-sheet-context",
            title="Table is missing its worksheet context",
            severity=Severity.WARNING,
            category=FindingCategory.INGESTION_LIMITATION,
            owner=FindingOwner.PLATFORM_TEAM,
            why_it_matters=(
                "The normalized table is not associated with a worksheet. AI users cannot tell "
                "which part of the workbook the records came from."
            ),
            recommendation=(
                "Preserve the worksheet name with every exported table and verify the workbook "
                "normalization path."
            ),
            evidence=Evidence(excerpt=block.text, location=block.location),
        )

    @staticmethod
    def _missing_table_purpose_finding(block: Block) -> Finding:
        return Finding(
            id="excel-table-has-no-detectable-purpose",
            title="Table has no detectable name or purpose",
            severity=Severity.WARNING,
            category=FindingCategory.CONTENT_ISSUE,
            owner=FindingOwner.SHARED,
            why_it_matters=(
                "Column headers alone may not explain what a table represents. Its intended "
                "meaning can be lost when the table is retrieved without nearby workbook context."
            ),
            recommendation=(
                "Content owner: add a concise title directly above the table. Platform team: "
                "retain that title with the exported table."
            ),
            evidence=Evidence(excerpt=block.text, location=block.location),
        )

    def _dense_row_findings(self, block: Block) -> list[Finding]:
        findings: list[Finding] = []
        for row_number, row in enumerate(block.text.splitlines(), start=1):
            if len(row) > self.config.maximum_characters_per_table_row:
                findings.append(
                    Finding(
                        id="excel-row-exceeds-recommended-density",
                        title="Table row is too dense to preserve context reliably",
                        severity=Severity.WARNING,
                        category=FindingCategory.CONTENT_ISSUE,
                        owner=FindingOwner.CONTENT_OWNER,
                        why_it_matters=(
                            f"This normalized table row contains {len(row)} characters. Dense "
                            "records are more likely to be split or retrieved without the fields "
                            "needed to interpret them."
                        ),
                        recommendation=(
                            "Split the record into smaller rows or move long narrative fields into "
                            "a separately titled section."
                        ),
                        evidence=Evidence(
                            excerpt=row,
                            location=block.location,
                        ),
                    )
                )
        return findings
