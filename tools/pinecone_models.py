"""Pydantic models for Pinecone-processed standard records."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PineconeRecord(BaseModel):
    """A single standard record ready for Pinecone upsert."""

    model_config = ConfigDict(
        json_encoders={
            # Ensure parent_id null is serialized as null, not omitted
            type(None): lambda v: None,
        },
        # Use snake_case for field names (matches JSON schema)
        populate_by_name=True,
    )

    # Core identifier - use alias to serialize as _id
    id: str = Field(alias="_id", serialization_alias="_id")

    # Content for embedding
    content: str

    # Standard Set Context
    standard_set_id: str
    standard_set_title: str
    subject: str
    normalized_subject: str | None = None
    education_levels: list[str]
    document_id: str
    document_valid: str
    publication_status: str | None = None
    jurisdiction_id: str
    jurisdiction_title: str

    # Standard Identity & Position
    asn_identifier: str | None = None
    statement_notation: str | None = None
    statement_label: str | None = None
    depth: int
    is_leaf: bool
    is_root: bool

    # Hierarchy Relationships
    parent_id: str | None = None  # null for root nodes
    root_id: str
    ancestor_ids: list[str]
    child_ids: list[str]
    sibling_count: int

    @field_validator("education_levels", mode="before")
    @classmethod
    def process_education_levels(cls, v: Any) -> list[str]:
        """
        Process education_levels: split comma-separated strings, flatten, dedupe.

        Handles cases where source data has comma-separated values within array
        elements (e.g., ["01,02"] instead of ["01", "02"]).

        Args:
            v: Input value (list[str] or list with comma-separated strings)

        Returns:
            Flattened, deduplicated list of grade level strings
        """
        if not isinstance(v, list):
            return []

        # Split comma-separated strings and flatten
        flattened: list[str] = []
        for item in v:
            if isinstance(item, str):
                # Split on commas and strip whitespace
                split_items = [s.strip() for s in item.split(",") if s.strip()]
                flattened.extend(split_items)

        # Deduplicate while preserving order
        seen: set[str] = set()
        result: list[str] = []
        for item in flattened:
            if item not in seen:
                seen.add(item)
                result.append(item)

        return result


class ProcessedStandardSet(BaseModel):
    """Container for processed standard set records ready for Pinecone."""

    records: list[PineconeRecord]
