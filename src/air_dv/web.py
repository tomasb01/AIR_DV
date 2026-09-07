"""Local-only upload UI for AIR-DV."""

from __future__ import annotations

import html
import shutil
import tempfile
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse

from air_dv.analysis import analyse_file
from air_dv.models import AnalysisResult, Finding, Severity
from air_dv.remediation import suggested_change
from air_dv.reporting import check_outcomes


_SUPPORTED_SUFFIXES = {".md", ".docx", ".pdf", ".xlsx"}
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def create_app() -> FastAPI:
    """Create the local AIR-DV upload application."""

    app = FastAPI(title="AIR-DV", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def upload_page() -> str:
        return _page(_upload_panel())

    @app.post("/analyse", response_class=HTMLResponse)
    def analyse_upload(document: UploadFile = File(...)) -> str:
        filename = Path(document.filename or "").name
        suffix = Path(filename).suffix.casefold()
        if not filename or suffix not in _SUPPORTED_SUFFIXES:
            return _page(
                _upload_panel(
                    "Choose a Markdown, Word, PDF, or Excel file (.md, .docx, .pdf, .xlsx)."
                )
            )

        try:
            with tempfile.TemporaryDirectory(prefix="air-dv-upload-") as directory:
                uploaded_path = Path(directory, filename)
                _save_upload(document, uploaded_path)
                result = analyse_file(uploaded_path)
        except (OSError, ValueError) as error:
            return _page(_upload_panel(f"Analysis could not be completed: {error}"))
        finally:
            document.file.close()

        return _page(_result_panel(result))

    return app


def _save_upload(document: UploadFile, destination: Path) -> None:
    """Save one bounded upload into an isolated temporary directory."""

    copied = 0
    with destination.open("wb") as output:
        while chunk := document.file.read(1024 * 1024):
            copied += len(chunk)
            if copied > _MAX_UPLOAD_BYTES:
                raise ValueError("The file exceeds the 50 MB local upload limit.")
            output.write(chunk)


def _page(body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AIR-DV — AI-ready document validation</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #172033; background: #f6f8fc; }}
    body {{ margin: 0; }} main {{ max-width: 900px; margin: 0 auto; padding: 52px 24px 72px; }}
    h1 {{ margin: 0; font-size: 2.25rem; letter-spacing: -.04em; }} h2 {{ margin: 0 0 12px; }}
    .subtitle {{ color: #536076; max-width: 650px; line-height: 1.55; }} .card {{ background: white; border: 1px solid #dce2ed; border-radius: 16px; padding: 28px; margin-top: 28px; box-shadow: 0 8px 30px #1b274014; }}
    .upload {{ border: 2px dashed #9cabc3; padding: 32px; border-radius: 12px; text-align: center; }} input {{ display: block; margin: 20px auto; max-width: 100%; }} button, .button {{ background: #2457d6; color: white; border: 0; border-radius: 9px; padding: 12px 18px; font-weight: 650; cursor: pointer; text-decoration: none; display: inline-block; }}
    .notice {{ color: #9e3124; background: #fff0ee; border-radius: 8px; padding: 12px; }} .status {{ font-size: 1.1rem; font-weight: 700; }} .needs-attention {{ color: #a04b00; }} .ready-for-review {{ color: #167044; }} .blocked {{ color: #b12c25; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 20px 0; }} .metric {{ background: #f4f7fb; border-radius: 10px; padding: 14px; }} .metric strong {{ display: block; font-size: 1.35rem; }}
    table {{ border-collapse: collapse; width: 100%; }} td, th {{ padding: 10px; border-bottom: 1px solid #e3e7ef; text-align: left; }} .finding {{ border-left: 4px solid #d4931d; background: #fffaf0; padding: 18px; border-radius: 0 10px 10px 0; margin-top: 16px; }} .finding.critical {{ border-color: #bd3b36; background: #fff4f3; }} .label {{ color: #536076; font-weight: 700; }} .evidence {{ background: #f2f4f8; padding: 10px; border-radius: 6px; white-space: pre-wrap; overflow-wrap: anywhere; }} .small {{ color: #536076; font-size: .9rem; }}
  </style>
</head>
<body><main>
  <h1>AIR-DV</h1>
  <p class="subtitle">Check what an AI system can reliably receive from a document before it enters a vector database, knowledge graph, or general AI workflow.</p>
  {body}
</main></body></html>"""


def _upload_panel(error: str | None = None) -> str:
    notice = f'<p class="notice">{html.escape(error)}</p>' if error else ""
    return f"""<section class="card"><h2>Analyse a document</h2>
      <p class="small">Your file is processed locally and deleted immediately after analysis.</p>{notice}
      <form action="/analyse" method="post" enctype="multipart/form-data" class="upload">
        <label for="document">Choose a file</label>
        <input id="document" name="document" type="file" accept=".md,.docx,.pdf,.xlsx" required>
        <p class="small">Markdown, Word, PDF, or Excel · maximum 50 MB</p>
        <button type="submit">Analyse document</button>
      </form></section>"""


def _result_panel(result: AnalysisResult) -> str:
    counts = {severity: len(result.findings_by_severity(severity)) for severity in Severity}
    status = _status(result)
    findings = "".join(_finding_card(number, finding) for number, finding in enumerate(result.findings, 1))
    if not findings:
        findings = "<p>No deterministic AI-readiness issues were identified.</p>"
    overview = "".join(
        f"<tr><td>{html.escape(outcome.name)}</td><td>{html.escape(_outcome_text(outcome.status, outcome.finding_count))}</td></tr>"
        for outcome in check_outcomes(result)
    )
    return f"""<section class="card"><p class="status {status.lower().replace(' ', '-')}">STATUS: {status}</p>
      <h2>{html.escape(result.document.filename)}</h2>
      <p class="small">{html.escape(_format_name(result.document.file_type))} · Extraction: {'Successful' if result.document.extraction_succeeded else 'Failed'}</p>
      <div class="summary"><div class="metric"><strong>{len(result.findings)}</strong>issues</div><div class="metric"><strong>{counts[Severity.CRITICAL]}</strong>critical</div><div class="metric"><strong>{counts[Severity.WARNING]}</strong>warnings</div></div>
      <h2>Check overview</h2><table><tbody>{overview}</tbody></table>
      <h2 style="margin-top:28px">Issues to fix</h2>{findings}
      <p><a class="button" href="/">Analyse another document</a></p></section>"""


def _finding_card(number: int, finding: Finding) -> str:
    location = _location(finding)
    return f"""<article class="finding {finding.severity.value}"><strong>{number}. {html.escape(finding.title)}</strong>
      <p><span class="label">Where:</span> {html.escape(location)}<br><span class="label">Owner:</span> {html.escape(_owner(finding))}</p>
      <p><span class="label">Why:</span> {html.escape(finding.why_it_matters)}</p>
      <p><span class="label">Suggested change:</span> {html.escape(suggested_change(finding))}</p>
      <p class="label">Evidence</p><div class="evidence">{html.escape(finding.evidence.excerpt)}</div></article>"""


def _status(result: AnalysisResult) -> str:
    if not result.document.extraction_succeeded:
        return "BLOCKED"
    return "NEEDS ATTENTION" if result.findings else "READY FOR REVIEW"


def _outcome_text(status: str, count: int) -> str:
    return f"Needs attention ({count})" if status == "Needs attention" else status


def _format_name(file_type: str) -> str:
    return {"md": "Markdown", "docx": "Word", "pdf": "PDF", "xlsx": "Excel"}[file_type]


def _owner(finding: Finding) -> str:
    return {"content_owner": "Content owner", "platform_team": "Platform team", "shared": "Content owner and platform team"}[finding.owner.value]


def _location(finding: Finding) -> str:
    location = finding.evidence.location
    if location.paragraph_index:
        return f"Word paragraph {location.paragraph_index}"
    if location.page_number:
        return f"PDF page {location.page_number}"
    if location.sheet_name and location.cell_range:
        return f"Sheet {location.sheet_name}, cells {location.cell_range}"
    if location.line_start:
        return f"Markdown line {location.line_start}"
    return location.label


app = create_app()


def main() -> None:
    """Run AIR-DV's local web interface."""

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
