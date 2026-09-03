"""Command-line interface for AIR-DV analysis and local report exports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from air_dv.analysis import analyse_file
from air_dv.reporting import render_markdown_report, render_terminal_summary


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the AIR-DV CLI and return a process-compatible exit code."""

    parser = _build_parser()
    parsed_arguments = parser.parse_args(arguments)

    try:
        result = analyse_file(parsed_arguments.source)
        saved_exports = []
        if parsed_arguments.report:
            Path(parsed_arguments.report).write_text(render_markdown_report(result), encoding="utf-8")
            saved_exports.append(f"Report: {parsed_arguments.report}")
        if parsed_arguments.ai_view:
            Path(parsed_arguments.ai_view).write_text(result.normalized_content, encoding="utf-8")
            saved_exports.append(f"AI view: {parsed_arguments.ai_view}")
        if parsed_arguments.json_report:
            Path(parsed_arguments.json_report).write_text(
                json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            saved_exports.append(f"JSON: {parsed_arguments.json_report}")
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(render_terminal_summary(result, saved_exports))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check whether a document is ready for general AI use.")
    commands = parser.add_subparsers(dest="command", required=True)
    analyse_parser = commands.add_parser("analyse", help="Analyse a Markdown, Word, or Excel document.")
    analyse_parser.add_argument("source", help="Path to a .md, .docx, or .xlsx file.")
    analyse_parser.add_argument("--report", help="Write a Markdown findings report to this path.")
    analyse_parser.add_argument("--ai-view", help="Write normalized AI-view content to this path.")
    analyse_parser.add_argument("--json", dest="json_report", help="Write the full JSON result to this path.")
    return parser
