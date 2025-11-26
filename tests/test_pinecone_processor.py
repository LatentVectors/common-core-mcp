"""Tests for Pinecone processor module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.models import Standard, StandardSet
from tools.pinecone_processor import StandardSetProcessor, process_and_save


@pytest.fixture
def sample_standard_set():
    """Create a sample standard set for testing."""
    # Create a simple hierarchy:
    # Root (depth 0): "Math"
    #   Child (depth 1, notation "1.1"): "Numbers"
    #     Child (depth 2, notation "1.1.A"): "Count to 10"
    root_id = "ROOT_ID"
    child1_id = "CHILD1_ID"
    child2_id = "CHILD2_ID"

    standards = {
        root_id: Standard(
            id=root_id,
            position=100000,
            depth=0,
            description="Math",
            statementLabel="Domain",
            ancestorIds=[],
            parentId=None,
        ),
        child1_id: Standard(
            id=child1_id,
            position=101000,
            depth=1,
            description="Numbers",
            statementNotation="1.1",
            statementLabel="Standard",
            ancestorIds=[root_id],
            parentId=root_id,
        ),
        child2_id: Standard(
            id=child2_id,
            position=102000,
            depth=2,
            description="Count to 10",
            statementNotation="1.1.A",
            statementLabel="Benchmark",
            ancestorIds=[root_id, child1_id],
            parentId=child1_id,
        ),
    }

    standard_set = StandardSet(
        id="SET_ID",
        title="Grade 1",
        subject="Mathematics",
        normalizedSubject="Math",
        educationLevels=["01"],
        license={
            "title": "CC BY",
            "URL": "https://example.com",
            "rightsHolder": "Test",
        },
        document={
            "id": "DOC_ID",
            "title": "Test Document",
            "valid": "2021",
            "publicationStatus": "Published",
        },
        jurisdiction={"id": "JUR_ID", "title": "Test State"},
        standards=standards,
    )

    return standard_set


class TestRelationshipMaps:
    """Test relationship map building (Task 3)."""

    def test_build_id_to_standard_map(self, sample_standard_set):
        """Test ID-to-standard map building."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }

        result = processor._build_id_to_standard_map(standards_dict)

        assert len(result) == 3
        assert "ROOT_ID" in result
        assert "CHILD1_ID" in result
        assert "CHILD2_ID" in result
        assert result["ROOT_ID"]["id"] == "ROOT_ID"

    def test_build_parent_to_children_map(self, sample_standard_set):
        """Test parent-to-children map building with position sorting."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }

        result = processor._build_parent_to_children_map(standards_dict)

        # Root should have one child
        assert None in result
        assert result[None] == ["ROOT_ID"]

        # Root should have child1 as child
        assert "ROOT_ID" in result
        assert result["ROOT_ID"] == ["CHILD1_ID"]

        # Child1 should have child2 as child
        assert "CHILD1_ID" in result
        assert result["CHILD1_ID"] == ["CHILD2_ID"]

        # Child2 should have no children
        assert "CHILD2_ID" not in result or result.get("CHILD2_ID") == []

    def test_identify_leaf_nodes(self, sample_standard_set):
        """Test leaf node identification."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }

        result = processor._identify_leaf_nodes(standards_dict)

        # Only child2 should be a leaf (no children)
        assert "CHILD2_ID" in result
        assert "ROOT_ID" not in result
        assert "CHILD1_ID" not in result

    def test_identify_root_nodes(self, sample_standard_set):
        """Test root node identification."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }

        result = processor._identify_root_nodes(standards_dict)

        # Only ROOT_ID should be a root
        assert "ROOT_ID" in result
        assert "CHILD1_ID" not in result
        assert "CHILD2_ID" not in result


class TestHierarchyFunctions:
    """Test hierarchy functions (Task 4)."""

    def test_find_root_id_for_root(self, sample_standard_set):
        """Test finding root ID for a root node."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }
        processor.id_to_standard = processor._build_id_to_standard_map(standards_dict)

        root_std = standards_dict["ROOT_ID"]
        root_id = processor.find_root_id(root_std, processor.id_to_standard)

        assert root_id == "ROOT_ID"

    def test_find_root_id_for_child(self, sample_standard_set):
        """Test finding root ID for a child node."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }
        processor.id_to_standard = processor._build_id_to_standard_map(standards_dict)

        child_std = standards_dict["CHILD2_ID"]
        root_id = processor.find_root_id(child_std, processor.id_to_standard)

        assert root_id == "ROOT_ID"

    def test_build_ordered_ancestors(self, sample_standard_set):
        """Test building ordered ancestor list."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }
        processor.id_to_standard = processor._build_id_to_standard_map(standards_dict)

        # For root, ancestors should be empty
        root_std = standards_dict["ROOT_ID"]
        ancestors = processor.build_ordered_ancestors(root_std, processor.id_to_standard)
        assert ancestors == []

        # For child1, ancestors should be [ROOT_ID]
        child1_std = standards_dict["CHILD1_ID"]
        ancestors = processor.build_ordered_ancestors(child1_std, processor.id_to_standard)
        assert ancestors == ["ROOT_ID"]

        # For child2, ancestors should be [ROOT_ID, CHILD1_ID]
        child2_std = standards_dict["CHILD2_ID"]
        ancestors = processor.build_ordered_ancestors(child2_std, processor.id_to_standard)
        assert ancestors == ["ROOT_ID", "CHILD1_ID"]

    def test_compute_sibling_count(self, sample_standard_set):
        """Test sibling count computation."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }
        processor.parent_to_children = processor._build_parent_to_children_map(standards_dict)

        # Root has no siblings
        root_std = standards_dict["ROOT_ID"]
        count = processor._compute_sibling_count(root_std)
        assert count == 0

        # Child1 has no siblings
        child1_std = standards_dict["CHILD1_ID"]
        count = processor._compute_sibling_count(child1_std)
        assert count == 0

        # Child2 has no siblings
        child2_std = standards_dict["CHILD2_ID"]
        count = processor._compute_sibling_count(child2_std)
        assert count == 0


class TestContentGeneration:
    """Test content text generation (Task 5)."""

    def test_build_content_text_for_root(self, sample_standard_set):
        """Test content generation for root node."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }
        processor.id_to_standard = processor._build_id_to_standard_map(standards_dict)

        root_std = standards_dict["ROOT_ID"]
        content = processor._build_content_text(root_std)

        assert content == "Depth 0: Math"

    def test_build_content_text_for_child(self, sample_standard_set):
        """Test content generation for child node with notation."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }
        processor.id_to_standard = processor._build_id_to_standard_map(standards_dict)

        child1_std = standards_dict["CHILD1_ID"]
        content = processor._build_content_text(child1_std)

        expected = "Depth 0: Math\nDepth 1 (1.1): Numbers"
        assert content == expected

    def test_build_content_text_for_deep_child(self, sample_standard_set):
        """Test content generation for deep child node."""
        processor = StandardSetProcessor()
        standards_dict = {
            std_id: std.model_dump()
            for std_id, std in sample_standard_set.standards.items()
        }
        processor.id_to_standard = processor._build_id_to_standard_map(standards_dict)

        child2_std = standards_dict["CHILD2_ID"]
        content = processor._build_content_text(child2_std)

        expected = "Depth 0: Math\nDepth 1 (1.1): Numbers\nDepth 2 (1.1.A): Count to 10"
        assert content == expected

    def test_build_content_text_without_notation(self):
        """Test content generation without statement notation."""
        processor = StandardSetProcessor()
        
        # Create a standard without notation
        standard = {
            "id": "TEST_ID",
            "depth": 1,
            "description": "Test Description",
            "parentId": "PARENT_ID",
        }
        
        parent = {
            "id": "PARENT_ID",
            "depth": 0,
            "description": "Parent",
            "parentId": None,
        }
        
        processor.id_to_standard = {"TEST_ID": standard, "PARENT_ID": parent}
        
        content = processor._build_content_text(standard)
        
        expected = "Depth 0: Parent\nDepth 1: Test Description"
        assert content == expected


class TestRecordTransformation:
    """Test record transformation (Task 6)."""

    def test_transform_root_standard(self, sample_standard_set):
        """Test transforming a root standard."""
        processor = StandardSetProcessor()
        processor._build_relationship_maps(sample_standard_set.standards)

        root_standard = sample_standard_set.standards["ROOT_ID"]
        record = processor._transform_standard(root_standard, sample_standard_set)

        assert record.id == "ROOT_ID"
        assert record.is_root is True
        assert record.is_leaf is False
        assert record.parent_id is None
        assert record.root_id == "ROOT_ID"
        assert record.ancestor_ids == []
        assert record.depth == 0
        assert record.content == "Depth 0: Math"

    def test_transform_leaf_standard(self, sample_standard_set):
        """Test transforming a leaf standard."""
        processor = StandardSetProcessor()
        processor._build_relationship_maps(sample_standard_set.standards)

        leaf_standard = sample_standard_set.standards["CHILD2_ID"]
        record = processor._transform_standard(leaf_standard, sample_standard_set)

        assert record.id == "CHILD2_ID"
        assert record.is_root is False
        assert record.is_leaf is True
        assert record.parent_id == "CHILD1_ID"
        assert record.root_id == "ROOT_ID"
        assert record.ancestor_ids == ["ROOT_ID", "CHILD1_ID"]
        assert record.depth == 2
        assert "Depth 0: Math" in record.content
        assert "Depth 2 (1.1.A): Count to 10" in record.content

    def test_transform_standard_with_optional_fields(self, sample_standard_set):
        """Test transformation includes optional fields when present."""
        processor = StandardSetProcessor()
        processor._build_relationship_maps(sample_standard_set.standards)

        standard = sample_standard_set.standards["CHILD2_ID"]
        record = processor._transform_standard(standard, sample_standard_set)

        assert record.statement_notation == "1.1.A"
        assert record.statement_label == "Benchmark"

    def test_transform_standard_without_optional_fields(self):
        """Test transformation omits optional fields when missing."""
        # Create a minimal standard set
        standard = Standard(
            id="MIN_ID",
            position=100000,
            depth=0,
            description="Minimal",
            ancestorIds=[],
            parentId=None,
        )

        standard_set = StandardSet(
            id="SET_ID",
            title="Test",
            subject="Test",
            normalizedSubject="Test",
            educationLevels=["01"],
            license={"title": "CC", "URL": "https://example.com", "rightsHolder": "Test"},
            document={"id": "DOC", "title": "Doc", "valid": "2021", "publicationStatus": "Published"},
            jurisdiction={"id": "JUR", "title": "Jur"},
            standards={"MIN_ID": standard},
        )

        processor = StandardSetProcessor()
        processor._build_relationship_maps(standard_set.standards)

        record = processor._transform_standard(standard, standard_set)

        assert record.asn_identifier is None
        assert record.statement_notation is None
        assert record.statement_label is None

    def test_process_standard_set(self, sample_standard_set):
        """Test processing entire standard set."""
        processor = StandardSetProcessor()
        processed_set = processor.process_standard_set(sample_standard_set)

        assert len(processed_set.records) == 3
        assert all(isinstance(r, type(processed_set.records[0])) for r in processed_set.records)


class TestFileOperations:
    """Test file operations (Task 7)."""

    def test_process_and_save(self, tmp_path, sample_standard_set):
        """Test processing and saving to file."""
        # Create temporary directory structure
        set_dir = tmp_path / "standardSets" / "TEST_SET_ID"
        set_dir.mkdir(parents=True)

        # Save sample data.json
        data_file = set_dir / "data.json"
        response_data = {"data": sample_standard_set.model_dump(mode="json")}
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(response_data, f)

        # Mock the settings to use tmp_path
        from unittest.mock import patch
        from tools.config import ToolsSettings

        with patch("tools.pinecone_processor.settings") as mock_settings:
            mock_settings.standard_sets_dir = tmp_path / "standardSets"
            
            processed_file = process_and_save("TEST_SET_ID")

            assert processed_file.exists()
            assert processed_file.name == "processed.json"

            # Verify content
            with open(processed_file, encoding="utf-8") as f:
                data = json.load(f)

            assert "records" in data
            assert len(data["records"]) == 3

    def test_process_and_save_missing_file(self):
        """Test error handling for missing data.json."""
        from unittest.mock import patch
        from tools.config import ToolsSettings

        with patch("tools.pinecone_processor.settings") as mock_settings:
            mock_settings.standard_sets_dir = Path("/nonexistent/path")

            with pytest.raises(FileNotFoundError):
                process_and_save("NONEXISTENT_SET")

    def test_process_and_save_invalid_json(self, tmp_path):
        """Test error handling for invalid JSON."""
        set_dir = tmp_path / "standardSets" / "TEST_SET_ID"
        set_dir.mkdir(parents=True)

        # Write invalid JSON
        data_file = set_dir / "data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        from unittest.mock import patch

        with patch("tools.pinecone_processor.settings") as mock_settings:
            mock_settings.standard_sets_dir = tmp_path / "standardSets"

            with pytest.raises(ValueError, match="Invalid JSON"):
                process_and_save("TEST_SET_ID")

