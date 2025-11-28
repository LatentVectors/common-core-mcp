# Spec Tasks

## Tasks

- [x] 1. Update Dependencies in pyproject.toml

  - [x] 1.1 Update Gradio dependency from `gradio>=5.0.0,<6.0.0` to `gradio[mcp]>=6.0.0` to enable MCP server support
  - [x] 1.2 Add `huggingface_hub` to dependencies list for Inference API access in chat interface
  - [x] 1.3 Remove standalone `mcp` package dependency (FastMCP is no longer used, Gradio 6 includes MCP support)
  - [x] 1.4 Verify all other dependencies remain unchanged (pinecone, python-dotenv, typer, requests, rich, loguru, pydantic>=2.0.0, pydantic-settings>=2.0.0)

- [x] 2. Create app.py with MCP Tool Wrapper Functions

  - [x] 2.1 Create `app.py` in project root with imports: `gradio as gr`, `find_relevant_standards_impl` from `src.search`, `get_standard_details_impl` from `src.lookup`
  - [x] 2.2 Implement `find_relevant_standards()` function with signature: `(activity: str, max_results: int = 5, grade: str | None = None, subject: str | None = None) -> str`
  - [x] 2.3 Add comprehensive docstring to `find_relevant_standards()` following spec format with Args and Returns sections, including all grade level codes and subject examples
  - [x] 2.4 Add input handling: convert empty string `grade` and `subject` to `None`, convert `max_results` float to int (Gradio Number returns float)
  - [x] 2.5 Implement `get_standard_details()` function with signature: `(standard_id: str) -> str`
  - [x] 2.6 Add comprehensive docstring to `get_standard_details()` following spec format with Args, Returns, and Raises sections
  - [x] 2.7 Delegate both functions to their respective `_impl` functions from `src/` modules

- [x] 3. Create Gradio Interface Structure with TabbedInterface

  - [x] 3.1 Create `gr.Interface` for `find_relevant_standards` with inputs: `gr.Textbox` (activity), `gr.Number` (max_results, min=1, max=20, value=5), `gr.Dropdown` (grade with choices including empty string), `gr.Textbox` (subject, optional)
  - [x] 3.2 Configure `find_relevant_standards` interface with `gr.JSON` output, title "Find Relevant Standards", description, and `api_name="find_relevant_standards"`
  - [x] 3.3 Create `gr.Interface` for `get_standard_details` with `gr.Textbox` input (standard_id) and `gr.JSON` output
  - [x] 3.4 Configure `get_standard_details` interface with title "Get Standard Details", description, and `api_name="get_standard_details"`
  - [x] 3.5 Create `gr.ChatInterface` with `fn=chat_with_standards` (placeholder for now), `type="messages"`, title, description, and example prompts
  - [x] 3.6 Combine all three interfaces into `gr.TabbedInterface` with tab labels: ["Search", "Lookup", "Chat"]
  - [x] 3.7 Add `if __name__ == "__main__": demo.launch(mcp_server=True)` to enable MCP server

- [x] 4. Implement Chat Interface with Hugging Face Inference API

  - [x] 4.1 Add imports to `app.py`: `os`, `json`, `InferenceClient` from `huggingface_hub`
  - [x] 4.2 Initialize `InferenceClient` with `provider="together"` and `token=os.environ.get("HF_TOKEN")` at module level
  - [x] 4.3 Define `TOOLS` list with OpenAI function calling format schemas for `find_relevant_standards` and `get_standard_details` matching the function signatures
  - [x] 4.4 Create `AVAILABLE_FUNCTIONS` dict mapping function names to their `_impl` implementations
  - [x] 4.5 Implement `chat_with_standards(message: str, history: list) -> str` function signature
  - [x] 4.6 Add Gradio 6 history format conversion: extract text from structured content blocks `[{"type": "text", "text": "..."}]` format
  - [x] 4.7 Build message list with system message, converted history, and current user message
  - [x] 4.8 Implement tool calling workflow: initial API call with tools, detect tool_calls, execute functions, add results, get final response
  - [x] 4.9 Add error handling with try/except returning user-friendly error messages
  - [x] 4.10 Configure API calls: model `"Qwen/Qwen2.5-7B-Instruct"`, `tool_choice="auto"`, `temperature=0.7`, `max_tokens=1000`

- [x] 5. Create requirements.txt for Hugging Face Space Deployment

  - [x] 5.1 Create `requirements.txt` in project root
  - [x] 5.2 Extract dependencies from `pyproject.toml` or manually specify: `gradio[mcp]>=6.0.0`, `pinecone`, `python-dotenv`, `pydantic>=2.0.0`, `pydantic-settings>=2.0.0`, `huggingface_hub`
  - [x] 5.3 Ensure `[mcp]` extra is included in Gradio dependency specification
  - [x] 5.4 Verify all required dependencies for both MCP server and chat interface are included

- [x] 6. Create .env.example Template File

  - [x] 6.1 Create `.env.example` in project root
  - [x] 6.2 Add `PINECONE_API_KEY=your_api_key_here` with comment explaining Pinecone API key requirement
  - [x] 6.3 Add `PINECONE_INDEX_NAME=common-core-standards` with default value
  - [x] 6.4 Add `PINECONE_NAMESPACE=standards` with default value
  - [x] 6.5 Add `HF_TOKEN=your_huggingface_token_here` with comment explaining Hugging Face token requirement for chat interface
  - [x] 6.6 Add comment noting that `MCP_SERVER_URL` is not needed since functions are called directly

- [x] 7. Create README.md with Code and Documentation Sections

  - [x] 7.1 Create `README.md` in project root with hackathon track tag `building-mcp-track-consumer` in frontmatter or badge format
  - [x] 7.2 Add project title and description explaining the MCP server purpose, capabilities, and target users (teachers, students, parents)
  - [x] 7.3 Add team information section (placeholder for username if solo, or format for team members)
  - [x] 7.4 Add "Usage Instructions" section with subsection A: Gradio Web Interface usage, tab descriptions, and example queries
  - [x] 7.5 Add subsection B: MCP Client Integration instructions with MCP server URL format, step-by-step configuration, example JSON config, and note about screenshots
  - [x] 7.6 Add "Setup Instructions" section with local development setup, environment variables, installation steps, and how to run locally
  - [x] 7.7 Add "Technical Details" section with architecture overview, technologies used (Gradio 6, MCP), how MCP tools work, and API documentation references
  - [x] 7.8 Add "Visual Documentation" section placeholder noting screenshots/GIFs should be added (but do not create actual media files)
  - [x] 7.9 Add "Acknowledgments" section with hackathon organizers, libraries/tools used, and inspiration/references
  - [x] 7.10 Add placeholder sections for "Demo Video" and "Social Media" with note that links will be added separately (exclude from code tasks)

- [x] 8. Delete Old FastMCP server.py File
  - [x] 8.1 Delete `server.py` from project root (replaced by `app.py`)
  - [x] 8.2 Verify no other files reference `server.py` that would break
