"""Pinecone client for uploading and managing standard records."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import Any

from loguru import logger
from pinecone import Pinecone
from pinecone.exceptions import PineconeException

from src.mcp_config import get_mcp_settings
from tools.pinecone_models import PineconeRecord

settings = get_mcp_settings()


class PineconeClient:
    """Client for interacting with Pinecone index."""

    def __init__(self) -> None:
        """Initialize Pinecone SDK from config settings."""
        api_key = settings.pinecone_api_key
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")

        self.pc = Pinecone(api_key=api_key)
        self.index_name = settings.pinecone_index_name
        self.namespace = settings.pinecone_namespace
        self._index = None

    @property
    def index(self):
        """Get the index object, creating it if needed."""
        if self._index is None:
            self._index = self.pc.Index(self.index_name)
        return self._index

    def validate_index(self) -> None:
        """
        Check index exists with pc.has_index(), raise helpful error if not.

        Raises:
            ValueError: If index does not exist, with instructions to create it.
        """
        if not self.pc.has_index(name=self.index_name):
            raise ValueError(
                f"Index '{self.index_name}' not found. Create it with:\n"
                f"pc index create -n {self.index_name} -m cosine -c aws -r us-east-1 "
                f"--model llama-text-embed-v2 --field_map text=content"
            )

    def ensure_index_exists(self) -> bool:
        """
        Check if index exists, create it if not.

        Creates the index with integrated embeddings using llama-text-embed-v2 model.

        Returns:
            True if index was created, False if it already existed.
        """
        if self.pc.has_index(name=self.index_name):
            logger.info(f"Index '{self.index_name}' already exists")
            return False

        logger.info(f"Creating index '{self.index_name}' with integrated embeddings...")
        self.pc.create_index_for_model(
            name=self.index_name,
            cloud="aws",
            region="us-east-1",
            embed={
                "model": "llama-text-embed-v2",
                "field_map": {"text": "content"},
            },
        )
        logger.info(f"Successfully created index '{self.index_name}'")
        return True

    def get_index_stats(self) -> dict[str, Any]:
        """
        Get index statistics including vector count and namespaces.

        Returns:
            Dictionary with index stats including total_vector_count and namespaces.
        """
        stats = self.index.describe_index_stats()
        return {
            "total_vector_count": stats.total_vector_count,
            "namespaces": dict(stats.namespaces) if stats.namespaces else {},
        }

    @staticmethod
    def exponential_backoff_retry(
        func: Callable[[], Any], max_retries: int = 5
    ) -> Any:
        """
        Retry function with exponential backoff on 429/5xx, fail on 4xx.

        Args:
            func: Function to retry (should be a callable that takes no args)
            max_retries: Maximum number of retry attempts

        Returns:
            Result of func()

        Raises:
            PineconeException: If retries exhausted or non-retryable error
        """
        for attempt in range(max_retries):
            try:
                return func()
            except PineconeException as e:
                status_code = getattr(e, "status", None)
                # Only retry transient errors
                if status_code and (status_code >= 500 or status_code == 429):
                    if attempt < max_retries - 1:
                        delay = min(2 ** attempt, 60)  # Cap at 60s
                        logger.warning(
                            f"Retryable error (status {status_code}), "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for retryable error"
                        )
                        raise
                else:
                    # Don't retry client errors
                    logger.error(f"Non-retryable error (status {status_code}): {e}")
                    raise
            except Exception as e:
                # Non-Pinecone exceptions should not be retried
                logger.error(f"Non-retryable exception: {e}")
                raise

    def batch_upsert(
        self, records: list[PineconeRecord], batch_size: int = 96
    ) -> None:
        """
        Upsert records in batches of specified size with rate limiting.

        Args:
            records: List of PineconeRecord objects to upsert
            batch_size: Number of records per batch (default: 96)
        """
        if not records:
            logger.info("No records to upsert")
            return

        total_batches = (len(records) + batch_size - 1) // batch_size
        logger.info(
            f"Upserting {len(records)} records in {total_batches} batch(es) "
            f"(batch size: {batch_size})"
        )

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            batch_num = (i // batch_size) + 1

            # Convert PineconeRecord models to dict format for Pinecone
            batch_dicts = [self._record_to_dict(record) for record in batch]

            logger.debug(f"Upserting batch {batch_num}/{total_batches} ({len(batch)} records)")

            # Retry with exponential backoff
            self.exponential_backoff_retry(
                lambda b=batch_dicts: self.index.upsert_records(
                    namespace=self.namespace, records=b
                )
            )

            # Rate limiting between batches
            if i + batch_size < len(records):
                time.sleep(0.1)

        logger.info(f"Successfully upserted {len(records)} records")

    @staticmethod
    def _record_to_dict(record: PineconeRecord) -> dict[str, Any]:
        """
        Convert PineconeRecord model to dict format for Pinecone API.

        Handles optional fields by omitting them if None. Pinecone doesn't accept
        null values for metadata fields, so parent_id must be omitted entirely
        when None (for root nodes).

        Args:
            record: PineconeRecord model instance

        Returns:
            Dictionary ready for Pinecone upsert_records
        """
        # Use by_alias=True to serialize 'id' as '_id' per model serialization_alias
        record_dict = record.model_dump(exclude_none=False, by_alias=True)

        # Remove None values for optional fields
        optional_fields = {
            "asn_identifier",
            "statement_notation",
            "statement_label",
            "normalized_subject",
            "publication_status",
            "parent_id",  # Must be omitted when None (Pinecone doesn't accept null)
            "document_id",
            "document_valid",
        }
        for field in optional_fields:
            if record_dict.get(field) is None:
                record_dict.pop(field, None)

        return record_dict

    def search_standards(
        self,
        query_text: str,
        top_k: int = 5,
        grade: str | None = None,
    ) -> list[dict]:
        """
        Perform semantic search over standards.

        Args:
            query_text: Natural language query
            top_k: Maximum number of results
            grade: Optional grade filter

        Returns:
            List of result dictionaries with metadata and scores
        """
        # Build filter dictionary dynamically
        # Always filter to only leaf nodes (actual standards, not parent categories)
        filter_parts = [{"is_leaf": {"$eq": True}}]
        
        if grade:
            filter_parts.append({"education_levels": {"$in": [grade]}})

        filter_dict = None
        if len(filter_parts) == 1:
            filter_dict = filter_parts[0]
        elif len(filter_parts) == 2:
            filter_dict = {"$and": filter_parts}

        # Build query dictionary
        query_dict: dict[str, Any] = {
            "inputs": {"text": query_text},
            "top_k": top_k * 2,  # Get more candidates for reranking
        }
        if filter_dict:
            query_dict["filter"] = filter_dict

        # Call search with reranking
        results = self.index.search(
            namespace=self.namespace,
            query=query_dict,
            rerank={"model": "bge-reranker-v2-m3", "top_n": top_k, "rank_fields": ["content"]},
        )

        # Parse results
        hits = results.get("result", {}).get("hits", [])
        parsed_results = []
        for hit in hits:
            result_dict = {
                "_id": hit["_id"],
                "score": hit["_score"],
                **hit.get("fields", {}),
            }
            parsed_results.append(result_dict)

        return parsed_results

    def fetch_standard(self, standard_id: str) -> dict | None:
        """
        Fetch a standard by its GUID (_id field only).

        This method performs a direct lookup using Pinecone's fetch() API, which only
        works with the standard's GUID (_id field). It does NOT search by statement_notation,
        asn_identifier, or any other metadata fields.

        Args:
            standard_id: Standard GUID (_id field) - must be the exact GUID format
                (e.g., "EA60C8D165F6481B90BFF782CE193F93")

        Returns:
            Standard dictionary with metadata, or None if not found
        """
        result = self.index.fetch(ids=[standard_id], namespace=self.namespace)

        # Extract vectors from FetchResponse
        # FetchResponse.vectors is a dict mapping ID to Vector objects
        vectors = result.vectors
        
        if not vectors or standard_id not in vectors:
            return None

        vector = vectors[standard_id]
        
        # Extract metadata from Vector object
        # Vector has: id, values (embedding), and metadata (dict with all fields)
        metadata = vector.metadata or {}
        vector_id = vector.id

        # Combine _id with all metadata fields
        record_dict = {
            "_id": vector_id,
            **metadata,
        }

        return record_dict

    @staticmethod
    def is_uploaded(set_dir: Path) -> bool:
        """
        Check for .pinecone_uploaded marker file.

        Args:
            set_dir: Path to standard set directory

        Returns:
            True if marker file exists, False otherwise
        """
        marker_file = set_dir / ".pinecone_uploaded"
        return marker_file.exists()

    @staticmethod
    def mark_uploaded(set_dir: Path) -> None:
        """
        Create marker file with ISO 8601 timestamp.

        Args:
            set_dir: Path to standard set directory
        """
        marker_file = set_dir / ".pinecone_uploaded"
        timestamp = datetime.now(timezone.utc).isoformat()
        marker_file.write_text(timestamp, encoding="utf-8")
        logger.debug(f"Created upload marker: {marker_file}")

    @staticmethod
    def get_upload_timestamp(set_dir: Path) -> str | None:
        """
        Read timestamp from marker file.

        Args:
            set_dir: Path to standard set directory

        Returns:
            ISO 8601 timestamp string if marker exists, None otherwise
        """
        marker_file = set_dir / ".pinecone_uploaded"
        if not marker_file.exists():
            return None

        try:
            return marker_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"Failed to read upload marker {marker_file}: {e}")
            return None

