"""Confluence Data Center URL and OAuth configuration primitives.

The actual OAuth callback and page retrieval are intentionally separate from these
pure local helpers, so URL handling never depends on credentials or network access.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import unquote_plus, urlparse


class ConfluencePageUrlError(ValueError):
    """Raised when a URL is not a supported Confluence Data Center page URL."""


@dataclass(frozen=True)
class ConfluencePageReference:
    """A validated Confluence page identity extracted from one page URL."""

    base_url: str
    space_key: str
    page_id: str
    title: str | None = None


@dataclass(frozen=True)
class ConfluenceOAuthConfig:
    """Local-only configuration required for a future OAuth authorization flow."""

    client_id: str | None
    authorization_url: str | None
    token_url: str | None
    scope: str | None

    @classmethod
    def from_environment(cls) -> "ConfluenceOAuthConfig":
        """Read non-secret OAuth connection settings from the local environment."""

        return cls(
            client_id=os.environ.get("AIR_DV_CONFLUENCE_OAUTH_CLIENT_ID"),
            authorization_url=os.environ.get("AIR_DV_CONFLUENCE_OAUTH_AUTHORIZATION_URL"),
            token_url=os.environ.get("AIR_DV_CONFLUENCE_OAUTH_TOKEN_URL"),
            scope=os.environ.get("AIR_DV_CONFLUENCE_OAUTH_SCOPE"),
        )

    @property
    def is_configured(self) -> bool:
        """Return whether the minimum safe OAuth settings have been supplied locally."""

        return not self.missing_fields

    @property
    def missing_fields(self) -> tuple[str, ...]:
        """Return display-safe names of absent connection settings."""

        fields = (
            ("client ID", self.client_id),
            ("authorization URL", self.authorization_url),
            ("token URL", self.token_url),
            ("read-only scope", self.scope),
        )
        return tuple(name for name, value in fields if not value)


def parse_confluence_page_url(value: str) -> ConfluencePageReference:
    """Parse one HTTPS Data Center page URL using the stable page-ID route."""

    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ConfluencePageUrlError("Enter a full HTTPS Confluence page URL.")

    path_parts = [part for part in parsed.path.split("/") if part]
    try:
        spaces_index = path_parts.index("spaces")
        pages_index = spaces_index + 2
        if path_parts[pages_index] != "pages":
            raise ValueError
        space_key = path_parts[spaces_index + 1]
        page_id = path_parts[pages_index + 1]
    except (IndexError, ValueError):
        raise ConfluencePageUrlError(
            "Enter a Confluence page URL containing /spaces/<space>/pages/<page-id>."
        ) from None

    if not page_id.isdecimal():
        raise ConfluencePageUrlError("The Confluence page ID must be numeric.")

    base_path = "/" + "/".join(path_parts[:spaces_index])
    base_url = f"{parsed.scheme}://{parsed.netloc}{base_path.rstrip('/')}"
    title = unquote_plus(path_parts[pages_index + 2]) if len(path_parts) > pages_index + 2 else None
    return ConfluencePageReference(
        base_url=base_url,
        space_key=space_key,
        page_id=page_id,
        title=title or None,
    )
