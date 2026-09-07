"""Browser-style tests for the local AIR-DV upload UI."""

import unittest
from pathlib import Path

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

    def test_rejects_an_unsupported_upload(self) -> None:
        response = self.client.post(
            "/analyse",
            files={"document": ("notes.txt", b"Not supported", "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Choose a Markdown, Word, PDF, or Excel file", response.text)
