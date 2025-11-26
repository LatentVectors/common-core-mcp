"""Processor for transforming standard sets into Pinecone-ready format."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from tools.config import get_settings
from tools.models import StandardSet, StandardSetResponse
from tools.pinecone_models import PineconeRecord, ProcessedStandardSet

if TYPE_CHECKING:
    from collections.abc import Mapping

settings = get_settings()


class StandardSetProcessor:
    """Processes standard sets into Pinecone-ready format."""

    def __init__(self):
        """Initialize the processor."""
        self.id_to_standard: dict[str, dict] = {}
        self.parent_to_children: dict[str | None, list[str]] = {}
        self.leaf_nodes: set[str] = set()
        self.root_nodes: set[str] = set()

    def process_standard_set(self, standard_set: StandardSet) -> ProcessedStandardSet:
        """
        Process a standard set into Pinecone-ready records.

        Args:
            standard_set: The StandardSet model from the API

        Returns:
            ProcessedStandardSet with all records ready for Pinecone
        """
        # Build relationship maps from all standards
        self._build_relationship_maps(standard_set.standards)

        # Process each standard into a PineconeRecord
        records = []
        for standard_id, standard in standard_set.standards.items():
            record = self._transform_standard(standard, standard_set)
            records.append(record)

        return ProcessedStandardSet(records=records)

    def _build_relationship_maps(self, standards: dict[str, Standard]) -> None:
        """
        Build helper data structures from all standards in the set.

        Args:
            standards: Dictionary mapping standard ID to Standard object
        """
        # Convert to dict format for easier manipulation
        standards_dict = {
            std_id: standard.model_dump() for std_id, standard in standards.items()
        }

        # Build ID-to-standard map
        self.id_to_standard = self._build_id_to_standard_map(standards_dict)

        # Build parent-to-children map (sorted by position)
        self.parent_to_children = self._build_parent_to_children_map(standards_dict)

        # Identify leaf nodes
        self.leaf_nodes = self._identify_leaf_nodes(standards_dict)

        # Identify root nodes
        self.root_nodes = self._identify_root_nodes(standards_dict)

    def _build_id_to_standard_map(
        self, standards: dict[str, dict]
    ) -> dict[str, dict]:
        """Build map of id -> standard object."""
        return {std_id: std for std_id, std in standards.items()}

    def _build_parent_to_children_map(
        self, standards: dict[str, dict]
    ) -> dict[str | None, list[str]]:
        """
        Build map of parentId -> [child_ids], sorted by position ascending.

        Args:
            standards: Dictionary of standard ID to standard dict

        Returns:
            Dictionary mapping parent ID (or None for roots) to sorted list of child IDs
        """
        parent_map: dict[str | None, list[tuple[int, str]]] = {}

        for std_id, std in standards.items():
            parent_id = std.get("parentId")
            position = std.get("position", 0)

            if parent_id not in parent_map:
                parent_map[parent_id] = []
            parent_map[parent_id].append((position, std_id))

        # Sort each list by position and extract just the IDs
        result: dict[str | None, list[str]] = {}
        for parent_id, children in parent_map.items():
            sorted_children = sorted(children, key=lambda x: x[0])
            result[parent_id] = [std_id for _, std_id in sorted_children]

        return result

    def _identify_leaf_nodes(self, standards: dict[str, dict]) -> set[str]:
        """
        Identify leaf nodes: standards whose ID does NOT appear as any standard's parentId.

        Args:
            standards: Dictionary of standard ID to standard dict

        Returns:
            Set of standard IDs that are leaf nodes
        """
        all_ids = set(standards.keys())
        parent_ids = {std.get("parentId") for std in standards.values() if std.get("parentId") is not None}

        # Leaf nodes are IDs that are NOT in parent_ids
        return all_ids - parent_ids

    def _identify_root_nodes(self, standards: dict[str, dict]) -> set[str]:
        """
        Identify root nodes: standards where parentId is null.

        Args:
            standards: Dictionary of standard ID to standard dict

        Returns:
            Set of standard IDs that are root nodes
        """
        return {
            std_id
            for std_id, std in standards.items()
            if std.get("parentId") is None
        }

    def find_root_id(self, standard: dict, id_to_standard: dict[str, dict]) -> str:
        """
        Walk up the parent chain to find the root ancestor.

        Args:
            standard: The standard dict to find root for
            id_to_standard: Map of ID to standard dict

        Returns:
            The root ancestor's ID
        """
        current = standard
        visited = set()  # Prevent infinite loops from bad data

        while current.get("parentId") is not None:
            parent_id = current["parentId"]
            if parent_id in visited:
                break  # Circular reference protection
            visited.add(parent_id)

            if parent_id not in id_to_standard:
                break  # Parent not found, use current as root
            current = id_to_standard[parent_id]

        return current["id"]

    def build_ordered_ancestors(
        self, standard: dict, id_to_standard: dict[str, dict]
    ) -> list[str]:
        """
        Build ancestor list ordered from root (index 0) to immediate parent (last index).

        Args:
            standard: The standard dict to build ancestors for
            id_to_standard: Map of ID to standard dict

        Returns:
            List of ancestor IDs ordered root -> immediate parent
        """
        ancestors = []
        current_id = standard.get("parentId")
        visited = set()

        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            if current_id in id_to_standard:
                ancestors.append(current_id)
                current_id = id_to_standard[current_id].get("parentId")
            else:
                break

        ancestors.reverse()  # Now ordered root → immediate parent
        return ancestors

    def _compute_sibling_count(self, standard: dict) -> int:
        """
        Count standards with same parent_id, excluding self.

        Args:
            standard: The standard dict

        Returns:
            Number of siblings (excluding self)
        """
        parent_id = standard.get("parentId")
        if parent_id not in self.parent_to_children:
            return 0

        siblings = self.parent_to_children[parent_id]
        # Exclude self from count
        return len([s for s in siblings if s != standard["id"]])

    def _build_content_text(self, standard: dict) -> str:
        """
        Generate content text block with full hierarchy.

        Format: "Depth N (notation): description" for each ancestor and self.

        Args:
            standard: The standard dict

        Returns:
            Multi-line text block with full hierarchy
        """
        # Build ordered ancestor chain
        ancestor_ids = self.build_ordered_ancestors(standard, self.id_to_standard)

        # Build lines from root to current standard
        lines = []

        # Add ancestor lines
        for ancestor_id in ancestor_ids:
            ancestor = self.id_to_standard[ancestor_id]
            depth = ancestor.get("depth", 0)
            description = ancestor.get("description", "")
            notation = ancestor.get("statementNotation")

            if notation:
                lines.append(f"Depth {depth} ({notation}): {description}")
            else:
                lines.append(f"Depth {depth}: {description}")

        # Add current standard line
        depth = standard.get("depth", 0)
        description = standard.get("description", "")
        notation = standard.get("statementNotation")

        if notation:
            lines.append(f"Depth {depth} ({notation}): {description}")
        else:
            lines.append(f"Depth {depth}: {description}")

        return "\n".join(lines)

    def _transform_standard(
        self, standard: Standard, standard_set: StandardSet
    ) -> PineconeRecord:
        """
        Transform a single standard into a PineconeRecord.

        Args:
            standard: The Standard object to transform
            standard_set: The parent StandardSet containing context

        Returns:
            PineconeRecord ready for Pinecone upsert
        """
        std_dict = standard.model_dump()

        # Compute hierarchy relationships
        is_root = std_dict.get("parentId") is None
        root_id = (
            std_dict["id"] if is_root else self.find_root_id(std_dict, self.id_to_standard)
        )
        ancestor_ids = self.build_ordered_ancestors(std_dict, self.id_to_standard)
        child_ids = self.parent_to_children.get(std_dict["id"], [])
        is_leaf = std_dict["id"] in self.leaf_nodes
        sibling_count = self._compute_sibling_count(std_dict)

        # Build content text
        content = self._build_content_text(std_dict)

        # Extract standard set context
        parent_id = std_dict.get("parentId")  # Keep as None if null

        # Build record with all fields
        # Note: Use "id" not "_id" - Pydantic handles serialization alias automatically
        record_data = {
            "id": std_dict["id"],
            "content": content,
            "standard_set_id": standard_set.id,
            "standard_set_title": standard_set.title,
            "subject": standard_set.subject,
            "normalized_subject": standard_set.normalizedSubject,  # Optional, can be None
            "education_levels": standard_set.educationLevels,
            "document_id": standard_set.document.id,
            "document_valid": standard_set.document.valid,
            "publication_status": standard_set.document.publicationStatus,  # Optional, can be None
            "jurisdiction_id": standard_set.jurisdiction.id,
            "jurisdiction_title": standard_set.jurisdiction.title,
            "depth": std_dict.get("depth", 0),
            "is_leaf": is_leaf,
            "is_root": is_root,
            "parent_id": parent_id,
            "root_id": root_id,
            "ancestor_ids": ancestor_ids,
            "child_ids": child_ids,
            "sibling_count": sibling_count,
        }

        # Add optional fields only if present
        if std_dict.get("asnIdentifier"):
            record_data["asn_identifier"] = std_dict["asnIdentifier"]
        if std_dict.get("statementNotation"):
            record_data["statement_notation"] = std_dict["statementNotation"]
        if std_dict.get("statementLabel"):
            record_data["statement_label"] = std_dict["statementLabel"]

        return PineconeRecord(**record_data)


def process_and_save(standard_set_id: str) -> Path:
    """
    Load data.json, process it, and save processed.json.

    Args:
        standard_set_id: The ID of the standard set to process

    Returns:
        Path to the saved processed.json file

    Raises:
        FileNotFoundError: If data.json doesn't exist
        ValueError: If JSON is invalid
    """
    # Locate data.json
    data_file = settings.standard_sets_dir / standard_set_id / "data.json"
    if not data_file.exists():
        logger.warning(f"data.json not found for set {standard_set_id}, skipping")
        raise FileNotFoundError(f"data.json not found for set {standard_set_id}")

    # Load and parse JSON
    try:
        with open(data_file, encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {data_file}: {e}") from e

    # Parse into Pydantic model
    try:
        response = StandardSetResponse(**raw_data)
        standard_set = response.data
    except Exception as e:
        raise ValueError(f"Failed to parse standard set data: {e}") from e

    # Process the standard set
    processor = StandardSetProcessor()
    processed_set = processor.process_standard_set(standard_set)

    # Save processed.json
    processed_file = settings.standard_sets_dir / standard_set_id / "processed.json"
    processed_file.parent.mkdir(parents=True, exist_ok=True)

    with open(processed_file, "w", encoding="utf-8") as f:
        json.dump(processed_set.model_dump(mode="json"), f, indent=2)

    logger.info(
        f"Processed {standard_set_id}: {len(processed_set.records)} records"
    )

    return processed_file

