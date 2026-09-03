"""Tests for deterministic Markdown normalization."""

import unittest

from air_dv.models import BlockType
from air_dv.normalization import MarkdownNormalizer


class MarkdownNormalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.normalizer = MarkdownNormalizer()

    def test_preserves_semantic_blocks_and_line_locations(self) -> None:
        content = """# Plant guide

Introductory paragraph
that continues on a second line.

## Hawthorn

- Gather flowers in spring.

![Hawthorn diagram](hawthorn.png)

| Part | Season |
| --- | --- |
| Flower | Spring |
"""

        document = self.normalizer.normalize_text("plants.md", content)

        self.assertEqual(document.document.filename, "plants.md")
        self.assertEqual(document.document.file_type, "md")
        self.assertEqual(
            [block.type for block in document.blocks],
            [
                BlockType.HEADING,
                BlockType.PARAGRAPH,
                BlockType.HEADING,
                BlockType.LIST_ITEM,
                BlockType.IMAGE,
                BlockType.TABLE,
            ],
        )
        self.assertEqual(document.blocks[0].heading_level, 1)
        self.assertEqual(document.blocks[2].heading_level, 2)
        self.assertEqual(document.blocks[1].location.line_start, 3)
        self.assertEqual(document.blocks[1].location.line_end, 4)
        self.assertEqual(document.blocks[-1].location.line_start, 12)
        self.assertEqual(document.blocks[-1].location.line_end, 14)

    def test_does_not_treat_bold_text_as_a_semantic_heading(self) -> None:
        document = self.normalizer.normalize_text(
            "legacy.md", "**Visual title only**\n\nText without a Markdown heading.\n"
        )

        self.assertEqual([block.type for block in document.blocks], [BlockType.PARAGRAPH] * 2)
        self.assertFalse(any(block.type is BlockType.HEADING for block in document.blocks))

    def test_allows_a_caller_to_label_normalized_content(self) -> None:
        document = self.normalizer.normalize_text(
            "converted.docx", "# Converted heading\n", source_label="Normalized Word content"
        )

        self.assertEqual(document.blocks[0].location.label, "Normalized Word content")
