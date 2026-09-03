"""Core, extractor-independent models for document analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Impact level assigned to a finding."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class FindingOwner(str, Enum):
    """Person or team expected to resolve a finding."""

    CONTENT_OWNER = "content_owner"
    PLATFORM_TEAM = "platform_team"
    SHARED = "shared"


class FindingCategory(str, Enum):
    """Distinguishes source-content issues from ingestion limitations."""

    CONTENT_ISSUE = "content_issue"
    INGESTION_LIMITATION = "ingestion_limitation"


class BlockType(str, Enum):
    """Semantic block types retained during normalization."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    IMAGE = "image"
    UNSUPPORTED_OBJECT = "unsupported_object"


@dataclass(frozen=True)
class SourceLocation:
    """A stable location in a source document or normalized output."""

    label: str
    line_start: int | None = None
    line_end: int | None = None
    sheet_name: str | None = None

    def __post_init__(self) -> None:
        if self.line_start is not None and self.line_start < 1:
            raise ValueError("line_start must be greater than zero")
        if self.line_end is not None and self.line_end < 1:
            raise ValueError("line_end must be greater than zero")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end cannot be earlier than line_start")


@dataclass(frozen=True)
class Evidence:
    """The extractable content that supports a finding."""

    excerpt: str
    location: SourceLocation


@dataclass(frozen=True)
class Block:
    """A semantically identified part of normalized document content."""

    type: BlockType
    text: str
    location: SourceLocation
    heading_level: int | None = None

    def __post_init__(self) -> None:
        if self.heading_level is not None and not 1 <= self.heading_level <= 6:
            raise ValueError("heading_level must be between 1 and 6")
        if self.type is BlockType.HEADING and self.heading_level is None:
            raise ValueError("heading blocks must include a heading_level")


@dataclass(frozen=True)
class NormalizedDocument:
    """Extractor-independent content used by checks and UI rendering."""

    document: DocumentSummary
    content: str
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class Finding:
    """A single actionable result from a deterministic document check."""

    id: str
    title: str
    severity: Severity
    category: FindingCategory
    owner: FindingOwner
    why_it_matters: str
    recommendation: str
    evidence: Evidence


@dataclass(frozen=True)
class DocumentSummary:
    """Basic identity and extraction status for an analyzed document."""

    filename: str
    file_type: str
    extraction_succeeded: bool
    extraction_notes: tuple[str, ...] = ()
    source_metadata: tuple[tuple[str, str], ...] = ()


@dataclass
class AnalysisResult:
    """Complete output of an analysis, independent of CLI or web UI."""

    document: DocumentSummary
    normalized_content: str
    findings: list[Finding] = field(default_factory=list)

    def findings_by_severity(self, severity: Severity) -> list[Finding]:
        """Return findings with the requested severity."""

        return [finding for finding in self.findings if finding.severity is severity]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for reports and APIs."""

        return _serialize(asdict(self))


def _serialize(value: Any) -> Any:
    """Convert enums nested in dataclass output into their string values."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    return value
