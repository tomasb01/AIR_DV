"""Tests for Confluence Data Center page URL handling and local OAuth settings."""

import os
import unittest
from unittest.mock import patch

from air_dv.confluence import ConfluenceOAuthConfig, ConfluencePageUrlError, parse_confluence_page_url


class ConfluencePageUrlTests(unittest.TestCase):
    def test_parses_the_data_center_page_url_shape(self) -> None:
        page = parse_confluence_page_url(
            "https://wiki.example.com/confluence/spaces/NCL/pages/5422764848/TO-BE++PSD2+FinAPI+v2"
        )

        self.assertEqual(page.base_url, "https://wiki.example.com/confluence")
        self.assertEqual(page.space_key, "NCL")
        self.assertEqual(page.page_id, "5422764848")
        self.assertEqual(page.title, "TO-BE  PSD2 FinAPI v2")

    def test_rejects_a_non_page_or_non_https_url(self) -> None:
        with self.assertRaisesRegex(ConfluencePageUrlError, "full HTTPS"):
            parse_confluence_page_url("http://wiki.example.com/confluence/spaces/NCL/pages/42/Page")
        with self.assertRaisesRegex(ConfluencePageUrlError, "containing /spaces"):
            parse_confluence_page_url("https://wiki.example.com/confluence/display/NCL/Page")


class ConfluenceOAuthConfigTests(unittest.TestCase):
    def test_reports_missing_local_oauth_configuration_without_reading_secrets(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = ConfluenceOAuthConfig.from_environment()

        self.assertFalse(config.is_configured)
        self.assertEqual(
            config.missing_fields,
            ("client ID", "authorization URL", "token URL", "read-only scope"),
        )
