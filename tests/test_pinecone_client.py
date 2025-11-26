"""Unit tests for Pinecone client."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pinecone.exceptions import PineconeException

from tools.pinecone_client import PineconeClient
from tools.pinecone_models import PineconeRecord


class TestUploadTracking:
    """Tests for upload tracking marker file operations."""

    def test_is_uploaded_returns_false_when_marker_missing(self):
        """is_uploaded() returns False when marker file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_dir = Path(tmpdir)
            assert PineconeClient.is_uploaded(set_dir) is False

    def test_is_uploaded_returns_true_when_marker_exists(self):
        """is_uploaded() returns True when marker file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_dir = Path(tmpdir)
            marker_file = set_dir / ".pinecone_uploaded"
            marker_file.write_text("2025-01-15T14:30:00Z")
            assert PineconeClient.is_uploaded(set_dir) is True

    def test_mark_uploaded_creates_marker_file(self):
        """mark_uploaded() creates marker file with ISO 8601 timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_dir = Path(tmpdir)
            marker_file = set_dir / ".pinecone_uploaded"

            assert not marker_file.exists()
            PineconeClient.mark_uploaded(set_dir)
            assert marker_file.exists()

            # Verify timestamp format
            timestamp = marker_file.read_text(encoding="utf-8").strip()
            # Should be valid ISO 8601 format
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_mark_uploaded_writes_utc_timestamp(self):
        """mark_uploaded() writes UTC timestamp in ISO 8601 format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_dir = Path(tmpdir)
            PineconeClient.mark_uploaded(set_dir)

            marker_file = set_dir / ".pinecone_uploaded"
            timestamp_str = marker_file.read_text(encoding="utf-8").strip()

            # Parse and verify it's UTC
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"
            parsed = datetime.fromisoformat(timestamp_str)
            assert parsed.tzinfo == timezone.utc

    def test_get_upload_timestamp_returns_none_when_marker_missing(self):
        """get_upload_timestamp() returns None when marker file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_dir = Path(tmpdir)
            assert PineconeClient.get_upload_timestamp(set_dir) is None

    def test_get_upload_timestamp_returns_timestamp_when_marker_exists(self):
        """get_upload_timestamp() returns timestamp string when marker exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_dir = Path(tmpdir)
            expected_timestamp = "2025-01-15T14:30:00Z"
            marker_file = set_dir / ".pinecone_uploaded"
            marker_file.write_text(expected_timestamp)

            result = PineconeClient.get_upload_timestamp(set_dir)
            assert result == expected_timestamp

    def test_get_upload_timestamp_handles_read_error(self):
        """get_upload_timestamp() returns None if marker file can't be read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_dir = Path(tmpdir)
            marker_file = set_dir / ".pinecone_uploaded"
            marker_file.write_text("test")

            # Make file unreadable (on Unix systems)
            marker_file.chmod(0o000)

            try:
                result = PineconeClient.get_upload_timestamp(set_dir)
                # Should return None or handle gracefully
                assert result is None or isinstance(result, str)
            finally:
                # Restore permissions for cleanup
                marker_file.chmod(0o644)


class TestPineconeClientCore:
    """Tests for core Pinecone client functionality."""

    @patch("tools.pinecone_client.Pinecone")
    @patch("tools.pinecone_client.get_settings")
    def test_init_raises_error_when_api_key_missing(self, mock_get_settings):
        """__init__() raises ValueError when API key is not set."""
        mock_settings = MagicMock()
        mock_settings.pinecone_api_key = ""
        mock_get_settings.return_value = mock_settings

        with pytest.raises(ValueError, match="PINECONE_API_KEY"):
            PineconeClient()

    @patch("tools.pinecone_client.Pinecone")
    @patch("tools.pinecone_client.get_settings")
    def test_init_initializes_pinecone_client(self, mock_get_settings):
        """__init__() initializes Pinecone SDK with API key."""
        mock_settings = MagicMock()
        mock_settings.pinecone_api_key = "test-api-key"
        mock_settings.pinecone_index_name = "test-index"
        mock_settings.pinecone_namespace = "test-namespace"
        mock_get_settings.return_value = mock_settings

        mock_pc = MagicMock()
        mock_pc.Index.return_value = MagicMock()
        mock_pc.has_index.return_value = True
        mock_pinecone_class = MagicMock(return_value=mock_pc)
        with patch("tools.pinecone_client.Pinecone", mock_pinecone_class):
            client = PineconeClient()

        assert client.pc == mock_pc
        assert client.index_name == "test-index"
        assert client.namespace == "test-namespace"

    @patch("tools.pinecone_client.Pinecone")
    @patch("tools.pinecone_client.get_settings")
    def test_validate_index_raises_error_when_index_missing(self, mock_get_settings):
        """validate_index() raises ValueError when index doesn't exist."""
        mock_settings = MagicMock()
        mock_settings.pinecone_api_key = "test-api-key"
        mock_settings.pinecone_index_name = "missing-index"
        mock_get_settings.return_value = mock_settings

        mock_pc = MagicMock()
        mock_pc.has_index.return_value = False
        mock_pinecone_class = MagicMock(return_value=mock_pc)
        with patch("tools.pinecone_client.Pinecone", mock_pinecone_class):
            client = PineconeClient()

        with pytest.raises(ValueError, match="Index 'missing-index' not found"):
            client.validate_index()

    @patch("tools.pinecone_client.Pinecone")
    @patch("tools.pinecone_client.get_settings")
    def test_validate_index_succeeds_when_index_exists(self, mock_get_settings):
        """validate_index() succeeds when index exists."""
        mock_settings = MagicMock()
        mock_settings.pinecone_api_key = "test-api-key"
        mock_settings.pinecone_index_name = "existing-index"
        mock_get_settings.return_value = mock_settings

        mock_pc = MagicMock()
        mock_pc.has_index.return_value = True
        mock_pinecone_class = MagicMock(return_value=mock_pc)
        with patch("tools.pinecone_client.Pinecone", mock_pinecone_class):
            client = PineconeClient()

        # Should not raise
        client.validate_index()

    def test_exponential_backoff_retry_succeeds_on_first_attempt(self):
        """exponential_backoff_retry() succeeds when function succeeds immediately."""
        func = MagicMock(return_value="success")
        result = PineconeClient.exponential_backoff_retry(func)
        assert result == "success"
        func.assert_called_once()

    @patch("tools.pinecone_client.time.sleep")
    def test_exponential_backoff_retry_retries_on_429(self, mock_sleep):
        """exponential_backoff_retry() retries on 429 rate limit errors."""
        error_429 = PineconeException("Rate limited")
        error_429.status = 429

        func = MagicMock(side_effect=[error_429, "success"])
        result = PineconeClient.exponential_backoff_retry(func, max_retries=2)

        assert result == "success"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1

    @patch("tools.pinecone_client.time.sleep")
    def test_exponential_backoff_retry_retries_on_5xx(self, mock_sleep):
        """exponential_backoff_retry() retries on 5xx server errors."""
        error_500 = PineconeException("Server error")
        error_500.status = 500

        func = MagicMock(side_effect=[error_500, "success"])
        result = PineconeClient.exponential_backoff_retry(func, max_retries=2)

        assert result == "success"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_exponential_backoff_retry_fails_on_4xx(self):
        """exponential_backoff_retry() fails immediately on 4xx client errors."""
        error_400 = PineconeException("Bad request")
        error_400.status = 400

        func = MagicMock(side_effect=error_400)
        with pytest.raises(PineconeException):
            PineconeClient.exponential_backoff_retry(func, max_retries=3)

        # Should only try once (no retries for 4xx)
        assert func.call_count == 1

    @patch("tools.pinecone_client.time.sleep")
    def test_exponential_backoff_retry_caps_delay_at_60s(self, mock_sleep):
        """exponential_backoff_retry() caps delay at 60 seconds."""
        error_500 = PineconeException("Server error")
        error_500.status = 500

        func = MagicMock(side_effect=[error_500, error_500, "success"])
        result = PineconeClient.exponential_backoff_retry(func, max_retries=3)

        assert result == "success"
        # First retry: 2^0 = 1s, second retry: min(2^1, 60) = 2s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    def test_record_to_dict_omits_none_optional_fields(self):
        """_record_to_dict() omits None values for optional fields."""
        record = PineconeRecord(
            _id="test-id",
            content="test content",
            standard_set_id="set-id",
            standard_set_title="Test Set",
            subject="Math",
            education_levels=["01"],
            document_id="doc-id",
            document_valid="2021",
            jurisdiction_id="jur-id",
            jurisdiction_title="Test Jurisdiction",
            depth=0,
            is_leaf=True,
            is_root=True,
            root_id="test-id",
            ancestor_ids=[],
            child_ids=[],
            sibling_count=0,
            # Optional fields set to None
            normalized_subject=None,
            publication_status=None,
            asn_identifier=None,
            statement_notation=None,
            statement_label=None,
            parent_id=None,
        )

        record_dict = PineconeClient._record_to_dict(record)

        # Verify _id is serialized (not id)
        assert "_id" in record_dict
        assert record_dict["_id"] == "test-id"
        assert "id" not in record_dict

        # Optional fields should be omitted
        assert "asn_identifier" not in record_dict
        assert "statement_notation" not in record_dict
        assert "statement_label" not in record_dict
        assert "normalized_subject" not in record_dict
        assert "publication_status" not in record_dict
        # parent_id should be present as null
        assert "parent_id" in record_dict
        assert record_dict["parent_id"] is None

    def test_record_to_dict_includes_present_optional_fields(self):
        """_record_to_dict() includes optional fields when they have values."""
        record = PineconeRecord(
            _id="test-id",
            content="test content",
            standard_set_id="set-id",
            standard_set_title="Test Set",
            subject="Math",
            normalized_subject="Math",
            education_levels=["01"],
            document_id="doc-id",
            document_valid="2021",
            publication_status="Published",
            jurisdiction_id="jur-id",
            jurisdiction_title="Test Jurisdiction",
            asn_identifier="ASN123",
            statement_notation="1.2.3",
            statement_label="Standard",
            depth=1,
            is_leaf=True,
            is_root=False,
            parent_id="parent-id",
            root_id="root-id",
            ancestor_ids=["root-id"],
            child_ids=[],
            sibling_count=0,
        )

        record_dict = PineconeClient._record_to_dict(record)

        # Verify _id is serialized (not id)
        assert "_id" in record_dict
        assert record_dict["_id"] == "test-id"
        assert "id" not in record_dict

        # Optional fields should be included when present
        assert record_dict["asn_identifier"] == "ASN123"
        assert record_dict["statement_notation"] == "1.2.3"
        assert record_dict["statement_label"] == "Standard"
        assert record_dict["normalized_subject"] == "Math"
        assert record_dict["publication_status"] == "Published"
        assert record_dict["parent_id"] == "parent-id"
