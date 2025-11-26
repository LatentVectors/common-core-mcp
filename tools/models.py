"""Pydantic models for Common Standards Project API data structures."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class CSPBaseModel(BaseModel):
    """Base model for all CSP API models with extra fields allowed."""

    model_config = ConfigDict(extra="allow")


# ============================================================================
# Jurisdiction List Models
# ============================================================================


class Jurisdiction(CSPBaseModel):
    """Basic jurisdiction information from the jurisdictions list endpoint."""

    id: str
    title: str
    type: str  # "school", "organization", "state", "nation"


class JurisdictionsResponse(CSPBaseModel):
    """API response wrapper for jurisdictions list."""

    data: list[Jurisdiction]


# ============================================================================
# Jurisdiction Details Models
# ============================================================================


class Document(CSPBaseModel):
    """Standard document metadata."""

    id: Optional[str] = None
    title: str
    valid: Optional[str] = None  # Year as string
    sourceURL: Optional[str] = None
    asnIdentifier: Optional[str] = None
    publicationStatus: Optional[str] = None


class StandardSetReference(CSPBaseModel):
    """Reference to a standard set (metadata only, not full content)."""

    id: str
    title: str
    subject: str
    educationLevels: list[str]
    document: Document


class JurisdictionDetails(CSPBaseModel):
    """Full jurisdiction details including standard set references."""

    id: str
    title: str
    type: str  # "school", "organization", "state", "nation"
    standardSets: list[StandardSetReference]


class JurisdictionDetailsResponse(CSPBaseModel):
    """API response wrapper for jurisdiction details."""

    data: JurisdictionDetails


# ============================================================================
# Standard Set Models
# ============================================================================


class License(CSPBaseModel):
    """License information for a standard set."""

    title: str
    URL: str
    rightsHolder: str


class JurisdictionRef(CSPBaseModel):
    """Simple jurisdiction reference within a standard set."""

    id: str
    title: str


class Standard(CSPBaseModel):
    """Individual standard within a standard set."""

    id: str
    asnIdentifier: Optional[str] = None
    position: int
    depth: int
    statementNotation: Optional[str] = None
    description: str
    ancestorIds: list[str]
    parentId: Optional[str] = None
    statementLabel: Optional[str] = None  # e.g., "Standard", "Benchmark"
    educationLevels: Optional[list[str]] = None


class StandardSet(CSPBaseModel):
    """Full standard set data including all standards."""

    id: str
    title: str
    subject: str
    normalizedSubject: Optional[str] = None
    educationLevels: list[str]
    license: License
    document: Document
    jurisdiction: JurisdictionRef
    standards: dict[str, Standard]  # GUID -> Standard mapping
    cspStatus: Optional[dict[str, Any]] = None


class StandardSetResponse(CSPBaseModel):
    """API response wrapper for standard set."""

    data: StandardSet
