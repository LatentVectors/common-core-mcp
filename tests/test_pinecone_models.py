"""Unit tests for Pinecone Pydantic models."""

from __future__ import annotations

import json

import pytest

from tools.pinecone_models import PineconeRecord, ProcessedStandardSet


class TestEducationLevelsProcessing:
    """Test education_levels field validator."""

    def test_simple_array(self):
        """Test simple array without comma-separated values."""
        record = PineconeRecord(
            **{"_id": "test-id"},
            content="Test content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01", "02"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="test-id",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
        )
        assert record.education_levels == ["01", "02"]

    def test_comma_separated_strings(self):
        """Test array with comma-separated values."""
        record = PineconeRecord(
            **{"_id": "test-id"},
            content="Test content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01,02", "02", "03"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="test-id",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
        )
        assert record.education_levels == ["01", "02", "03"]

    def test_high_school_range(self):
        """Test high school grade levels."""
        record = PineconeRecord(
            **{"_id": "test-id"},
            content="Test content",
            standard_set_id="set-1",
            standard_set_title="High School",
            subject="Math",
            education_levels=["09,10,11,12"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="test-id",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
        )
        assert record.education_levels == ["09", "10", "11", "12"]

    def test_empty_array(self):
        """Test empty array."""
        record = PineconeRecord(
            **{"_id": "test-id"},
            content="Test content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=[],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="test-id",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
        )
        assert record.education_levels == []

    def test_whitespace_handling(self):
        """Test that whitespace is stripped."""
        record = PineconeRecord(
            **{"_id": "test-id"},
            content="Test content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01 , 02", " 03 "],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="test-id",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
        )
        assert record.education_levels == ["01", "02", "03"]


class TestParentIdNullHandling:
    """Test that parent_id null is properly serialized."""

    def test_root_node_parent_id_null(self):
        """Test root node has parent_id as null."""
        record = PineconeRecord(
            **{"_id": "root-id"},
            content="Root content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=False,
            is_root=True,
            parent_id=None,
            root_id="root-id",
            ancestor_ids=[],
            child_ids=["child-1"],
            sibling_count=0,
        )
        assert record.parent_id is None

        # Test JSON serialization preserves null
        json_str = record.model_dump_json()
        data = json.loads(json_str)
        assert data["parent_id"] is None

    def test_child_node_parent_id_set(self):
        """Test child node has parent_id set."""
        record = PineconeRecord(
            **{"_id": "child-id"},
            content="Child content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=1,
            is_leaf=True,
            is_root=False,
            parent_id="parent-id",
            root_id="root-id",
            ancestor_ids=["root-id"],
            child_ids=[],
            sibling_count=0,
        )
        assert record.parent_id == "parent-id"

        # Test JSON serialization
        json_str = record.model_dump_json()
        data = json.loads(json_str)
        assert data["parent_id"] == "parent-id"


class TestOptionalFields:
    """Test optional fields can be omitted."""

    def test_all_optional_fields_omitted(self):
        """Test record with all optional fields omitted."""
        record = PineconeRecord(
            **{"_id": "test-id"},
            content="Test content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="test-id",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
        )
        assert record.normalized_subject is None
        assert record.asn_identifier is None
        assert record.statement_notation is None
        assert record.statement_label is None
        assert record.publication_status is None

    def test_optional_fields_set(self):
        """Test record with optional fields set."""
        record = PineconeRecord(
            **{"_id": "test-id"},
            content="Test content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            normalized_subject="Math",
            education_levels=["01"],
            document_id="doc-1",
            document_valid="2021",
            publication_status="Published",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            asn_identifier="S12345",
            statement_notation="1.G.K",
            statement_label="Standard",
            depth=1,
            is_leaf=True,
            is_root=False,
            parent_id="parent-id",
            root_id="root-id",
            ancestor_ids=["root-id"],
            child_ids=[],
            sibling_count=1,
        )
        assert record.normalized_subject == "Math"
        assert record.asn_identifier == "S12345"
        assert record.statement_notation == "1.G.K"
        assert record.statement_label == "Standard"
        assert record.publication_status == "Published"


class TestProcessedStandardSet:
    """Test ProcessedStandardSet container model."""

    def test_empty_records(self):
        """Test ProcessedStandardSet with empty records."""
        processed = ProcessedStandardSet(records=[])
        assert processed.records == []

    def test_multiple_records(self):
        """Test ProcessedStandardSet with multiple records."""
        record1 = PineconeRecord(
            **{"_id": "id-1"},
            content="Content 1",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="id-1",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
        )
        record2 = PineconeRecord(
            **{"_id": "id-2"},
            content="Content 2",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=1,
            is_leaf=True,
            is_root=False,
            parent_id="id-1",
            root_id="id-1",
            ancestor_ids=["id-1"],
            child_ids=[],
            sibling_count=0,
        )
        processed = ProcessedStandardSet(records=[record1, record2])
        assert len(processed.records) == 2
        assert processed.records[0].id == "id-1"
        assert processed.records[1].id == "id-2"

    def test_json_serialization(self):
        """Test JSON serialization of ProcessedStandardSet."""
        record = PineconeRecord(
            **{"_id": "test-id"},
            content="Test content",
            standard_set_id="set-1",
            standard_set_title="Grade 1",
            subject="Math",
            education_levels=["01"],
            document_id="doc-1",
            document_valid="2021",
            jurisdiction_id="jur-1",
            jurisdiction_title="Wyoming",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="test-id",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
        )
        processed = ProcessedStandardSet(records=[record])
        json_str = processed.model_dump_json(by_alias=True)
        data = json.loads(json_str)
        assert "records" in data
        assert len(data["records"]) == 1
        assert data["records"][0]["_id"] == "test-id"
        assert data["records"][0]["parent_id"] is None  # Verify null handling

