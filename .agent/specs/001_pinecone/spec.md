# Pinecone Integration Sprint

## Overview

This sprint integrates Pinecone for vector storage and semantic search of educational standards. We will use Pinecone's hosted embedding models (`llama-text-embed-v2`) for both creating embeddings and search, leveraging their native search functionality through the Python SDK. This approach allows rapid iteration, takes advantage of their free tier, and eliminates the need for local embedding generation.

---

## User Stories

**US-1: Transform Standards on Download**
As a developer, I want downloaded standard sets to be automatically transformed into Pinecone-ready format so that I don't need a separate processing step before uploading.

**US-2: Upload Standards to Pinecone**
As a developer, I want to upload processed standards to Pinecone with a single CLI command so that the standards become searchable.

**US-3: Prevent Duplicate Uploads**
As a developer, I want the system to track which standard sets have been uploaded so that I don't waste time and API calls re-uploading data.

**US-4: Resume Failed Uploads**
As a developer, I want to be able to resume uploads after a failure so that I can recover from crashes without starting over.

**US-5: Preview Before Upload**
As a developer, I want a dry-run option to see what would be uploaded without actually uploading so that I can verify the data before committing.

---

## Sprint Parts

### Part 1: Transform Standard Sets on Download

Update the CLI `download-sets` command to create transformed `processed.json` files alongside the original `data.json`. These transformed files contain records ready for Pinecone ingestion.

### Part 2: Pinecone Upsert CLI Command

Implement a new CLI command to upload transformed standard set records to Pinecone in batches, with tracking to prevent duplicate uploads.

---

## Technical Decisions

### Text Content Format (for Embedding)

Use a structured text block with depth-based headers to preserve the full parent-child context:

```
Depth 0: Geometry
Depth 1 (1.G.K): Reason with shapes and their attributes.
Depth 2 (1.G.K.3.Ba): Partition circles and rectangles into two equal shares and:
Depth 3 (1.G.K.3.Ba.B): Describe the whole as two of the shares.
```

Format rules:

- Each line starts with `Depth N:` where N is the standard's depth value
- If `statementNotation` is present, include it in parentheses after the depth label
- Include the full ancestor chain from root (depth 0) down to the current standard
- Join all lines with `\n`

This format is depth-agnostic and works regardless of how deep the hierarchy goes, avoiding assumptions about what each depth level represents semantically.

### Which Standards to Process

**Process ALL standards in the hierarchy, not just leaf nodes.** This enables:

- Direct lookup of any standard by ID (including parents)
- Navigation up and down the hierarchy
- Finding children of any standard
- Complete relationship traversal

Each record includes an `is_leaf` boolean to distinguish leaf nodes (no children) from branch nodes (have children). Search queries can filter to `is_leaf: true` when only the most specific standards are desired.

**Identifying leaf vs branch nodes:** A standard is a leaf node if its `id` does NOT appear as a `parentId` for any other standard in the set.

**Note:** The previous implementation in `data_processor.py` that filtered only on `statementLabel == "Standard"` is incorrect and should be completely replaced.

### Pinecone Record ID Strategy

Use the individual standard's GUID as the record `_id` (e.g., `EA60C8D165F6481B90BFF782CE193F93`). This ensures uniqueness and enables direct lookup. The parent hierarchy is preserved in the text content, not the ID.

### Namespace Strategy

Use a single namespace for all standards (configurable via environment variable, default: `standards`). This allows cross-jurisdiction and cross-subject searches in a single query. Filtering by metadata handles scoping to specific jurisdictions, subjects, or grade levels.

### Upload Tracking

Create a `.pinecone_uploaded` marker file in each standard set directory after successful upload. Before uploading, check for this marker file to skip already-uploaded sets.

### Index Management

The Pinecone index should be created manually using the Pinecone CLI before running the upsert command. The index name is configured via environment variable.

**Index creation command (run once manually):**

```bash
pc index create -n common-core-standards -m cosine -c aws -r us-east-1 --model llama-text-embed-v2 --field_map text=content
```

The upsert CLI command should validate the index exists and fail with helpful instructions if not found.

### File Changes

**Files to Delete:**

- `tools/data_processor.py` - Outdated local embedding approach, completely replaced

**Files to Edit:**

- `tools/cli.py` - Add `pinecone-upload` command, update `download-sets` to call processor, remove old `process` command
- `tools/config.py` - Add Pinecone configuration settings
- `.env.example` - Add Pinecone environment variables
- `pyproject.toml` - Remove `sentence-transformers` and `numpy`, add `pinecone`

**Files to Create:**

- `tools/pinecone_processor.py` - New module for transforming standards to Pinecone format
- `tools/pinecone_client.py` - New module for Pinecone SDK interactions (upsert, index validation)

### Processing Trigger

The `download-sets` command will automatically generate `processed.json` immediately after saving `data.json`. This ensures processed data is always in sync with raw data.

### Handling Missing Optional Fields

Per Pinecone best practices, handle missing fields as follows:

- **Omit missing string/array fields** from the record entirely. Do not include empty strings or empty arrays for optional fields.
- **`parent_id`**: Store as `null` for root nodes (do not omit). This explicitly indicates "no parent" vs "unknown parent".
- **`statement_label`**: If missing in source, omit the field entirely. Do not infer from depth.
- **`statement_notation`**: If missing, omit from content text parentheses (just use `Depth N: {description}`).

### Handling Education Levels

The source `educationLevels` field may contain comma-separated values within individual array elements (e.g., `["01,02"]` instead of `["01", "02"]`). Process as follows:

1. **Split comma-separated strings**: For each element in the array, split on commas to extract individual grade levels
2. **Flatten**: Combine all split values into a single array
3. **Deduplicate**: Remove any duplicate grade level strings
4. **Preserve as array**: Store as an array of strings in the output—do NOT join back into a comma-separated string

Pinecone metadata supports string lists natively.

**Example transformation:**

```python
# Input: ["01,02", "02", "03"]
# After split: [["01", "02"], ["02"], ["03"]]
# After flatten: ["01", "02", "02", "03"]
# After dedupe: ["01", "02", "03"]
# Output: ["01", "02", "03"]
```

**Note:** The `education_levels` value comes from the **standard set** level (`data.educationLevels`), not from individual standards. Individual standards do not have their own education level field. The same education levels are applied to all records from a given standard set to enhance retrieval filtering.

---

## Processed.json Schema

Each `processed.json` file contains records ready for Pinecone upsert:

```json
{
  "records": [
    {
      "_id": "EA60C8D165F6481B90BFF782CE193F93",
      "content": "Depth 0: Geometry\nDepth 1 (1.G.K): Reason with shapes and their attributes.\nDepth 2 (1.G.K.3.Ba): Partition circles and rectangles into two equal shares and:\nDepth 3 (1.G.K.3.Ba.B): Describe the whole as two of the shares.",
      "standard_set_id": "744704BE56D44FB9B3D18B543FBF9BCC_D21218769_grade-01",
      "standard_set_title": "Grade 1",
      "subject": "Mathematics (2021-)",
      "normalized_subject": "Math",
      "education_levels": ["01"],
      "document_id": "D21218769",
      "document_valid": "2021",
      "publication_status": "Published",
      "jurisdiction_id": "744704BE56D44FB9B3D18B543FBF9BCC",
      "jurisdiction_title": "Wyoming",
      "asn_identifier": "S21238682",
      "statement_notation": "1.G.K.3.Ba.B",
      "statement_label": "Benchmark",
      "depth": 3,
      "is_leaf": true,
      "is_root": false,
      "parent_id": "3445678A58C74065B7DF5617B353B89C",
      "root_id": "FE0D33F3287E4137AD66FA3926FAB114",
      "ancestor_ids": [
        "FE0D33F3287E4137AD66FA3926FAB114",
        "386EA56EADD24A209DC2D77A71B2F89B",
        "3445678A58C74065B7DF5617B353B89C"
      ],
      "child_ids": [],
      "sibling_count": 1
    }
  ]
}
```

### Metadata Fields

All metadata fields must be flat (no nested objects) per Pinecone requirements. Arrays of strings are allowed.

**Standard Set Context:**

| Field                | Description                                                                 |
| -------------------- | --------------------------------------------------------------------------- |
| `_id`                | Standard's unique GUID                                                      |
| `content`            | Rich text block with full hierarchy (used for embedding)                    |
| `standard_set_id`    | ID of the parent standard set                                               |
| `standard_set_title` | Title of the standard set (e.g., "Grade 1")                                 |
| `subject`            | Full subject name                                                           |
| `normalized_subject` | Normalized subject (e.g., "Math", "ELA")                                    |
| `education_levels`   | Array of grade level strings (e.g., `["01"]` or `["09", "10", "11", "12"]`) |
| `document_id`        | Document ID                                                                 |
| `document_valid`     | Year the document is valid                                                  |
| `publication_status` | Publication status (e.g., "Published")                                      |
| `jurisdiction_id`    | Jurisdiction GUID                                                           |
| `jurisdiction_title` | Jurisdiction name (e.g., "Wyoming")                                         |

**Standard Identity & Position:**

| Field                | Description                                                  |
| -------------------- | ------------------------------------------------------------ |
| `asn_identifier`     | ASN identifier if available (e.g., "S21238682")              |
| `statement_notation` | Standard notation teachers use (e.g., "1.G.K.3.Ba.B")        |
| `statement_label`    | Type of standard if present in source (e.g., "Benchmark")    |
| `depth`              | Hierarchy depth level (0 is root, increases with each level) |
| `is_leaf`            | Boolean: true if this standard has no children               |
| `is_root`            | Boolean: true if this is a root node (depth=0, no parent)    |

**Hierarchy Relationships:**

| Field           | Description                                                       |
| --------------- | ----------------------------------------------------------------- |
| `parent_id`     | Immediate parent's GUID, or `null` for root nodes                 |
| `root_id`       | Root ancestor's GUID. For root nodes, equals the node's own `_id` |
| `ancestor_ids`  | Array of ancestor GUIDs ordered root→parent (see ordering below)  |
| `child_ids`     | Array of direct children's GUIDs ordered by position (see below)  |
| `sibling_count` | Number of siblings (standards with same parent_id), excludes self |

**Array Ordering Guarantees:**

`ancestor_ids` is ordered from **root (index 0) to immediate parent (last index)**:

```
ancestor_ids[0]        = root ancestor (depth 0)
ancestor_ids[1]        = second level ancestor (depth 1)
ancestor_ids[2]        = third level ancestor (depth 2)
...
ancestor_ids[-1]       = immediate parent (depth = current_depth - 1)
ancestor_ids.length    = current standard's depth
```

Example for a depth-3 standard:

```python
ancestor_ids = ["ROOT_ID", "DEPTH1_ID", "DEPTH2_ID"]
# ancestor_ids[0] is the root (depth 0)
# ancestor_ids[1] is the depth-1 ancestor
# ancestor_ids[2] is the immediate parent (depth 2)
# To get ancestor at depth N: ancestor_ids[N]
```

`child_ids` is ordered by the source `position` field (ascending), preserving the natural document order of standards.

---

## Configuration

### Environment Variables

Add to `tools/config.py` and `.env.example`:

| Variable              | Description                | Default                 |
| --------------------- | -------------------------- | ----------------------- |
| `PINECONE_API_KEY`    | Pinecone API key           | (required)              |
| `PINECONE_INDEX_NAME` | Name of the Pinecone index | `common-core-standards` |
| `PINECONE_NAMESPACE`  | Namespace for records      | `standards`             |

---

## File Locations

- **Original data:** `data/raw/standardSets/{standard_set_id}/data.json`
- **Processed data:** `data/raw/standardSets/{standard_set_id}/processed.json`
- **Upload marker:** `data/raw/standardSets/{standard_set_id}/.pinecone_uploaded`

### Upload Marker File Format

The `.pinecone_uploaded` marker file contains an ISO 8601 timestamp indicating when the upload completed:

```
2025-01-15T14:30:00Z
```

This allows tracking when each standard set was last uploaded to Pinecone.

---

## Source Data Reference

The source data is stored at `data/raw/standardSets/{standard_set_id}/data.json`. Key fields used for transformation:

**Standard Set Level:**

- `id`, `title`, `subject`, `normalizedSubject`, `educationLevels`
- `document.id`, `document.valid`, `document.asnIdentifier`, `document.publicationStatus`
- `jurisdiction.id`, `jurisdiction.title`

**Individual Standard Level:**

- `id` (GUID)
- `asnIdentifier`
- `depth` (hierarchy level, 0 is root)
- `position` (numeric sort order within the document - used for ordering `child_ids`)
- `statementNotation` (e.g., "1.G.K.3.Ba.B")
- `statementLabel` (e.g., "Domain", "Standard", "Benchmark")
- `description`
- `ancestorIds` (array of ancestor GUIDs - **order is NOT guaranteed**, must be rebuilt programmatically)
- `parentId`

---

## CLI Commands

### Updated Command: `download-sets`

After downloading `data.json`, automatically call the processor to generate `processed.json` in the same directory. No changes to command arguments.

### New Command: `pinecone-upload`

```
Usage: cli pinecone-upload [OPTIONS]

Upload processed standard sets to Pinecone.

Options:
  --set-id TEXT      Upload a specific standard set by ID
  --all              Upload all downloaded standard sets with processed.json
  --force            Re-upload even if .pinecone_uploaded marker exists
  --dry-run          Show what would be uploaded without actually uploading
  --batch-size INT   Number of records per batch (default: 96)
```

**Behavior:**

- If neither `--set-id` nor `--all` is provided, prompt for confirmation before uploading all
- Skip sets that have `.pinecone_uploaded` marker unless `--force` is specified
- Show progress with count of records uploaded
- On success, create `.pinecone_uploaded` marker file with timestamp
- On failure, log error and continue with next set (if `--all`)
- Validate index exists before attempting upload; fail with helpful instructions if not found

### Removed Command: `process`

The old `process` command is removed as it used the deprecated local embedding approach.

---

## Dependencies

### Remove from `pyproject.toml`:

- `sentence-transformers`
- `numpy<2`
- `huggingface_hub`

### Add to `pyproject.toml`:

- `pinecone` (current SDK, not `pinecone-client`)

---

## Transformation Algorithm

### Pre-processing: Build Relationship Maps

Before processing individual standards, build helper data structures from ALL standards in the set:

1. **ID-to-standard map**: Map of `id` → standard object for lookups
2. **Parent-to-children map**: Map of `parentId` → `[child_ids]`, with children **sorted by `position` ascending**
3. **Leaf node set**: A standard is a leaf if its `id` does NOT appear as any standard's `parentId`
4. **Root identification**: Find all standards where `parentId` is `null`. These are root nodes.

**Note on ordering:** The source data includes a `position` field for each standard that defines the natural document order. When building `child_ids`, sort by this `position` value to maintain consistent ordering.

### Determining root_id

**Do NOT rely on the order of `ancestorIds` from the source data.** Instead, programmatically determine the root by walking up the parent chain:

```python
def find_root_id(standard: dict, id_to_standard: dict[str, dict]) -> str:
    """Walk up the parent chain to find the root ancestor."""
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
```

For root nodes themselves (where `parentId` is `null`), `root_id` equals the node's own `_id`.

### Building ancestor_ids in Correct Order

Since `ancestorIds` order in source data is NOT guaranteed, rebuild the ancestor chain by walking up the parent chain:

```python
def build_ordered_ancestors(standard: dict, id_to_standard: dict[str, dict]) -> list[str]:
    """Build ancestor list ordered from root to immediate parent."""
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
```

### Processing Each Standard

For **EACH** standard in the set (not just leaves), create a record:

**Step 1: Compute hierarchy relationships**

| Field           | How to compute                                                          |
| --------------- | ----------------------------------------------------------------------- |
| `parent_id`     | Copy from source `parentId` (`null` if not present)                     |
| `ancestor_ids`  | Build using `build_ordered_ancestors()` - ordered root (idx 0) → parent |
| `root_id`       | Use `find_root_id()`. For root nodes, equals own `_id`                  |
| `is_root`       | `True` if `parentId` is `null`                                          |
| `child_ids`     | Look up in parent-to-children map, **sorted by `position` ascending**   |
| `is_leaf`       | `True` if `child_ids` is empty                                          |
| `sibling_count` | Count of other standards with same `parent_id` (excludes self)          |

**Step 2: Build the content text block**

1. Get ordered ancestors from the computed `ancestor_ids`
2. Look up each ancestor in `id_to_standard` map
3. Build text lines in order from root to current standard:
   - If `statementNotation` is present: `Depth {depth} ({statementNotation}): {description}`
   - Otherwise: `Depth {depth}: {description}`
4. Join all lines with `\n`

**Step 3: Set statement_label**

- Copy `statementLabel` from source if present
- If missing in source, **omit the field entirely** (do not infer from depth)

### Example Transformation

Given this hierarchy:

- Root (depth 0, id "FE0D..."): "Geometry"
- Child (depth 1, notation "1.G.K"): "Reason with shapes and their attributes."
- Child (depth 2, notation "1.G.K.3.Ba"): "Partition circles and rectangles into two equal shares and:"
- Child (depth 3, notation "1.G.K.3.Ba.B"): "Describe the whole as two of the shares."

Output `content` for the depth-3 standard:

```
Depth 0: Geometry
Depth 1 (1.G.K): Reason with shapes and their attributes.
Depth 2 (1.G.K.3.Ba): Partition circles and rectangles into two equal shares and:
Depth 3 (1.G.K.3.Ba.B): Describe the whole as two of the shares.
```

**For a root node** (depth 0, e.g., "Geometry"):

- `is_root`: `true`
- `root_id`: equals own `_id` (e.g., "FE0D...")
- `parent_id`: `null`
- `ancestor_ids`: `[]` (empty array)
- `content`: `Depth 0: Geometry`

---

## Error Handling

### Processing Errors

- **Missing `data.json`**: Skip with warning, continue to next set
- **Invalid JSON**: Log error with file path and continue to next set
- **No leaf nodes found**: Create `processed.json` with empty records array, log warning

### Pinecone API Errors

| Error Type          | Action                                                 |
| ------------------- | ------------------------------------------------------ |
| 4xx (client errors) | Fail immediately, do not retry (indicates bad request) |
| 429 (rate limit)    | Retry with exponential backoff                         |
| 5xx (server errors) | Retry with exponential backoff                         |

### Retry Pattern

```python
import time
from pinecone.exceptions import PineconeException

def exponential_backoff_retry(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except PineconeException as e:
            status_code = getattr(e, 'status', None)
            # Only retry transient errors
            if status_code and (status_code >= 500 or status_code == 429):
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 60)  # Cap at 60s
                    time.sleep(delay)
                else:
                    raise
            else:
                raise  # Don't retry client errors
```

### Upload Failure Recovery

- On batch failure, log which standard set and batch failed
- Continue with remaining sets if `--all` flag is used
- Do NOT create `.pinecone_uploaded` marker for failed sets
- User can re-run command to retry failed sets

---

## Pinecone SDK Requirements

### Installation

```bash
pip install pinecone          # ✅ Correct (current SDK)
# NOT: pip install pinecone-client  # ❌ Deprecated
```

### Initialization

```python
from pinecone import Pinecone
import os

api_key = os.getenv("PINECONE_API_KEY")
if not api_key:
    raise ValueError("PINECONE_API_KEY environment variable not set")

pc = Pinecone(api_key=api_key)
index = pc.Index("common-core-standards")
```

### Index Validation

Use SDK to check index exists before upload:

```python
if not pc.has_index(index_name):
    # Fail with helpful message including the CLI command to create index
    raise ValueError(f"Index '{index_name}' not found. Create it with:\n"
                     f"pc index create -n {index_name} -m cosine -c aws -r us-east-1 "
                     f"--model llama-text-embed-v2 --field_map text=content")
```

### Upserting Records

**Critical**: Use `upsert_records()` for indexes with integrated embeddings, NOT `upsert()`:

```python
# ✅ Correct - for integrated embeddings
index.upsert_records(namespace, records)

# ❌ Wrong - this is for pre-computed vectors
index.upsert(vectors=...)
```

### Batch Processing

```python
def batch_upsert(index, namespace, records, batch_size=96):
    """Upsert records in batches with rate limiting."""
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        exponential_backoff_retry(
            lambda b=batch: index.upsert_records(namespace, b)
        )
        time.sleep(0.1)  # Rate limiting between batches
```

### Key Constraints

| Constraint          | Limit                                      | Notes                                    |
| ------------------- | ------------------------------------------ | ---------------------------------------- |
| Text batch size     | 96 records                                 | Also 2MB total per batch                 |
| Metadata per record | 40KB                                       | Flat JSON only                           |
| Metadata types      | strings, ints, floats, bools, string lists | No nested objects                        |
| Consistency         | Eventually consistent                      | Wait ~1-5s after upsert before searching |

### Record Format

Records must have:

- `_id`: Unique identifier (string)
- `content`: Text field for embedding (must match `field_map` in index config)
- Additional flat metadata fields (no nesting)

```python
record = {
    "_id": "EA60C8D165F6481B90BFF782CE193F93",
    "content": "Depth 0: Geometry\nDepth 1 (1.G.K): ...",  # Embedded by Pinecone
    "subject": "Mathematics",  # Flat metadata
    "jurisdiction_title": "Wyoming",
    "depth": 3,  # int allowed
    "is_root": False,  # bool allowed
    "parent_id": "3445678A...",  # null for root nodes
}
```

### Common Mistakes to Avoid

1. **Nested metadata**: Will cause API errors

   ```python
   # ❌ Wrong
   {"user": {"name": "John"}}
   # ✅ Correct
   {"user_name": "John"}
   ```

2. **Hardcoded API keys**: Always use environment variables

3. **Missing namespace**: Always specify namespace in all operations

4. **Wrong upsert method**: Use `upsert_records()` not `upsert()` for integrated embeddings

---

## Assumptions and Dependencies

### Assumptions

- Pinecone free tier limits are sufficient for initial dataset
- The index has been created manually via Pinecone CLI before running upload
- API key has been configured in environment

### Dependencies

- Python 3.12+
- `pinecone` SDK (current version, 2025)
- Pinecone account with API key
- Network access to Pinecone API
