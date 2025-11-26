# Spec Tasks

Tasks for implementing the Pinecone Integration Sprint as defined in `spec.md`.

Recommended execution order:
Task 1 (Setup) - foundation
Task 2 (Models) - data structures
Tasks 3-7 (Processor) - in sequence
Tasks 8-9 (Client) - can parallel with 3-7
Tasks 10-12 (CLI) - depends on processor and client

---

## Tasks

- [x] 1. **Project Setup & Configuration**

  - [x] 1.1 Update `pyproject.toml`: Remove `sentence-transformers`, `numpy<2`, `huggingface_hub`; add `pinecone`
  - [x] 1.2 Update `tools/config.py`: Add `pinecone_api_key`, `pinecone_index_name` (default: `common-core-standards`), `pinecone_namespace` (default: `standards`) settings
  - [x] 1.3 Create/update `.env.example`: Add `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_NAMESPACE` variables
  - [x] 1.4 Delete `tools/data_processor.py` (outdated local embedding approach)
  - [x] 1.5 Run `pip install -e .` to verify dependencies resolve correctly

- [x] 2. **Pydantic Models for Processed Records**

  - [x] 2.1 Create `tools/pinecone_models.py` with `PineconeRecord` model containing all fields from processed.json schema
  - [x] 2.2 Define `ProcessedStandardSet` model with `records: list[PineconeRecord]` for the output file structure
  - [x] 2.3 Add field validators for `education_levels` (split comma-separated, flatten, dedupe)
  - [x] 2.4 Add `model_config` with `json_encoders` for proper null handling of `parent_id`
  - [x] 2.5 Write unit tests for model validation and education_levels processing

- [x] 3. **Pinecone Processor - Relationship Maps**

  - [x] 3.1 Create `tools/pinecone_processor.py` with `StandardSetProcessor` class
  - [x] 3.2 Implement `_build_id_to_standard_map()`: Map of `id` → standard object
  - [x] 3.3 Implement `_build_parent_to_children_map()`: Map of `parentId` → `[child_ids]` sorted by `position` ascending
  - [x] 3.4 Implement `_identify_leaf_nodes()`: Set of IDs that are NOT any standard's `parentId`
  - [x] 3.5 Implement `_identify_root_nodes()`: Set of IDs where `parentId` is `null`
  - [x] 3.6 Write unit tests for relationship map building with sample data

- [x] 4. **Pinecone Processor - Hierarchy Functions**

  - [x] 4.1 Implement `find_root_id()`: Walk up parent chain with circular reference protection
  - [x] 4.2 Implement `build_ordered_ancestors()`: Build ancestor list ordered root (idx 0) → immediate parent
  - [x] 4.3 Implement `_compute_sibling_count()`: Count standards with same `parent_id`, excluding self
  - [x] 4.4 Write unit tests for hierarchy functions with various depth levels (0, 1, 3+)

- [x] 5. **Pinecone Processor - Content Generation**

  - [x] 5.1 Implement `_build_content_text()`: Generate `Depth N (notation): description` format
  - [x] 5.2 Handle missing `statementNotation` (omit parentheses)
  - [x] 5.3 Handle root nodes (single line `Depth 0: description`)
  - [x] 5.4 Write unit tests for content generation with various hierarchy depths

- [x] 6. **Pinecone Processor - Record Transformation**

  - [x] 6.1 Implement `_transform_standard()`: Convert single standard to `PineconeRecord`
  - [x] 6.2 Extract standard set context fields (subject, jurisdiction, document, education_levels)
  - [x] 6.3 Compute all hierarchy fields (is_leaf, is_root, parent_id, root_id, ancestor_ids, child_ids, sibling_count)
  - [x] 6.4 Handle optional fields (omit if missing: statement_label, statement_notation, asn_identifier)
  - [x] 6.5 Implement `process_standard_set()`: Main entry point that processes all standards and returns `ProcessedStandardSet`
  - [x] 6.6 Write integration test with real `data.json` sample file

- [x] 7. **Pinecone Processor - File Operations**

  - [x] 7.1 Implement `process_and_save()`: Load `data.json`, process, save `processed.json`
  - [x] 7.2 Add error handling for missing `data.json` (skip with warning)
  - [x] 7.3 Add error handling for invalid JSON (log error, continue)
  - [x] 7.4 Add logging for processing progress and record counts
  - [x] 7.5 Write integration test for file operations

- [x] 8. **Pinecone Client - Core Functions**

  - [x] 8.1 Create `tools/pinecone_client.py` with `PineconeClient` class
  - [x] 8.2 Implement `__init__()`: Initialize Pinecone SDK from config settings
  - [x] 8.3 Implement `validate_index()`: Check index exists with `pc.has_index()`, raise helpful error if not
  - [x] 8.4 Implement `exponential_backoff_retry()`: Retry on 429/5xx, fail on 4xx
  - [x] 8.5 Implement `batch_upsert()`: Upsert records in batches of 96 with rate limiting

- [x] 9. **Pinecone Client - Upload Tracking**

  - [x] 9.1 Implement `is_uploaded()`: Check for `.pinecone_uploaded` marker file
  - [x] 9.2 Implement `mark_uploaded()`: Create marker file with ISO 8601 timestamp
  - [x] 9.3 Implement `get_upload_timestamp()`: Read timestamp from marker file
  - [x] 9.4 Write unit tests for upload tracking functions

- [x] 10. **CLI - Update download-sets Command**

  - [x] 10.1 Import `pinecone_processor` in `tools/cli.py`
  - [x] 10.2 After successful `download_standard_set()` call, invoke `process_and_save()` for single set download
  - [x] 10.3 After successful bulk download loop, invoke `process_and_save()` for each downloaded set
  - [x] 10.4 Add console output showing processing status
  - [x] 10.5 Update `list` command to show processing status (processed.json exists)

- [x] 11. **CLI - Remove Old Process Command**

  - [x] 11.1 Remove the `process` command function from `tools/cli.py`
  - [x] 11.2 Remove `data_processor` import from `tools/cli.py`
  - [x] 11.3 Update `list` command if it references old processing status

- [x] 12. **CLI - Implement pinecone-upload Command**
  - [x] 12.1 Add `pinecone-upload` command with options: `--set-id`, `--all`, `--force`, `--dry-run`, `--batch-size`
  - [x] 12.2 Implement set discovery: Find all standard sets with `processed.json`
  - [x] 12.3 Implement upload filtering: Skip sets with `.pinecone_uploaded` unless `--force`
  - [x] 12.4 Implement `--dry-run`: Show what would be uploaded without uploading
  - [x] 12.5 Implement upload execution: Call `PineconeClient.batch_upsert()` for each set
  - [x] 12.6 Add progress output with record counts
  - [x] 12.7 Handle upload failures: Log error, continue with next set if `--all`, don't create marker
  - [x] 12.8 Write manual test script to verify end-to-end upload flow
