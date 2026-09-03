"""Normalization of source formats into an extractor-independent document model."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from openpyxl import load_workbook

from air_dv.models import Block, BlockType, DocumentSummary, NormalizedDocument, SourceLocation


_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
_LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)$")
_IMAGE_PATTERN = re.compile(r"!\[[^]]*\]\([^)]*\)")


class MarkdownNormalizer:
    """Read Markdown while preserving the semantic structures needed by AIR-DV checks."""

    file_type = "md"

    def normalize_file(self, path: str | Path) -> NormalizedDocument:
        """Normalize a UTF-8 Markdown file from disk."""

        source_path = Path(path)
        return self.normalize_text(source_path.name, source_path.read_text(encoding="utf-8"))

    def normalize_text(
        self,
        filename: str,
        content: str,
        *,
        source_label: str = "Source Markdown",
    ) -> NormalizedDocument:
        """Normalize Markdown text and retain source line locations for each block."""

        blocks: list[Block] = []
        lines = content.splitlines()
        index = 0

        while index < len(lines):
            line = lines[index]
            line_number = index + 1

            if not line.strip():
                index += 1
                continue

            heading_match = _HEADING_PATTERN.match(line)
            if heading_match:
                blocks.append(
                    Block(
                        type=BlockType.HEADING,
                        text=heading_match.group(2),
                        heading_level=len(heading_match.group(1)),
                        location=SourceLocation(label=source_label, line_start=line_number),
                    )
                )
                index += 1
                continue

            if line.lstrip().startswith("|"):
                index = self._collect_table(lines, index, blocks, source_label)
                continue

            image_match = _IMAGE_PATTERN.search(line)
            if image_match:
                blocks.append(
                    Block(
                        type=BlockType.IMAGE,
                        text=image_match.group(0),
                        location=SourceLocation(label=source_label, line_start=line_number),
                    )
                )
                index += 1
                continue

            list_match = _LIST_ITEM_PATTERN.match(line)
            if list_match:
                blocks.append(
                    Block(
                        type=BlockType.LIST_ITEM,
                        text=list_match.group(1),
                        location=SourceLocation(label=source_label, line_start=line_number),
                    )
                )
                index += 1
                continue

            index = self._collect_paragraph(lines, index, blocks, source_label)

        summary = DocumentSummary(
            filename=filename,
            file_type=self.file_type,
            extraction_succeeded=True,
        )
        return NormalizedDocument(document=summary, content=content, blocks=tuple(blocks))

    @staticmethod
    def _collect_table(
        lines: list[str], index: int, blocks: list[Block], source_label: str
    ) -> int:
        start_index = index
        table_lines: list[str] = []
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            table_lines.append(lines[index])
            index += 1

        blocks.append(
            Block(
                type=BlockType.TABLE,
                text="\n".join(table_lines),
                location=SourceLocation(
                    label=source_label,
                    line_start=start_index + 1,
                    line_end=index,
                ),
            )
        )
        return index

    @staticmethod
    def _collect_paragraph(
        lines: list[str], index: int, blocks: list[Block], source_label: str
    ) -> int:
        start_index = index
        paragraph_lines: list[str] = []

        while index < len(lines):
            line = lines[index]
            if not line.strip() or _HEADING_PATTERN.match(line) or line.lstrip().startswith("|"):
                break
            if _LIST_ITEM_PATTERN.match(line) or _IMAGE_PATTERN.search(line):
                break
            paragraph_lines.append(line)
            index += 1

        if paragraph_lines:
            blocks.append(
                Block(
                    type=BlockType.PARAGRAPH,
                    text="\n".join(paragraph_lines),
                    location=SourceLocation(
                        label=source_label,
                        line_start=start_index + 1,
                        line_end=index,
                    ),
                )
            )
            return index

        return index + 1


class DoclingWordNormalizer:
    """Normalize Word documents through the locally installed Docling CLI."""

    file_type = "docx"

    def __init__(self, executable: str = "docling") -> None:
        self.executable = executable
        self._markdown_normalizer = MarkdownNormalizer()

    def normalize_file(self, path: str | Path) -> NormalizedDocument:
        """Extract a Word file to Markdown and retain its original identity."""

        source_path = Path(path)
        if source_path.suffix.lower() != ".docx":
            raise ValueError("DoclingWordNormalizer only accepts .docx files")

        if shutil.which(self.executable) is None:
            return self._failed_document(
                source_path,
                f"Required extractor '{self.executable}' is not available on PATH.",
            )

        with tempfile.TemporaryDirectory(prefix="air-dv-docling-") as output_dir:
            command = [
                self.executable,
                "convert",
                str(source_path),
                "--to",
                "md",
                "--output",
                output_dir,
                "--image-export-mode",
                "placeholder",
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            output_path = Path(output_dir, f"{source_path.stem}.md")

            if completed.returncode != 0:
                detail = completed.stderr.strip() or completed.stdout.strip() or "Unknown extractor error."
                return self._failed_document(source_path, f"Docling extraction failed: {detail}")
            if not output_path.is_file():
                return self._failed_document(
                    source_path,
                    "Docling completed without producing a Markdown output file.",
                )

            extracted_markdown = output_path.read_text(encoding="utf-8")

        normalized_markdown = self._markdown_normalizer.normalize_text(
            source_path.name,
            extracted_markdown,
            source_label="Normalized Word content",
        )
        return NormalizedDocument(
            document=DocumentSummary(
                filename=source_path.name,
                file_type=self.file_type,
                extraction_succeeded=True,
                extraction_notes=("Extracted with Docling.",),
            ),
            content=normalized_markdown.content,
            blocks=normalized_markdown.blocks,
        )

    def _failed_document(self, source_path: Path, note: str) -> NormalizedDocument:
        return NormalizedDocument(
            document=DocumentSummary(
                filename=source_path.name,
                file_type=self.file_type,
                extraction_succeeded=False,
                extraction_notes=(note,),
            ),
            content="",
            blocks=(),
        )


class ExcelNormalizer:
    """Normalize Excel workbooks while retaining workbook and sheet context."""

    file_type = "xlsx"

    def __init__(self) -> None:
        self._markdown_normalizer = MarkdownNormalizer()

    def normalize_file(self, path: str | Path) -> NormalizedDocument:
        """Create a context-preserving Markdown representation of an Excel workbook."""

        source_path = Path(path)
        if source_path.suffix.lower() != ".xlsx":
            raise ValueError("ExcelNormalizer only accepts .xlsx files")

        try:
            workbook = load_workbook(source_path, data_only=False)
        except Exception as error:
            return self._failed_document(source_path, f"Excel extraction failed: {error}")

        formula_count = 0
        merged_range_count = 0
        image_count = 0
        markdown_lines = [f"# Workbook: {source_path.stem}", ""]

        for worksheet in workbook.worksheets:
            formula_count += sum(
                1
                for row in worksheet.iter_rows()
                for cell in row
                if cell.data_type == "f"
            )
            merged_range_count += len(worksheet.merged_cells.ranges)
            image_count += len(worksheet._images)
            markdown_lines.extend(self._normalize_worksheet(worksheet))

        content = "\n".join(markdown_lines).rstrip() + "\n"
        normalized_markdown = self._markdown_normalizer.normalize_text(
            source_path.name,
            content,
            source_label="Normalized Excel content",
        )
        return NormalizedDocument(
            document=DocumentSummary(
                filename=source_path.name,
                file_type=self.file_type,
                extraction_succeeded=True,
                extraction_notes=("Extracted from workbook structure.",),
                source_metadata=(
                    ("sheet_count", str(len(workbook.worksheets))),
                    ("formula_count", str(formula_count)),
                    ("merged_range_count", str(merged_range_count)),
                    ("image_count", str(image_count)),
                ),
            ),
            content=content,
            blocks=self._attach_sheet_context(normalized_markdown.blocks),
        )

    def _normalize_worksheet(self, worksheet: object) -> list[str]:
        lines = [f"## Sheet: {worksheet.title}", ""]
        row_groups = self._non_empty_row_groups(worksheet)
        pending_title: str | None = None

        if not row_groups:
            return [*lines, "_No populated cells found._", ""]

        for group in row_groups:
            if self._is_title_row(group):
                pending_title = self._row_values(group[0])[0]
                continue

            if pending_title:
                lines.extend([f"### Table: {pending_title}", ""])
                pending_title = None

            lines.extend(self._to_markdown_table(group))
            lines.append("")

        if pending_title:
            lines.extend([f"### Note: {pending_title}", ""])
        return lines

    @staticmethod
    def _non_empty_row_groups(worksheet: object) -> list[list[tuple[object, ...]]]:
        groups: list[list[tuple[object, ...]]] = []
        current_group: list[tuple[object, ...]] = []

        for row in worksheet.iter_rows():
            if any(cell.value not in (None, "") for cell in row):
                current_group.append(row)
            elif current_group:
                groups.append(current_group)
                current_group = []

        if current_group:
            groups.append(current_group)
        return groups

    @classmethod
    def _is_title_row(cls, rows: list[tuple[object, ...]]) -> bool:
        return len(rows) == 1 and len(cls._row_values(rows[0])) == 1

    @staticmethod
    def _row_values(row: tuple[object, ...]) -> list[str]:
        values = ["" if cell.value is None else str(cell.value) for cell in row]
        while values and not values[-1]:
            values.pop()
        return values or [""]

    @classmethod
    def _to_markdown_table(cls, rows: list[tuple[object, ...]]) -> list[str]:
        values_by_row = [cls._row_values(row) for row in rows]
        column_count = max(len(values) for values in values_by_row)
        padded_rows = [values + [""] * (column_count - len(values)) for values in values_by_row]
        header, *body = padded_rows

        lines = [cls._markdown_row(header), cls._markdown_row(["---"] * column_count)]
        lines.extend(cls._markdown_row(row) for row in body)
        return lines

    @staticmethod
    def _markdown_row(values: list[str]) -> str:
        escaped = [value.replace("|", "\\|").replace("\n", "<br>") for value in values]
        return f"| {' | '.join(escaped)} |"

    @staticmethod
    def _attach_sheet_context(blocks: tuple[Block, ...]) -> tuple[Block, ...]:
        current_sheet: str | None = None
        contextualized_blocks: list[Block] = []

        for block in blocks:
            if block.type is BlockType.HEADING and block.heading_level == 2:
                sheet_prefix = "Sheet: "
                if block.text.startswith(sheet_prefix):
                    current_sheet = block.text.removeprefix(sheet_prefix)

            contextualized_blocks.append(
                replace(block, location=replace(block.location, sheet_name=current_sheet))
            )

        return tuple(contextualized_blocks)

    def _failed_document(self, source_path: Path, note: str) -> NormalizedDocument:
        return NormalizedDocument(
            document=DocumentSummary(
                filename=source_path.name,
                file_type=self.file_type,
                extraction_succeeded=False,
                extraction_notes=(note,),
            ),
            content="",
            blocks=(),
        )
