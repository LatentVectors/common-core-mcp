# MCP Server Sprint Specification

## Overview

This sprint builds the MCP (Model Context Protocol) server that exposes the Pinecone database of educational standards to MCP clients (e.g., Claude Desktop). The server provides two methods of interacting with the Pinecone database:

1. **Semantic Search**: Vector similarity search using natural language queries to find relevant standards
2. **Direct ID Lookup**: Retrieve a specific standard by its GUID or identifier

---

## MCP Server Architecture

### Entry Point

The MCP server will be implemented as `server.py` in the project root. This file is minimal and focused on:

- Setting up the FastMCP server instance
- Defining tool decorators that delegate to logic in `src/`
- Running the server

The bulk of the logic lives in the `src/` directory, which serves as the authoritative location for shared code.

### Framework

Use `mcp.server.fastmcp.FastMCP` for the MCP server implementation. This provides a simple decorator-based API for defining tools.

### Code Organization

**Separation of Concerns:**

- `server.py` (root): Server setup, tool definitions, and delegation to `src/` modules
- `src/`: Authoritative location for all business logic, including Pinecone client and tool implementations
- `tools/`: CLI tools that import shared logic from `src/`

### Pinecone Client Migration

Move `tools/pinecone_client.py` to `src/pinecone_client.py`. Update all imports in `tools/` to import from `src.pinecone_client` instead. This establishes `src/` as the definitive source for Pinecone interaction logic.

### Configuration

Create a configuration module `src/mcp_config.py` that wraps or duplicates Pinecone configuration settings. This provides isolation from the CLI tools configuration.

**Configuration Requirements:**

- `PINECONE_API_KEY`: Pinecone API key (required)
- `PINECONE_INDEX_NAME`: Name of the Pinecone index (default: `common-core-standards`)
- `PINECONE_NAMESPACE`: Namespace for records (default: `standards`)

---

## MCP Tools

The server exposes two tools matching the MVP spec interface:

### Tool 1: `find_relevant_standards`

Performs semantic search over educational standards using vector similarity.

**Parameters:**

- `activity` (str, required): Natural language description of the learning activity
- `max_results` (int, optional, default: 5): Maximum number of standards to return
- `grade` (str, optional): Grade level filter (e.g., "K", "01", "05", "09")
- `subject` (str, optional): Subject filter (e.g., "Mathematics", "ELA-Literacy")

**Implementation:**

- Use Pinecone's `search()` method with integrated embeddings (`llama-text-embed-v2`)
- Pass the user's query text via `query={"inputs": {"text": activity}, "top_k": max_results}`
- Embeddings are generated automatically by Pinecone
- Apply metadata filters inside the query dict: `"filter": {...}` (only include key if filters exist)
- Always rerank results using `rerank={"model": "bge-reranker-v2-m3", "top_n": max_results, "rank_fields": ["content"]}`
- Access results via `results['result']['hits']`, extracting `_id`, `_score`, and `fields` from each hit
- Return top N matches sorted by reranked relevance score

**Response Format:**
Returns a JSON string with structured format:

```json
{
  "success": true,
  "results": [
    {
      "_id": "EA60C8D165F6481B90BFF782CE193F93",
      "content": "...",
      "subject": "Mathematics",
      "education_levels": ["01"],
      "statement_notation": "CCSS.Math.Content.1.OA.A.1",
      "standard_set_title": "...",
      "score": 0.85
    }
  ],
  "message": "Found 5 matching standards"
}
```

### Tool 2: `get_standard_details`

Retrieves a specific standard by its GUID or identifier.

**Parameters:**

- `standard_id` (str, required): The standard's GUID (`_id` field) or identifier

**Implementation:**

- Use Pinecone's `fetch()` method with the standard's GUID (`_id` field)
- If the identifier is not a GUID, may need to query by metadata filter on `statement_notation` or `asn_identifier` fields

**Response Format:**
Returns a JSON string with structured format:

```json
{
  "success": true,
  "results": [
    {
      "_id": "EA60C8D165F6481B90BFF782CE193F93",
      "content": "...",
      "subject": "Mathematics",
      "education_levels": ["01"],
      "statement_notation": "CCSS.Math.Content.1.OA.A.1",
      "standard_set_title": "...",
      "all_metadata_fields": "..."
    }
  ],
  "message": "Retrieved standard details"
}
```

---

## Error Handling

All tools catch exceptions and return structured error responses with `error_type` fields:

**Error Response Format:**

```json
{
  "success": false,
  "results": [],
  "message": "Error description",
  "error_type": "error_category"
}
```

**Valid `error_type` values:**

- `no_results`: Query returned no matches
- `invalid_input`: Malformed input (empty string, invalid ID format, etc.)
- `api_error`: Pinecone API failure or connection error
- `not_found`: Standard ID doesn't exist (for `get_standard_details`)

For `get_standard_details` with invalid ID, include a helpful suggestion:

```json
{
  "success": false,
  "results": [],
  "message": "Standard 'XYZ.123' not found. Try using find_relevant_standards with a keyword search instead.",
  "error_type": "not_found"
}
```

---

## Pinecone Integration

### Implementation Approach

Use the shared `PineconeClient` class from `src/pinecone_client.py`. The MCP server and CLI tools both import and use this shared client, ensuring consistency and avoiding code duplication. The `src/` directory is the authoritative location for Pinecone interaction logic.

### Extending PineconeClient

Add search and fetch methods to `src/pinecone_client.py`:

- `search_standards()`: Semantic search with filters
- `fetch_standard()`: Direct ID lookup

These methods encapsulate the Pinecone query logic and can be used by both the MCP server and CLI tools.

### Semantic Search Implementation

- Use Pinecone's `search()` method with integrated embeddings
- The index is configured with `llama-text-embed-v2` model and `field_map text=content`
- Pass query text to Pinecone's `search()` method using the `inputs` parameter - embeddings are generated automatically
- Always rerank results using the `bge-reranker-v2-m3` model for improved relevance
- Build filter dictionary dynamically (only include filters with values):
  - If `grade` provided: `{"education_levels": {"$in": [grade]}}`
  - If `subject` provided: `{"subject": {"$eq": subject}}`
  - Combine with `$and` if both: `{"$and": [grade_filter, subject_filter]}`
- Add filter to query dict only if it exists: `query_dict["filter"] = filter_dict`
- **Important**: Do not set `filter` to `None` — omit the key entirely when no filters

### Direct ID Lookup Implementation

- Use Pinecone's `fetch()` method with the standard's GUID (`_id` field)
- The `_id` field corresponds to the standard's GUID from the source data

### Pinecone Record Structure

Records in Pinecone follow the `PineconeRecord` model structure:

- `_id`: Standard GUID (string)
- `content`: Text content for embedding (string)
- `subject`: Subject name (string)
- `education_levels`: List of grade levels (list[str])
- `statement_notation`: CCSS notation if available (str | None)
- `standard_set_id`, `standard_set_title`, `jurisdiction_id`, etc.: Additional metadata fields

---

## File Structure

```
common_core_mcp/
├── server.py                    # MCP server entry point - minimal setup only (NEW)
├── src/
│   ├── pinecone_client.py      # Pinecone client (MOVED from tools/) (MODIFIED)
│   ├── mcp_config.py          # MCP-specific configuration (NEW)
│   ├── search.py               # Semantic search logic (NEW)
│   └── lookup.py               # Direct ID lookup logic (NEW)
├── tools/                       # CLI tools (MODIFIED - imports from src/)
│   └── pinecone_client.py      # (REMOVED - moved to src/)
├── data/                        # Existing data directory (unchanged)
└── pyproject.toml               # Dependencies (mcp already included)
```

### Files to Create

- **`server.py`** (project root): Minimal MCP server setup and tool definitions
- **`src/mcp_config.py`**: MCP-specific configuration module
- **`src/search.py`**: Semantic search implementation logic
- **`src/lookup.py`**: Direct ID lookup implementation logic

### Files to Move

- **`tools/pinecone_client.py`** → **`src/pinecone_client.py`**: Move Pinecone client to authoritative `src/` location

### Files to Modify

- **`tools/cli.py`**: Update imports to use `from src.pinecone_client import PineconeClient` (replace `from tools.pinecone_client`)
- **`tools/pinecone_processor.py`**: Update imports to use `from src.pinecone_client import PineconeClient` (replace `from tools.pinecone_client`)
- **`src/pinecone_client.py`**: Add `search_standards()` and `fetch_standard()` methods for MCP server use
- Any other files in `tools/` that import `pinecone_client`: Update to import from `src.pinecone_client`

### Files to Reference (Existing)

- **`tools/pinecone_models.py`**: Contains `PineconeRecord` model structure for reference (may also move to `src/` in future)
- **`tools/config.py`**: Contains `ToolsSettings` for reference (but MCP uses separate config)

---

## Implementation Details

### Server Entry Point (`server.py`)

The `server.py` file should be minimal and focused on setup:

1. Import FastMCP and create server instance:

   ```python
   from mcp.server.fastmcp import FastMCP
   mcp = FastMCP("CommonCore")
   ```

2. Import tool logic functions from `src/` modules
3. Define thin wrapper functions with `@mcp.tool()` decorator that delegate to `src/` logic
4. Run server with `mcp.run()` when executed directly

**Example Structure:**

```python
from mcp.server.fastmcp import FastMCP
from src.search import find_relevant_standards_impl
from src.lookup import get_standard_details_impl

mcp = FastMCP("CommonCore")

@mcp.tool()
def find_relevant_standards(activity: str, max_results: int = 5, grade: str | None = None, subject: str | None = None) -> str:
    """Returns educational standards relevant to the activity."""
    return find_relevant_standards_impl(activity, max_results, grade, subject)

@mcp.tool()
def get_standard_details(standard_id: str) -> str:
    """Returns full metadata for a standard by its GUID or identifier."""
    return get_standard_details_impl(standard_id)

if __name__ == "__main__":
    mcp.run()
```

**Execution:**

- Run with: `uv run server.py` or `python server.py`
- Server communicates via stdio (FastMCP handles transport automatically)

### Configuration Module (`src/mcp_config.py`)

Create a configuration module that:

- Loads environment variables from `.env` file
- Provides settings for Pinecone connection (API key, index name, namespace)
- Can duplicate or wrap settings from `tools/config.py` but maintains isolation

**Function Signature:**

```python
def get_mcp_settings() -> McpSettings:
    """Get MCP server configuration settings."""
    # Returns settings object with pinecone_api_key, pinecone_index_name, pinecone_namespace
```

### Search Module (`src/search.py`)

Contains the implementation logic for semantic search.

**Function Signature:**

```python
def find_relevant_standards_impl(
    activity: str,
    max_results: int = 5,
    grade: str | None = None,
    subject: str | None = None
) -> str:
    """
    Implementation of semantic search over educational standards.

    Args:
        activity: Description of the learning activity
        max_results: Maximum number of standards to return (default: 5)
        grade: Optional grade level filter (e.g., "K", "01", "05", "09")
        subject: Optional subject filter (e.g., "Mathematics", "ELA-Literacy")

    Returns:
        JSON string with structured response containing matching standards
    """
    # Uses PineconeClient from src.pinecone_client
    # Handles error cases and returns JSON response
```

### Lookup Module (`src/lookup.py`)

Contains the implementation logic for direct ID lookup.

**Function Signature:**

```python
def get_standard_details_impl(standard_id: str) -> str:
    """
    Implementation of direct standard lookup by ID.

    Args:
        standard_id: The standard's GUID (_id field) or identifier

    Returns:
        JSON string with structured response containing standard details
    """
    # Uses PineconeClient from src.pinecone_client
    # Handles error cases and returns JSON response
```

### PineconeClient Extensions (`src/pinecone_client.py`)

Add methods to the `PineconeClient` class (moved from `tools/`):

**New Methods:**

```python
def search_standards(
    self,
    query_text: str,
    top_k: int = 5,
    grade: str | None = None,
    subject: str | None = None
) -> list[dict]:
    """
    Perform semantic search over standards.

    Args:
        query_text: Natural language query
        top_k: Maximum number of results
        grade: Optional grade filter
        subject: Optional subject filter

    Returns:
        List of result dictionaries with metadata and scores
    """

def fetch_standard(self, standard_id: str) -> dict | None:
    """
    Fetch a standard by its GUID.

    Args:
        standard_id: Standard GUID (_id field)

    Returns:
        Standard dictionary with metadata, or None if not found
    """
```

### Pinecone Query Implementation

**Semantic Search Workflow (`src/search.py`):**

1. Import `PineconeClient` from `src.pinecone_client`
2. Initialize client instance (or use singleton pattern)
3. Call `client.search_standards()` with parameters
4. Format results into JSON response structure
5. Handle errors and return appropriate error responses

**Implementation in `PineconeClient.search_standards()` (`src/pinecone_client.py`):**

1. Build Pinecone filter dictionary from optional parameters:
   - If `grade` provided: Add `{"education_levels": {"$in": [grade]}}`
   - If `subject` provided: Add `{"subject": {"$eq": subject}}`
   - Combine filters with `$and` if both provided
2. Build the query dictionary:
   - `"inputs": {"text": query_text}` for text queries (embeddings generated automatically)
   - `"top_k": top_k * 2` to get more candidates for reranking
   - `"filter": filter_dict` only if filters are provided (omit key if no filters)
3. Call `index.search()` with:
   - `namespace=namespace` (from config)
   - `query=query_dict` (the constructed query dictionary)
   - `rerank={"model": "bge-reranker-v2-m3", "top_n": top_k, "rank_fields": ["content"]}` (always enabled)
4. Access results via `results['result']['hits']`
5. Extract `_id`, `_score`, and `fields` from each hit and return list of result dictionaries

**Response Parsing:**

Access search results via `results['result']['hits']`. Each hit contains:

- `hit['_id']`: Record ID
- `hit['_score']`: Reranked relevance score
- `hit['fields']`: Dictionary of metadata fields (e.g., `hit['fields']['content']`, `hit['fields']['subject']`)

Example parsing:

```python
for hit in results['result']['hits']:
    record = {
        "_id": hit["_id"],
        "score": hit["_score"],
        **hit["fields"]  # Spread all metadata fields
    }
```

**Direct ID Lookup Workflow (`src/lookup.py`):**

1. Import `PineconeClient` from `src.pinecone_client`
2. Initialize client instance (or use singleton pattern)
3. Call `client.fetch_standard()` with standard_id
4. If found, format into JSON response structure
5. If not found, return error response with `error_type: "not_found"`

**Implementation in `PineconeClient.fetch_standard()` (`src/pinecone_client.py`):**

1. Call `index.fetch()` with:
   - `ids=[standard_id]`
   - `namespace=namespace` (from config)
2. Extract result from returned dictionary
3. Return standard dictionary with metadata, or None if not found

### Error Handling Implementation

Error handling is implemented in the `src/` modules (`src/search.py` and `src/lookup.py`):

**In `src/search.py` (`find_relevant_standards_impl`):**

1. Validate input parameters (e.g., empty strings, None values)
2. Wrap `PineconeClient.search_standards()` call in try/except
3. Catch `PineconeException` and map to appropriate `error_type`
4. Handle empty results case
5. Return structured JSON error responses
6. Never raise exceptions - always return JSON response

**In `src/lookup.py` (`get_standard_details_impl`):**

1. Validate input parameters (e.g., empty strings, None values)
2. Wrap `PineconeClient.fetch_standard()` call in try/except
3. Catch `PineconeException` and map to appropriate `error_type`
4. Handle None result (not found)
5. Return structured JSON error responses
6. Never raise exceptions - always return JSON response

**Error Mapping:**

- `PineconeException` → `error_type: "api_error"`
- Empty `activity` or `standard_id` → `error_type: "invalid_input"`
- No results from query → `error_type: "no_results"`
- ID not found in fetch (returns None) → `error_type: "not_found"`

---

## Dependencies

The `mcp` package is already included in `pyproject.toml`. Ensure `pinecone` is also available (already included). No additional dependencies are required for this sprint.

---

## Running the Server

### Local Development

1. Ensure environment variables are set in `.env`:

   ```
   PINECONE_API_KEY=your_api_key_here
   PINECONE_INDEX_NAME=common-core-standards
   PINECONE_NAMESPACE=standards
   ```

2. Run the server:

   ```bash
   uv run server.py
   ```

   Or:

   ```bash
   python server.py
   ```

3. The server communicates via stdio. FastMCP handles the MCP protocol transport automatically.

### Claude Desktop Integration

To connect Claude Desktop to the local MCP server, add configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "common-core": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/absolute/path/to/common_core_mcp"
    }
  }
}
```

**Important:** Replace `/absolute/path/to/common_core_mcp` with the actual absolute path to your project directory.

---

## Testing

Skip tests for this sprint. Focus on getting the server working first. Tests can be added in a future sprint.

### Manual Validation

To validate the server works:

1. Run `server.py` and verify it starts without errors
2. Connect Claude Desktop and verify tools appear
3. Test `find_relevant_standards` with a sample activity
4. Test `get_standard_details` with a known GUID
5. Test error cases (invalid ID, empty query, etc.)

---

## Limitations and Future Work

- **Tools Only**: The MCP server only supports tools for now. Prompts and resources are not included in this sprint.
- **No Reasoning**: The server does not include LLM reasoning/explanations for why standards match activities. This matches the MVP spec's `ask_llama` functionality but is deferred for now.
- **Limited Filters**: Only `grade` and `subject` filters are supported initially. Additional filters (e.g., `is_leaf`, `standard_set_id`, `jurisdiction_id`) can be added in future sprints.
