# Spec Tasks

## Tasks

- [x] 1. Create MCP Configuration Module

  - [x] 1.1 Create `src/mcp_config.py` with `McpSettings` class using Pydantic BaseSettings
  - [x] 1.2 Add `pinecone_api_key` (required), `pinecone_index_name` (default: "common-core-standards"), and `pinecone_namespace` (default: "standards") fields
  - [x] 1.3 Configure to load from `.env` file with `env_file=".env"` and `env_file_encoding="utf-8"`
  - [x] 1.4 Create `get_mcp_settings()` function that returns a singleton `McpSettings` instance
  - [x] 1.5 Add validation to ensure `pinecone_api_key` is not empty (raise ValueError if missing)

- [x] 2. Move PineconeClient to src/ Directory

  - [x] 2.1 Move `tools/pinecone_client.py` to `src/pinecone_client.py`
  - [x] 2.2 Update imports in `src/pinecone_client.py`: change `from tools.config import get_settings` to use `src.mcp_config.get_mcp_settings()` instead
  - [x] 2.3 Update `PineconeClient.__init__()` to use `get_mcp_settings()` from `src.mcp_config`
  - [x] 2.4 Verify `src/pinecone_client.py` imports `PineconeRecord` from `tools.pinecone_models` (keep this import for now)

- [x] 3. Update Tools Imports to Use src.pinecone_client

  - [x] 3.1 Update `tools/cli.py`: replace `from tools.pinecone_client import PineconeClient` with `from src.pinecone_client import PineconeClient` (2 occurrences)
  - [x] 3.2 Check `tools/pinecone_processor.py` for any `pinecone_client` imports and update if present
  - [x] 3.3 Verify all imports work correctly by checking for any remaining references to `tools.pinecone_client`

- [x] 4. Add search_standards() Method to PineconeClient

  - [x] 4.1 Add `search_standards()` method signature: `def search_standards(self, query_text: str, top_k: int = 5, grade: str | None = None, subject: str | None = None) -> list[dict]`
  - [x] 4.2 Build filter dictionary dynamically: create empty list, add `{"education_levels": {"$in": [grade]}}` if grade provided, add `{"subject": {"$eq": subject}}` if subject provided, combine with `$and` if both exist
  - [x] 4.3 Build query dictionary: `{"inputs": {"text": query_text}, "top_k": top_k * 2}` (double for reranking candidates), add `"filter": filter_dict` only if filter_dict exists
  - [x] 4.4 Call `index.search()` with `namespace=self.namespace`, `query=query_dict`, and `rerank={"model": "bge-reranker-v2-m3", "top_n": top_k, "rank_fields": ["content"]}`
  - [x] 4.5 Parse results: access `results['result']['hits']`, extract `_id`, `_score`, and `fields` from each hit, combine into dict with `{"_id": hit["_id"], "score": hit["_score"], **hit["fields"]}`
  - [x] 4.6 Return list of result dictionaries

- [x] 5. Add fetch_standard() Method to PineconeClient

  - [x] 5.1 Add `fetch_standard()` method signature: `def fetch_standard(self, standard_id: str) -> dict | None`
  - [x] 5.2 Call `index.fetch()` with `ids=[standard_id]` and `namespace=self.namespace`
  - [x] 5.3 Extract result from `result.records` dictionary using `standard_id` as key
  - [x] 5.4 If record found, extract `_id` and all fields from `record.fields`, combine into dict
  - [x] 5.5 Return dictionary with metadata or `None` if not found

- [x] 6. Create search.py Module with Semantic Search Implementation

  - [x] 6.1 Create `src/search.py` with imports: `json`, `PineconeClient` from `src.pinecone_client`, `PineconeException` from `pinecone.exceptions`
  - [x] 6.2 Implement `find_relevant_standards_impl()` function with signature matching spec (activity, max_results=5, grade=None, subject=None) -> str
  - [x] 6.3 Add input validation: check if `activity` is empty or None, return error JSON with `error_type: "invalid_input"` if invalid
  - [x] 6.4 Wrap `PineconeClient.search_standards()` call in try/except, catch `PineconeException` and return error JSON with `error_type: "api_error"`
  - [x] 6.5 Handle empty results: if results list is empty, return error JSON with `error_type: "no_results"` and message "No matching standards found"
  - [x] 6.6 Format successful results: create response dict with `success: True`, `results` list (each with `_id`, `score`, and all metadata fields), and `message` with count
  - [x] 6.7 Return JSON string using `json.dumps()` with proper formatting

- [x] 7. Create lookup.py Module with Direct ID Lookup Implementation

  - [x] 7.1 Create `src/lookup.py` with imports: `json`, `PineconeClient` from `src.pinecone_client`, `PineconeException` from `pinecone.exceptions`
  - [x] 7.2 Implement `get_standard_details_impl()` function with signature: `(standard_id: str) -> str`
  - [x] 7.3 Add input validation: check if `standard_id` is empty or None, return error JSON with `error_type: "invalid_input"` if invalid
  - [x] 7.4 Wrap `PineconeClient.fetch_standard()` call in try/except, catch `PineconeException` and return error JSON with `error_type: "api_error"`
  - [x] 7.5 Handle not found: if `fetch_standard()` returns `None`, return error JSON with `error_type: "not_found"` and helpful message suggesting to use `find_relevant_standards`
  - [x] 7.6 Format successful result: create response dict with `success: True`, `results` list containing single standard dict with all metadata, and `message: "Retrieved standard details"`
  - [x] 7.7 Return JSON string using `json.dumps()` with proper formatting

- [x] 8. Create server.py MCP Entry Point
  - [x] 8.1 Create `server.py` in project root with imports: `FastMCP` from `mcp.server.fastmcp`, `find_relevant_standards_impl` from `src.search`, `get_standard_details_impl` from `src.lookup`
  - [x] 8.2 Initialize FastMCP server: `mcp = FastMCP("CommonCore")`
  - [x] 8.3 Define `find_relevant_standards` tool with `@mcp.tool()` decorator, signature matching spec (activity, max_results=5, grade=None, subject=None) -> str, docstring "Returns educational standards relevant to the activity"
  - [x] 8.4 Define `get_standard_details` tool with `@mcp.tool()` decorator, signature `(standard_id: str) -> str`, docstring "Returns full metadata for a standard by its GUID or identifier"
  - [x] 8.5 Add `if __name__ == "__main__": mcp.run()` block to start server
  - [x] 8.6 Verify server starts without errors by running `uv run server.py`
