# AIR-DV

AIR-DV is a local-first tool that checks whether a document is ready for general AI use.

The MVP accepts Markdown, Word, and Excel files, shows the normalized content that an AI
system would receive, and reports actionable content issues and ingestion limitations.

## Development

The project requires Python 3.12 or later.

Word analysis additionally requires the `docling` command to be available on `PATH`.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

## Product documents

- [Product specification](product_spec.md)
- [Development plan](development_plan.md)
