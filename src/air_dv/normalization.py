"""Normalization of source formats into an extractor-independent document model."""

from __future__ import annotations

import re
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

    def normalize_text(self, filename: str, content: str) -> NormalizedDocument:
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
                        location=SourceLocation(label="Source Markdown", line_start=line_number),
                    )
                )
                index += 1
                continue

            if line.lstrip().startswith("|"):
                index = self._collect_table(lines, index, blocks)
                continue

            image_match = _IMAGE_PATTERN.search(line)
            if image_match:
                blocks.append(
                    Block(
                        type=BlockType.IMAGE,
                        text=image_match.group(0),
                        location=SourceLocation(label="Source Markdown", line_start=line_number),
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
                        location=SourceLocation(label="Source Markdown", line_start=line_number),
                    )
                )
                index += 1
                continue

            index = self._collect_paragraph(lines, index, blocks)

        summary = DocumentSummary(
            filename=filename,
            file_type=self.file_type,
            extraction_succeeded=True,
        )
        return NormalizedDocument(document=summary, content=content, blocks=tuple(blocks))

    @staticmethod
    def _collect_table(lines: list[str], index: int, blocks: list[Block]) -> int:
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
                    label="Source Markdown",
                    line_start=start_index + 1,
                    line_end=index,
                ),
            )
        )
        return index

    @staticmethod
    def _collect_paragraph(lines: list[str], index: int, blocks: list[Block]) -> int:
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
                        label="Source Markdown",
                        line_start=start_index + 1,
                        line_end=index,
                    ),
                )
            )
            return index

        return index + 1
