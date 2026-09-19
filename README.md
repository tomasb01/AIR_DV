# AIR-DV

AIR-DV is a local-first tool that checks whether a document is ready for general AI use.

The MVP accepts Markdown, Word, PDF, and Excel files, shows the normalized content that an AI
system would receive, and reports actionable content issues and ingestion limitations.

## Development

The project requires Python 3.12 or later.

Word and PDF analysis additionally require the `docling` command to be available on `PATH`.

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

The command supports `.md`, `.docx`, `.pdf`, and `.xlsx`. Word and PDF analysis require the
local `docling` command; all analysis and exports remain on the local machine. PDF conversion
uses image placeholders rather than embedded image data and reports OCR warnings and visual
objects whose text equivalent cannot be verified.

## Local UI

Start the local upload UI from the project directory:

```bash
./air-dv-ui
```

Then open `http://127.0.0.1:8000` in a browser. The result shows the text-only normalized
"What AI sees" view and provides local downloads of the Markdown report, AI view, and JSON
result. Uploaded files are kept only in a temporary local directory for the duration of the
analysis and are then deleted; generated downloads remain only in the local app's memory for
15 minutes.

### Confluence Data Center POC

The UI accepts a Confluence Data Center page URL in the `/spaces/<space>/pages/<page-id>` form
and validates it locally. Page retrieval is enabled only after read-only OAuth is configured;
the current preparation step never sends page content or browser cookies to Confluence.

When the corporate OAuth client is available, keep its settings outside Git and provide them in
the local environment:

```bash
export AIR_DV_CONFLUENCE_OAUTH_CLIENT_ID="..."
export AIR_DV_CONFLUENCE_OAUTH_AUTHORIZATION_URL="https://..."
export AIR_DV_CONFLUENCE_OAUTH_TOKEN_URL="https://..."
export AIR_DV_CONFLUENCE_OAUTH_SCOPE="..."
```

Do not place access tokens, client secrets, or browser cookies in the repository.

## Product documents

- [Product specification](product_spec.md)
- [Development plan](development_plan.md)
