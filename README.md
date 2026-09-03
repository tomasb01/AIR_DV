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

## Command line

From the project directory, analyse a supported local document with the short launcher:

```bash
./air-dv "Data/document.docx"
```

It also accepts optional exports:

```bash
./air-dv "Data/document.docx" --report report.md --ai-view normalized.md --json result.json
```

The equivalent Python module command is available for automation:

```bash
PYTHONPATH=src .venv/bin/python -m air_dv analyse path/to/document.docx \
  --report report.md --ai-view normalized.md --json result.json
```

The command supports `.md`, `.docx`, and `.xlsx`. Word analysis requires the local
`docling` command; all analysis and exports remain on the local machine.

## Product documents

- [Product specification](product_spec.md)
- [Development plan](development_plan.md)
