# AIR-DV fixture catalog

These small, intentionally focused files cover the supported source formats and known
AI-readiness risks. They are safe to commit and contain no business data.

| Fixture | Format | Scenario |
|---|---|---|
| `markdown/semantic_structure.md` | Markdown | Semantic heading hierarchy and a normal table |
| `markdown/missing_image_alt.md` | Markdown | Image with no text equivalent |
| `markdown/generic_image_alt.md` | Markdown | Image with an insufficient generic label |
| `markdown/described_image.md` | Markdown | Image with a useful text equivalent |
| `markdown/external_reference.md` | Markdown | Jira reference without a local summary |
| `word/visual_title_only.docx` | Word | Bold visual title without a semantic heading style |
| `excel/context_workbook.xlsx` | Excel | Sheet and table context, merged title, formula |

The Word and Excel files are committed so they can be opened manually and used in
integration tests or the future UI. Their construction remains visible and reproducible
in `tests.fixture_builders`; tests validate both the builders and the committed files.
