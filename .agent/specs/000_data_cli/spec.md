# Data Ingestion CLI Specification

**Tool Name:** Common Core MCP Data CLI
**Framework:** `typer` (Python)
**Purpose:** To explore, discover, and download official standard sets (e.g., Utah Math, Wyoming Science) from the Common Standards Project API for local processing.
**Scope:** Development Tool (Dev Dependency). Not deployed to production.

**Architecture:** Clean separation between CLI interface (`tools/cli.py`) and business logic (`tools/api_client.py`, `tools/data_processor.py`). The CLI file contains only command definitions and invokes reusable functions.

**Initial Proof of Concept:** Grade 3 Mathematics for Utah, Wyoming, and Idaho.

---

## 1. Environment & Setup

### 1.1 Prerequisites

To use this CLI, you must register for an API key.

1.  Go to [Common Standards Project Developers](https://commonstandardsproject.com/developers).
2.  Create an account and generate an **API Key**.

### 1.2 Configuration (`.env`)

The CLI must load sensitive credentials from a local `.env` file.

```bash
# .env file in project root
CSP_API_KEY=your_generated_api_key_here
```

### 1.3 Dependencies (`pyproject.toml`)

Add these to the existing `[project.dependencies]` section:

```toml
[project.dependencies]
# ... existing dependencies ...
"typer",          # CLI framework
"requests",       # HTTP client for API calls
"rich",           # Pretty printing tables in terminal
"loguru",         # Structured logging
```

**Note:** `python-dotenv` is already in the project dependencies.

### 1.4 CLI Invocation

The CLI is invoked directly with Python (not via `uv`):

```bash
python tools/cli.py --help
```

---

## 2. API Reference (Internal)

The CLI acts as a wrapper around these specific Common Standards Project API endpoints.

**Base URL:** `https://api.commonstandardsproject.com/api/v1`
**Authentication:** Header `Api-Key: <YOUR_KEY>`

### Endpoint A: List Jurisdictions

- **URL:** `/jurisdictions`
- **Purpose:** Find the ID for "Utah", "Wyoming", "Idaho".
- **Response Shape:**
  ```json
  {
    "data": [
      { "id": "49FCDFBD...", "title": "Utah", "type": "state" },
      ...
    ]
  }
  ```

### Endpoint B: List Standard Sets

- **URL:** `/standard_sets`
- **Query Params:** `jurisdictionId=<ID>`
- **Purpose:** Find "Utah Core Standards - Mathematics - Grade 3".
- **Response Shape:**
  ```json
  {
    "data": [
      {
        "id": "SOME_SET_ID",
        "title": "Utah Core Standards - Mathematics",
        "subject": "Mathematics",
        "educationLevels": ["03"]
      }
    ]
  }
  ```

### Endpoint C: Get Standard Set (Download)

- **URL:** `/standard_sets/{standard_set_id}`
- **Purpose:** Download the full hierarchy for a specific set.
- **Response Shape:** Returns a complex object containing the full tree (Standards, Clusters, etc.).

---

## 3. CLI Architecture

### 3.1 File Structure

The CLI is organized with clean separation of concerns:

- **`tools/cli.py`**: CLI command definitions only (uses Typer). Imports and invokes functions from other modules.
- **`tools/api_client.py`**: Business logic for interacting with Common Standards Project API. Includes retry mechanisms, rate limiting, and error handling.
- **`tools/data_processor.py`**: Business logic for processing raw API data into flattened format with embeddings.
- **`tools/data_manager.py`**: Business logic for managing local data files (listing, status tracking, cleanup).

### 3.2 Command Structure

```bash
# View help
python tools/cli.py --help

# Explore API
python tools/cli.py jurisdictions --search "Utah"
python tools/cli.py sets <JURISDICTION_ID>

# Download raw data
python tools/cli.py download <SET_ID>

# View local data
python tools/cli.py list

# Process raw data
python tools/cli.py process <SET_ID>

# Check processing status
python tools/cli.py status
```

---

## 4. Command Specifications

### Command 1: `jurisdictions`

Allows the developer to find the internal IDs for states/organizations.

- **Arguments:** None.
- **Options:**
  - `--search` / `-s` (Optional): Filter output by name (case-insensitive).
- **Business Logic:** Implemented in `api_client.get_jurisdictions(search_term: str | None) -> list[dict]`
- **Display Logic:**
  1.  Call `api_client.get_jurisdictions()`.
  2.  Print table using `rich.table.Table`: `ID | Title | Type`.
  3.  Log operation with loguru.

### Command 2: `sets`

Allows the developer to see what standards are available for a specific state.

- **Arguments:**
  - `jurisdiction_id` (Required): The ID found in the previous command.
- **Business Logic:** Implemented in `api_client.get_standard_sets(jurisdiction_id: str) -> list[dict]`
- **Display Logic:**
  1.  Call `api_client.get_standard_sets(jurisdiction_id)`.
  2.  Print table: `Set ID | Subject | Title | Grade Levels`.
  3.  Log operation.

### Command 3: `download`

Downloads the official JSON definition for a standard set and saves it locally with organized directory structure.

- **Arguments:**
  - `set_id` (Required): The ID of the standard set (e.g., Utah Math).
- **Options:** None (output path is automatically determined based on metadata).
- **Business Logic:** Implemented in `api_client.download_standard_set(set_id: str) -> dict` and `data_manager.save_raw_data(set_id: str, data: dict, metadata: dict) -> Path`
- **Workflow:**
  1.  Call `api_client.download_standard_set(set_id)` (includes retry logic).
  2.  Extract metadata: jurisdiction, subject, grade levels.
  3.  Call `data_manager.save_raw_data()` to save with auto-generated path.
  4.  Print success message with file path.
  5.  Log download operation.

### Command 4: `list`

Shows all downloaded raw datasets with their metadata.

- **Arguments:** None.
- **Business Logic:** Implemented in `data_manager.list_downloaded_data() -> list[dict]`
- **Display Logic:**
  1.  Call `data_manager.list_downloaded_data()`.
  2.  Print table: `Set ID | Subject | Title | Grade Levels | Downloaded | Processed`.
  3.  Show total count.

### Command 5: `process`

Processes a raw downloaded dataset into flattened format with embeddings.

- **Arguments:**
  - `set_id` (Required): The ID of the standard set to process.
- **Business Logic:** Implemented in `data_processor.process_standard_set(set_id: str) -> tuple[Path, Path]`
- **Workflow:**
  1.  Verify raw data exists for set_id.
  2.  Call `data_processor.process_standard_set(set_id)`.
  3.  Generate flattened standards.json.
  4.  Generate embeddings.npy.
  5.  Save to `data/processed/<jurisdiction>/<subject>/`.
  6.  Update processing status metadata.
  7.  Print success message with output paths.
  8.  Log processing operation.

### Command 6: `status`

Shows processing status for all datasets (processed vs unprocessed).

- **Arguments:** None.
- **Business Logic:** Implemented in `data_manager.get_processing_status() -> dict`
- **Display Logic:**
  1.  Call `data_manager.get_processing_status()`.
  2.  Show summary: Total Downloaded, Processed, Unprocessed.
  3.  List unprocessed datasets.
  4.  List processed datasets with output paths.

---

## 5. Data Directory Structure

### 5.1 Raw Data Organization

Downloaded raw data is organized by jurisdiction and stored locally only (not in git):

```
data/raw/
├── <jurisdiction_id>/
│   ├── <set_id>/
│   │   ├── data.json              # Raw API response
│   │   └── metadata.json          # Download metadata
│   └── <set_id>/
│       ├── data.json
│       └── metadata.json
```

**Example:**

```
data/raw/
├── 49FCDFBD.../                   # Utah
│   ├── ABC123.../                 # Utah Math Grade 3
│   │   ├── data.json
│   │   └── metadata.json
│   └── DEF456.../                 # Utah Science Grade 5
│       ├── data.json
│       └── metadata.json
├── 82ABCDEF.../                   # Wyoming
    └── GHI789.../                 # Wyoming Math Grade 3
        ├── data.json
        └── metadata.json
```

### 5.2 Processed Data Organization

Processed data (flattened standards with embeddings) is organized by logical grouping:

```
data/processed/
├── <jurisdiction_name>/
│   ├── <subject>/
│   │   ├── <grade_level>/
│   │   │   ├── standards.json     # Flattened standards
│   │   │   └── embeddings.npy     # Vector embeddings
```

**Example (Initial Proof of Concept):**

```
data/processed/
├── utah/
│   └── mathematics/
│       └── grade_03/
│           ├── standards.json
│           └── embeddings.npy
├── wyoming/
│   └── mathematics/
│       └── grade_03/
│           ├── standards.json
│           └── embeddings.npy
├── idaho/
    └── mathematics/
        └── grade_03/
            ├── standards.json
            └── embeddings.npy
```

**Git Tracking:**

- `data/raw/` is added to `.gitignore` (local only)
- `data/processed/` for example datasets (Utah, Wyoming, Idaho Math Grade 3) is committed to git
- For production expansion, processed data would move to a vector database

### 5.3 Metadata Schema

The `metadata.json` file stored with each raw dataset:

```json
{
  "set_id": "ABC123...",
  "title": "Utah Core Standards - Mathematics - Grade 3",
  "jurisdiction": {
    "id": "49FCDFBD...",
    "title": "Utah"
  },
  "subject": "Mathematics",
  "grade_levels": ["03"],
  "download_date": "2024-11-25T10:30:00Z",
  "download_url": "https://api.commonstandardsproject.com/api/v1/standard_sets/ABC123...",
  "processed": false,
  "processed_date": null,
  "processed_output": null
}
```

---

## 6. Implementation Guide

The implementation follows clean architecture principles with separated concerns.

### 6.1 API Client Module (`tools/api_client.py`)

Handles all interactions with the Common Standards Project API, including retry logic, rate limiting, and error handling.

```python
"""API client for Common Standards Project with retry logic and rate limiting."""
from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

API_KEY = os.getenv("CSP_API_KEY")
BASE_URL = "https://api.commonstandardsproject.com/api/v1"

# Rate limiting: Max requests per minute
MAX_REQUESTS_PER_MINUTE = 60
_request_timestamps: list[float] = []


class APIError(Exception):
    """Raised when API request fails after all retries."""
    pass


def _get_headers() -> dict[str, str]:
    """Get authentication headers for API requests."""
    if not API_KEY:
        logger.error("CSP_API_KEY not found in .env file")
        raise ValueError("CSP_API_KEY environment variable not set")
    return {"Api-Key": API_KEY}


def _enforce_rate_limit() -> None:
    """Enforce rate limiting by tracking request timestamps."""
    global _request_timestamps
    now = time.time()

    # Remove timestamps older than 1 minute
    _request_timestamps = [ts for ts in _request_timestamps if now - ts < 60]

    # If at limit, wait
    if len(_request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        sleep_time = 60 - (now - _request_timestamps[0])
        logger.warning(f"Rate limit reached. Waiting {sleep_time:.1f} seconds...")
        time.sleep(sleep_time)
        _request_timestamps = []

    _request_timestamps.append(now)


def _make_request(
    endpoint: str,
    params: dict[str, Any] | None = None,
    max_retries: int = 3
) -> dict[str, Any]:
    """
    Make API request with exponential backoff retry logic.

    Args:
        endpoint: API endpoint path (e.g., "/jurisdictions")
        params: Query parameters
        max_retries: Maximum number of retry attempts

    Returns:
        Parsed JSON response

    Raises:
        APIError: After all retries exhausted or on fatal errors
    """
    url = f"{BASE_URL}{endpoint}"
    headers = _get_headers()

    for attempt in range(max_retries):
        try:
            _enforce_rate_limit()

            logger.debug(f"API request: {endpoint} (attempt {attempt + 1}/{max_retries})")
            response = requests.get(url, headers=headers, params=params, timeout=30)

            # Handle specific status codes
            if response.status_code == 401:
                logger.error("Invalid API key (401 Unauthorized)")
                raise APIError("Authentication failed. Check your CSP_API_KEY in .env")

            if response.status_code == 404:
                logger.error(f"Resource not found (404): {endpoint}")
                raise APIError(f"Resource not found: {endpoint}")

            if response.status_code == 429:
                # Rate limited by server
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Server rate limit hit. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            logger.info(f"API request successful: {endpoint}")
            return response.json()

        except requests.exceptions.Timeout:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.warning(f"Request timeout. Retrying in {wait_time}s...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                raise APIError(f"Request timeout after {max_retries} attempts")

        except requests.exceptions.ConnectionError:
            wait_time = 2 ** attempt
            logger.warning(f"Connection error. Retrying in {wait_time}s...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                raise APIError(f"Connection failed after {max_retries} attempts")

        except requests.exceptions.HTTPError as e:
            # Don't retry on 4xx errors (except 429)
            if 400 <= response.status_code < 500 and response.status_code != 429:
                raise APIError(f"HTTP {response.status_code}: {response.text}")
            # Retry on 5xx errors
            wait_time = 2 ** attempt
            logger.warning(f"Server error {response.status_code}. Retrying in {wait_time}s...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                raise APIError(f"Server error after {max_retries} attempts")

    raise APIError("Request failed after all retries")


def get_jurisdictions(search_term: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch all jurisdictions from the API.

    Args:
        search_term: Optional filter for jurisdiction title (case-insensitive)

    Returns:
        List of jurisdiction dicts with 'id', 'title', 'type' fields
    """
    logger.info("Fetching jurisdictions from API")
    response = _make_request("/jurisdictions")
    jurisdictions = response.get("data", [])

    if search_term:
        search_lower = search_term.lower()
        jurisdictions = [
            j for j in jurisdictions
            if search_lower in j.get("title", "").lower()
        ]
        logger.info(f"Filtered to {len(jurisdictions)} jurisdictions matching '{search_term}'")

    return jurisdictions


def get_standard_sets(jurisdiction_id: str) -> list[dict[str, Any]]:
    """
    Fetch standard sets for a specific jurisdiction.

    Args:
        jurisdiction_id: The jurisdiction GUID

    Returns:
        List of standard set dicts
    """
    logger.info(f"Fetching standard sets for jurisdiction {jurisdiction_id}")
    response = _make_request("/standard_sets", params={"jurisdictionId": jurisdiction_id})
    return response.get("data", [])


def download_standard_set(set_id: str) -> dict[str, Any]:
    """
    Download full standard set data.

    Args:
        set_id: The standard set GUID

    Returns:
        Complete standard set data including hierarchy
    """
    logger.info(f"Downloading standard set {set_id}")
    response = _make_request(f"/standard_sets/{set_id}")
    return response.get("data", {})
```

### 6.2 Data Manager Module (`tools/data_manager.py`)

Handles local file operations, directory structure, and metadata tracking.

```python
"""Manages local data storage and metadata tracking."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

# Data directories
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def save_raw_data(set_id: str, data: dict[str, Any], metadata_override: dict[str, Any] | None = None) -> Path:
    """
    Save raw standard set data with metadata.

    Args:
        set_id: Standard set GUID
        data: Raw API response data
        metadata_override: Optional metadata to merge (for jurisdiction info, etc.)

    Returns:
        Path to saved data file
    """
    # Extract metadata from data
    jurisdiction_id = data.get("jurisdiction", {}).get("id", "unknown")
    jurisdiction_title = data.get("jurisdiction", {}).get("title", "Unknown")

    # Create directory structure
    set_dir = RAW_DATA_DIR / jurisdiction_id / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    # Save raw data
    data_file = set_dir / "data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Create metadata
    metadata = {
        "set_id": set_id,
        "title": data.get("title", ""),
        "jurisdiction": {
            "id": jurisdiction_id,
            "title": jurisdiction_title
        },
        "subject": data.get("subject", "Unknown"),
        "grade_levels": data.get("educationLevels", []),
        "download_date": datetime.utcnow().isoformat() + "Z",
        "download_url": f"https://api.commonstandardsproject.com/api/v1/standard_sets/{set_id}",
        "processed": False,
        "processed_date": None,
        "processed_output": None
    }

    # Merge override metadata
    if metadata_override:
        metadata.update(metadata_override)

    # Save metadata
    metadata_file = set_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved raw data to {data_file}")
    logger.info(f"Saved metadata to {metadata_file}")

    return data_file


def list_downloaded_data() -> list[dict[str, Any]]:
    """
    List all downloaded raw datasets with their metadata.

    Returns:
        List of metadata dicts for each downloaded dataset
    """
    if not RAW_DATA_DIR.exists():
        return []

    datasets = []
    for jurisdiction_dir in RAW_DATA_DIR.iterdir():
        if not jurisdiction_dir.is_dir():
            continue

        for set_dir in jurisdiction_dir.iterdir():
            if not set_dir.is_dir():
                continue

            metadata_file = set_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)
                    datasets.append(metadata)

    logger.debug(f"Found {len(datasets)} downloaded datasets")
    return datasets


def get_processing_status() -> dict[str, Any]:
    """
    Get processing status summary for all datasets.

    Returns:
        Dict with 'total', 'processed', 'unprocessed', 'processed_list', 'unprocessed_list'
    """
    datasets = list_downloaded_data()
    processed = [d for d in datasets if d.get("processed", False)]
    unprocessed = [d for d in datasets if not d.get("processed", False)]

    return {
        "total": len(datasets),
        "processed": len(processed),
        "unprocessed": len(unprocessed),
        "processed_list": processed,
        "unprocessed_list": unprocessed
    }


def mark_as_processed(set_id: str, output_path: Path) -> None:
    """
    Update metadata to mark a dataset as processed.

    Args:
        set_id: Standard set GUID
        output_path: Path to processed output directory
    """
    # Find the dataset
    for jurisdiction_dir in RAW_DATA_DIR.iterdir():
        if not jurisdiction_dir.is_dir():
            continue

        set_dir = jurisdiction_dir / set_id
        if set_dir.exists():
            metadata_file = set_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)

                metadata["processed"] = True
                metadata["processed_date"] = datetime.utcnow().isoformat() + "Z"
                metadata["processed_output"] = str(output_path)

                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                logger.info(f"Marked {set_id} as processed")
                return

    logger.warning(f"Could not find dataset {set_id} to mark as processed")
```

### 6.3 Data Processor Module (`tools/data_processor.py`)

Handles the transformation of raw API data into flattened format with embeddings.

```python
"""Processes raw standard sets into flattened format with embeddings."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer

from tools.data_manager import PROCESSED_DATA_DIR, RAW_DATA_DIR, mark_as_processed


def _build_lookup_map(standards_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Build lookup map from standards dictionary in API response.

    The API returns standards in a flat dictionary keyed by GUID.

    Args:
        standards_dict: The 'standards' field from API response

    Returns:
        Lookup map of GUID -> standard object
    """
    logger.debug(f"Building lookup map with {len(standards_dict)} items")
    return standards_dict


def _resolve_context(standard: dict[str, Any], lookup_map: dict[str, Any]) -> str:
    """
    Build full context string by resolving ancestor chain.

    Concatenates descriptions from Domain -> Cluster -> Standard
    to create rich context for embedding.

    Args:
        standard: Standard dict with 'ancestorIds' and 'description'
        lookup_map: Map of GUID -> standard object

    Returns:
        Full context string with ancestors
    """
    context_parts = []

    # Resolve ancestors
    ancestor_ids = standard.get("ancestorIds", [])
    for ancestor_id in ancestor_ids:
        if ancestor_id in lookup_map:
            ancestor = lookup_map[ancestor_id]
            ancestor_desc = ancestor.get("description", "").strip()
            if ancestor_desc:
                context_parts.append(ancestor_desc)

    # Add standard's own description
    standard_desc = standard.get("description", "").strip()
    if standard_desc:
        context_parts.append(standard_desc)

    return " - ".join(context_parts)


def _extract_grade(grade_levels: list[str]) -> str:
    """Extract primary grade level from gradeLevels array."""
    if not grade_levels:
        return "Unknown"

    grade = grade_levels[0]

    # Handle high school ranges
    if grade in ["09", "10", "11", "12"]:
        return "09-12"

    return grade


def _process_standards(
    data: dict[str, Any],
    lookup_map: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Filter and process standards from raw API data.

    Keeps only items where statementLabel == "Standard".

    Args:
        data: Raw API response
        lookup_map: Map of GUID -> standard object

    Returns:
        List of processed standard dicts
    """
    processed = []
    standards_dict = data.get("standards", {})
    subject = data.get("subject", "Unknown")

    for guid, item in standards_dict.items():
        # Filter: Keep only "Standard" items
        if item.get("statementLabel") != "Standard":
            continue

        # Extract fields
        standard_id = item.get("statementNotation", "")
        grade_levels = item.get("educationLevels", [])
        grade = _extract_grade(grade_levels)
        description = item.get("description", "").strip()

        # Skip if missing critical fields
        if not standard_id or not description:
            continue

        # Resolve full context
        full_context = _resolve_context(item, lookup_map)

        # Build output record
        record = {
            "id": standard_id,
            "guid": guid,
            "subject": subject,
            "grade": grade,
            "description": description,
            "full_context": full_context
        }

        processed.append(record)

    logger.info(f"Processed {len(processed)} standards")
    return processed


def _generate_embeddings(standards: list[dict[str, Any]]) -> np.ndarray:
    """
    Generate embeddings for all standards.

    Uses sentence-transformers with 'full_context' field.

    Args:
        standards: List of standard dicts

    Returns:
        Numpy array of embeddings
    """
    logger.info("Initializing sentence-transformers model...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    contexts = [s["full_context"] for s in standards]

    logger.info(f"Generating embeddings for {len(contexts)} standards...")
    embeddings = model.encode(contexts, show_progress_bar=True)

    return embeddings


def process_standard_set(set_id: str) -> tuple[Path, Path]:
    """
    Process a raw standard set into flattened format with embeddings.

    Args:
        set_id: Standard set GUID

    Returns:
        Tuple of (standards_file_path, embeddings_file_path)

    Raises:
        FileNotFoundError: If raw data not found for set_id
        ValueError: If processing fails
    """
    logger.info(f"Processing standard set {set_id}")

    # Find raw data
    raw_data_file = None
    metadata_file = None

    for jurisdiction_dir in RAW_DATA_DIR.iterdir():
        if not jurisdiction_dir.is_dir():
            continue

        set_dir = jurisdiction_dir / set_id
        if set_dir.exists():
            raw_data_file = set_dir / "data.json"
            metadata_file = set_dir / "metadata.json"
            break

    if not raw_data_file or not raw_data_file.exists():
        raise FileNotFoundError(f"Raw data not found for set {set_id}. Run download first.")

    # Load metadata
    with open(metadata_file, encoding="utf-8") as f:
        metadata = json.load(f)

    # Load raw data
    with open(raw_data_file, encoding="utf-8") as f:
        raw_data = json.load(f)

    # Build lookup map
    standards_dict = raw_data.get("standards", {})
    lookup_map = _build_lookup_map(standards_dict)

    # Process standards
    processed_standards = _process_standards(raw_data, lookup_map)

    if not processed_standards:
        raise ValueError(f"No standards processed from set {set_id}")

    # Generate embeddings
    embeddings = _generate_embeddings(processed_standards)

    # Determine output path
    jurisdiction_name = metadata["jurisdiction"]["title"].lower().replace(" ", "_")
    subject_name = metadata["subject"].lower().replace(" ", "_").replace("-", "_")
    grade = _extract_grade(metadata["grade_levels"])
    grade_str = f"grade_{grade}".replace("-", "_")

    output_dir = PROCESSED_DATA_DIR / jurisdiction_name / subject_name / grade_str
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save standards
    standards_file = output_dir / "standards.json"
    with open(standards_file, "w", encoding="utf-8") as f:
        json.dump(processed_standards, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved standards to {standards_file}")

    # Save embeddings
    embeddings_file = output_dir / "embeddings.npy"
    np.save(embeddings_file, embeddings)
    logger.info(f"Saved embeddings to {embeddings_file}")

    # Mark as processed
    mark_as_processed(set_id, output_dir)

    return standards_file, embeddings_file
```

### 6.4 CLI Entry Point (`tools/cli.py`)

Thin CLI layer that imports and invokes business logic functions.

```python
"""CLI entry point for EduMatch Data Management."""
from __future__ import annotations

import sys

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from tools import api_client, data_manager, data_processor

# Configure logger
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
logger.add("data/cli.log", rotation="10 MB", retention="7 days", format="{time} | {level} | {message}")

app = typer.Typer(help="EduMatch Data CLI - Manage educational standards data")
console = Console()


@app.command()
def jurisdictions(
    search: str = typer.Option(None, "--search", "-s", help="Filter by jurisdiction name")
):
    """List all available jurisdictions (states/organizations)."""
    try:
        results = api_client.get_jurisdictions(search)

        table = Table("ID", "Title", "Type", title="Jurisdictions")
        for j in results:
            table.add_row(
                j.get("id", ""),
                j.get("title", ""),
                j.get("type", "N/A")
            )

        console.print(table)
        console.print(f"\n[green]Found {len(results)} jurisdictions[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to fetch jurisdictions")
        raise typer.Exit(code=1)


@app.command()
def sets(jurisdiction_id: str = typer.Argument(..., help="Jurisdiction ID")):
    """List standard sets for a specific jurisdiction."""
    try:
        results = api_client.get_standard_sets(jurisdiction_id)

        table = Table("Set ID", "Subject", "Title", "Grades", title=f"Standard Sets")
        for s in results:
            grade_levels = ", ".join(s.get("educationLevels", []))
            table.add_row(
                s.get("id", ""),
                s.get("subject", "N/A"),
                s.get("title", ""),
                grade_levels or "N/A"
            )

        console.print(table)
        console.print(f"\n[green]Found {len(results)} standard sets[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to fetch standard sets")
        raise typer.Exit(code=1)


@app.command()
def download(set_id: str = typer.Argument(..., help="Standard set ID")):
    """Download a standard set and save locally."""
    try:
        with console.status(f"[bold blue]Downloading set {set_id}..."):
            data = api_client.download_standard_set(set_id)
            output_path = data_manager.save_raw_data(set_id, data)

        console.print(f"[green]✓ Successfully downloaded to {output_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to download standard set")
        raise typer.Exit(code=1)


@app.command()
def list():
    """List all downloaded datasets."""
    try:
        datasets = data_manager.list_downloaded_data()

        if not datasets:
            console.print("[yellow]No datasets downloaded yet.[/yellow]")
            return

        table = Table("Set ID", "Subject", "Title", "Grades", "Downloaded", "Processed", title="Downloaded Datasets")
        for d in datasets:
            table.add_row(
                d["set_id"][:12] + "...",
                d.get("subject", "N/A"),
                d.get("title", "")[:50],
                ", ".join(d.get("grade_levels", [])),
                d.get("download_date", "")[:10],
                "✓" if d.get("processed") else "✗"
            )

        console.print(table)
        console.print(f"\n[green]Total: {len(datasets)} datasets[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to list datasets")
        raise typer.Exit(code=1)


@app.command()
def process(set_id: str = typer.Argument(..., help="Standard set ID to process")):
    """Process a downloaded dataset into flattened format with embeddings."""
    try:
        with console.status(f"[bold blue]Processing set {set_id}..."):
            standards_file, embeddings_file = data_processor.process_standard_set(set_id)

        console.print(f"[green]✓ Processing complete![/green]")
        console.print(f"  Standards: {standards_file}")
        console.print(f"  Embeddings: {embeddings_file}")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Hint: Run 'download' command first.[/yellow]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to process dataset")
        raise typer.Exit(code=1)


@app.command()
def status():
    """Show processing status for all datasets."""
    try:
        status_data = data_manager.get_processing_status()

        console.print(f"\n[bold]Processing Status Summary[/bold]")
        console.print(f"  Total Downloaded: {status_data['total']}")
        console.print(f"  Processed: {status_data['processed']}")
        console.print(f"  Unprocessed: {status_data['unprocessed']}")

        if status_data["unprocessed_list"]:
            console.print(f"\n[yellow]Unprocessed Datasets:[/yellow]")
            for d in status_data["unprocessed_list"]:
                console.print(f"  • {d['title']} ({d['set_id'][:12]}...)")

        if status_data["processed_list"]:
            console.print(f"\n[green]Processed Datasets:[/green]")
            for d in status_data["processed_list"]:
                console.print(f"  • {d['title']}")
                console.print(f"    Output: {d.get('processed_output', 'N/A')}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to get status")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
```

---

## 7. API Data Format Reference

### 7.1 Raw Data Structure (from API)

When you run the `download` command, the `data/raw/<jurisdiction>/<set_id>/data.json` files will contain the Common Standards Project API response format:

```json
{
  "id": "SET_ID",
  "title": "Utah Core Standards - Mathematics",
  "subject": "Mathematics",
  "educationLevels": ["03"],
  "jurisdiction": {
    "id": "JURISDICTION_ID",
    "title": "Utah"
  },
  "standards": {
    "STANDARD_UUID": {
      "id": "STANDARD_UUID",
      "statementNotation": "3.OA.1",
      "description": "Interpret products of whole numbers...",
      "ancestorIds": ["CLUSTER_UUID", "DOMAIN_UUID"],
      "statementLabel": "Standard",
      "educationLevels": ["03"]
    },
    "CLUSTER_UUID": {
      "id": "CLUSTER_UUID",
      "description": "Represent and solve problems involving multiplication...",
      "statementLabel": "Cluster",
      "ancestorIds": ["DOMAIN_UUID"]
    },
    "DOMAIN_UUID": {
      "id": "DOMAIN_UUID",
      "description": "Operations and Algebraic Thinking",
      "statementLabel": "Domain",
      "ancestorIds": []
    }
  }
}
```

**Key Points:**

- The `standards` field is a flat dictionary keyed by GUID (not an array)
- Each item includes `ancestorIds` that reference other items in the same dictionary
- The `statementLabel` field indicates the type: "Domain", "Cluster", or "Standard"
- We filter to keep only `"statementLabel": "Standard"` items and resolve their ancestor context

### 7.2 Processed Data Format

After running the `process` command, the output `standards.json` has this flattened structure:

```json
[
  {
    "id": "CCSS.Math.Content.3.OA.A.1",
    "guid": "STANDARD_UUID",
    "subject": "Mathematics",
    "grade": "03",
    "description": "Interpret products of whole numbers...",
    "full_context": "Operations and Algebraic Thinking - Represent and solve problems involving multiplication... - Interpret products of whole numbers..."
  }
]
```

The `full_context` field is created by concatenating:

1. Domain description
2. Cluster description
3. Standard description

This rich context is used for generating embeddings that capture the hierarchical meaning.

---

## 8. Error Handling & Retry Logic

### 8.1 API Error Categories

The CLI handles these error scenarios:

| Error Type         | Status Code | Behavior                                     |
| ------------------ | ----------- | -------------------------------------------- |
| Invalid API Key    | 401         | Stop immediately, show error message         |
| Resource Not Found | 404         | Stop immediately, show helpful error         |
| Rate Limited       | 429         | Wait for `Retry-After` header, then retry    |
| Timeout            | -           | Exponential backoff: 1s, 2s, 4s (3 attempts) |
| Connection Error   | -           | Exponential backoff: 1s, 2s, 4s (3 attempts) |
| Server Error       | 5xx         | Exponential backoff: 1s, 2s, 4s (3 attempts) |
| Client Error       | 4xx         | Stop immediately (no retry)                  |

### 8.2 Rate Limiting

- **Client-Side Limit:** 60 requests per minute
- **Implementation:** Track request timestamps, enforce delays when limit reached
- **Server-Side Limit:** Respect `429` status and `Retry-After` header

### 8.3 Logging

All operations are logged using `loguru`:

- **Console:** Formatted output with timestamps and log levels
- **File:** `data/cli.log` with rotation (10MB max, 7 days retention)
- **Exception Tracking:** Full stack traces logged for debugging

---

## 9. Git Configuration

### 9.1 .gitignore Additions

Add to `.gitignore`:

```
# Raw data (local only)
data/raw/

# CLI logs
data/cli.log
```

### 9.2 Git Tracking

**Tracked in Git:**

- `data/processed/utah/mathematics/grade_03/` (example dataset)
- `data/processed/wyoming/mathematics/grade_03/` (example dataset)
- `data/processed/idaho/mathematics/grade_03/` (example dataset)

**Not Tracked:**

- `data/raw/` (developer's local cache)
- `data/cli.log` (operational logs)

---

## 10. Testing Strategy

### 10.1 Manual Testing Checklist

For this initial sprint, manual testing is sufficient. Complete these test scenarios:

**API Discovery:**

- [ ] Run `jurisdictions` command without search
- [ ] Run `jurisdictions --search "Utah"` to filter
- [ ] Verify table output is readable
- [ ] Confirm logging to console and file

**Standard Set Discovery:**

- [ ] Find Utah jurisdiction ID from previous step
- [ ] Run `sets <UTAH_ID>` to list available standards
- [ ] Identify Mathematics Grade 3 set ID
- [ ] Repeat for Wyoming and Idaho

**Data Download:**

- [ ] Run `download <SET_ID>` for Utah Math Grade 3
- [ ] Verify file created in `data/raw/<jurisdiction>/<set_id>/data.json`
- [ ] Verify metadata created in `data/raw/<jurisdiction>/<set_id>/metadata.json`
- [ ] Repeat for Wyoming and Idaho Math Grade 3
- [ ] Run `list` command to see all downloads

**Data Processing:**

- [ ] Run `status` to see unprocessed datasets
- [ ] Run `process <SET_ID>` for Utah Math Grade 3
- [ ] Verify `data/processed/utah/mathematics/grade_03/standards.json` created
- [ ] Verify `data/processed/utah/mathematics/grade_03/embeddings.npy` created
- [ ] Run `status` again to confirm marked as processed
- [ ] Repeat for Wyoming and Idaho

**Error Handling:**

- [ ] Test with invalid API key (should fail immediately with clear message)
- [ ] Test `download` with invalid set ID (should show 404 error)
- [ ] Test `process` without downloading first (should show helpful error)

### 10.2 Validation Criteria

After processing all three datasets, verify:

- Each `standards.json` contains array of standard objects
- Each standard has all required fields: `id`, `guid`, `subject`, `grade`, `description`, `full_context`
- The `full_context` field is not empty and contains ancestor descriptions
- Each `embeddings.npy` file shape matches the number of standards
- Metadata files correctly show `"processed": true`

---

## 11. Implementation Workflow

### 11.1 Development Order

Implement modules in this order:

1. **`tools/api_client.py`** - Core API interactions with retry logic
2. **`tools/data_manager.py`** - File management and metadata tracking
3. **`tools/data_processor.py`** - Data transformation and embeddings
4. **`tools/cli.py`** - CLI commands that tie everything together

### 11.2 Testing Workflow

After implementing each module:

1. Test API discovery commands (`jurisdictions`, `sets`)
2. Test download command for one dataset
3. Test list command
4. Test process command
5. Test status command
6. Repeat download and process for remaining datasets

### 11.3 Deliverables

**Code:**

- `tools/api_client.py`
- `tools/data_manager.py`
- `tools/data_processor.py`
- `tools/cli.py`

**Data (committed to git):**

- `data/processed/utah/mathematics/grade_03/standards.json`
- `data/processed/utah/mathematics/grade_03/embeddings.npy`
- `data/processed/wyoming/mathematics/grade_03/standards.json`
- `data/processed/wyoming/mathematics/grade_03/embeddings.npy`
- `data/processed/idaho/mathematics/grade_03/standards.json`
- `data/processed/idaho/mathematics/grade_03/embeddings.npy`

**Configuration:**

- Updated `pyproject.toml` with new dependencies
- Updated `.gitignore` with data/raw/ and data/cli.log

---

## 12. Future Enhancements

Features not included in this sprint but planned for future:

- **Batch Processing:** Command to process all downloaded datasets at once
- **Update Detection:** Check API for updates to already-downloaded sets
- **Data Validation:** Verify processed data integrity
- **Export Formats:** Support CSV or other output formats
- **Automated Tests:** Unit tests for each module
- **Configuration File:** YAML config for default settings (rate limits, retry attempts, etc.)
- **Progress Tracking:** Better progress bars for long operations

---

_This specification provides complete requirements for implementing a CLI tool to download and process Common Core standards from the Common Standards Project API, with clean architecture, robust error handling, and proper data organization for the MVP._
