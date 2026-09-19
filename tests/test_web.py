"""Browser-style tests for the local AIR-DV upload UI."""

import unittest
from pathlib import Path
import re

from fastapi.testclient import TestClient

from air_dv.web import create_app


class WebTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())
        self.fixture_directory = Path(__file__).parent / "fixtures" / "markdown"

    def test_shows_an_upload_page(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Analyse a document", response.text)
        self.assertIn("processed locally and deleted", response.text)
        self.assertIn("Confluence page URL", response.text)

    def test_validates_a_confluence_page_url_without_sending_page_content(self) -> None:
        response = self.client.post(
            "/confluence/prepare",
            data={
                "page_url": (
                    "https://wiki.example.com/confluence/spaces/NCL/pages/5422764848/Example-page"
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Confluence OAuth is not configured locally", response.text)
        self.assertIn("No credentials or page content were sent", response.text)

    def test_uploads_a_supported_document_and_renders_actionable_result(self) -> None:
        fixture_path = self.fixture_directory / "missing_image_alt.md"
        with fixture_path.open("rb") as fixture:
            response = self.client.post(
                "/analyse",
                files={"document": (fixture_path.name, fixture, "text/markdown")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("STATUS: NEEDS ATTENTION", response.text)
        self.assertIn("Image has no text equivalent", response.text)
        self.assertIn("Markdown line 3", response.text)
        self.assertIn("Suggested change", response.text)
        self.assertIn("What AI sees", response.text)
        self.assertIn("This is the text-only normalized view", response.text)

        export_id = re.search(r"/exports/([^/]+)/report", response.text).group(1)
        report = self.client.get(f"/exports/{export_id}/report")
        ai_view = self.client.get(f"/exports/{export_id}/ai-view")
        json_export = self.client.get(f"/exports/{export_id}/json")

        self.assertEqual(report.status_code, 200)
        self.assertIn("# AIR-DV result", report.text)
        self.assertEqual(ai_view.status_code, 200)
        self.assertIn("![](architecture.png)", ai_view.text)
        self.assertEqual(json_export.status_code, 200)
        self.assertIn('"findings"', json_export.text)

    def test_rejects_an_expired_or_unknown_export(self) -> None:
        response = self.client.get("/exports/not-an-export/report")

        self.assertEqual(response.status_code, 404)
        self.assertIn("no longer available", response.text)

    def test_rejects_an_unsupported_upload(self) -> None:
        response = self.client.post(
            "/analyse",
            files={"document": ("notes.txt", b"Not supported", "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Choose a Markdown, Word, PDF, or Excel file", response.text)
