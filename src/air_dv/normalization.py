"""Normalization of source formats into an extractor-independent document model."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

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
