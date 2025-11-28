# Gradio MCP Server Sprint Specification

## Overview

This sprint replaces the existing FastMCP server implementation with a Gradio-based MCP server that can be hosted publicly on Hugging Face Spaces. The Gradio app will expose the Common Core Standards MCP tools and include a chat interface that demonstrates MCP tool calling capabilities. This enables public access to the MCP server and provides a demonstration interface for the hackathon submission.

## Key Changes

- Replace `server.py` (FastMCP) with `app.py` (Gradio MCP server)
- Update dependencies to use Gradio 6.0.0+ with MCP support
- Remove FastMCP dependency from `pyproject.toml`
- Create Hugging Face Space configuration files
- Implement chat interface with MCP tool calling support
- Update README to meet hackathon requirements

## User Stories

1. **As a developer**, I want to access the MCP server via a public Hugging Face Space URL so that I can use it from any MCP client without running it locally.

2. **As a user**, I want to interact with a chat interface that can answer questions about educational standards using the MCP tools, so that I can see how the MCP server works in practice.

3. **As a hackathon judge**, I want to see a working MCP server hosted on Hugging Face Spaces with proper documentation, so that I can evaluate the submission.

## Technical Architecture

### Gradio MCP Server Implementation

Gradio 6 introduces native MCP server support. When `mcp_server=True` is set in `demo.launch()`, Gradio automatically:

1. Converts each API endpoint (function) into an MCP tool
2. Uses function docstrings and type hints to generate tool descriptions and parameter schemas
3. Exposes the MCP server at `http://your-server:port/gradio_api/mcp/`
4. Provides an SSE (Server-Sent Events) endpoint for MCP clients

### Function to MCP Tool Conversion

Gradio automatically converts functions with proper docstrings and type hints into MCP tools:

- **Function name** → Tool name
- **Docstring** → Tool description
- **Type hints** → Parameter schema
- **Default values** → Default parameter values (from component initial values)

### MCP Server Endpoints

When `mcp_server=True` is enabled:

- **MCP Schema**: `http://your-server:port/gradio_api/mcp/schema`
- **MCP SSE Endpoint**: `http://your-server:port/gradio_api/mcp/` (for MCP clients)
- **MCP Documentation**: Available via "View API" link in Gradio app footer

### MCP Server Activation

**We will use the `demo.launch(mcp_server=True)` parameter approach** (not the environment variable method). This provides explicit control and makes the MCP server activation clear in the code.

## Implementation Details

### Dependencies Update

**File: `pyproject.toml`**

**Explicit Requirement**: Update Gradio dependency to version 6.0.0 or higher **with MCP extras**:

```toml
dependencies = [
    "gradio[mcp]>=6.0.0",
    "pinecone",
    "python-dotenv",
    "typer",
    "requests",
    "rich",
    "loguru",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "huggingface_hub",
]
```

**Important Notes:**

- The `[mcp]` extra ensures all MCP dependencies are installed
- Remove the standalone `mcp` package dependency if present (FastMCP is no longer used)
- Add `huggingface_hub` for Inference API access in the chat interface

### Gradio App Structure

**File: `app.py`** (new file, replaces `server.py`)

The Gradio app should:

1. **Expose MCP Tools**: Create functions that wrap the existing `src/search.py` and `src/lookup.py` implementations
2. **Enable MCP Server**: Set `mcp_server=True` in `demo.launch()`
3. **Include Chat Interface**: Use `gr.ChatInterface` with a function that supports MCP tool calling

**Function Requirements for MCP Tools:**

- Functions must have detailed docstrings in the format:

  ```python
  def function_name(param1: type, param2: type) -> return_type:
      """
      Description of what the function does.

      Args:
          param1: Description of param1
          param2: Description of param2

      Returns:
          Description of return value
      """
  ```

- Type hints are required for all parameters
- Default values can be set via component initial values (e.g., `gr.Textbox("default value")`)

**Example Structure:**

```python
import gradio as gr
from src.search import find_relevant_standards_impl
from src.lookup import get_standard_details_impl

def find_relevant_standards(
    activity: str,
    max_results: int = 5,
    grade: str | None = None,
    subject: str | None = None,
) -> str:
    """
    Searches for educational standards relevant to a learning activity using semantic search.

    This function performs a vector similarity search over the Common Core Standards database
    to find standards that match the described learning activity. Results are ranked by relevance
    and can be filtered by grade level and subject area.

    Args:
        activity: A natural language description of the learning activity, lesson, or educational
            objective. Examples: "teaching fractions to third graders", "reading comprehension
            activities", "solving quadratic equations". This is the primary search query and should
            be descriptive and specific for best results.

        max_results: The maximum number of standards to return. Must be between 1 and 20.
            Default is 5. Higher values return more results but may include less relevant matches.

        grade: Optional grade level filter. Must be one of the following valid grade level codes:
            - "K" for Kindergarten
            - "01" for Grade 1
            - "02" for Grade 2
            - "03" for Grade 3
            - "04" for Grade 4
            - "05" for Grade 5
            - "06" for Grade 6
            - "07" for Grade 7
            - "08" for Grade 8
            - "09" for Grade 9
            - "10" for Grade 10
            - "11" for Grade 11
            - "12" for Grade 12
            - "09-12" for high school range (when standards span multiple high school grades)

            If None or empty string, no grade filtering is applied and standards from all grade
            levels may be returned. The grade filter uses exact matching against the education_levels
            metadata field in the database.

        subject: Optional subject area filter. Common values include:
            - "Mathematics" or "Math"
            - "ELA-Literacy" or "English Language Arts"
            - "Science"
            - "Social Studies"
            - Other subject names as they appear in the standards database

            If None or empty string, no subject filtering is applied. The subject filter uses
            case-insensitive matching against the subject metadata field.

    Returns:
        A JSON string containing a structured response with the following format:
        {
            "success": true|false,
            "results": [
                {
                    "_id": "standard_guid",
                    "content": "full standard text with hierarchy",
                    "subject": "Mathematics",
                    "education_levels": ["03"],
                    "statement_notation": "3.NF.A.1",
                    "standard_set_title": "Grade 3",
                    "score": 0.85
                },
                ...
            ],
            "message": "Found N matching standards" or error message,
            "error_type": null or error type if success is false
        }

        On success, the results array contains up to max_results standards, sorted by relevance
        score (highest first). Each result includes the full standard content, metadata, and
        relevance score. On error, success is false and an error message describes the issue.
    """
    # Handle empty string from dropdown (convert to None)
    if grade == "":
        grade = None
    if subject == "":
        subject = None

    # Ensure max_results is an integer (gr.Number returns float by default)
    max_results = int(max_results)

    return find_relevant_standards_impl(activity, max_results, grade, subject)

def get_standard_details(standard_id: str) -> str:
    """
    Retrieves complete metadata and content for a specific educational standard by its identifier.

    This function performs a direct lookup of a standard using its unique identifier. The identifier
    can be either the standard's GUID (a unique UUID-like string) or its statement notation
    (the human-readable code like "3.NF.A.1" or "CCSS.Math.Content.3.NF.A.1").

    Args:
        standard_id: The unique identifier for the standard. This can be:
            - A GUID (e.g., "EA60C8D165F6481B90BFF782CE193F93"): The internal database ID
            - A statement notation (e.g., "3.NF.A.1"): The standard's notation code
            - An ASN identifier (e.g., "S21238682"): If available in the standard's metadata

            The function will attempt to match the identifier against multiple fields in the database.
            GUIDs provide the fastest and most reliable lookup. Statement notations may match
            multiple standards if the notation format is ambiguous.

    Returns:
        A JSON string containing a structured response with the following format:
        {
            "success": true|false,
            "results": [
                {
                    "_id": "standard_guid",
                    "content": "full standard text with hierarchy",
                    "subject": "Mathematics",
                    "education_levels": ["03"],
                    "statement_notation": "3.NF.A.1",
                    "standard_set_title": "Grade 3",
                    "asn_identifier": "S21238682",
                    "depth": 3,
                    "is_leaf": true,
                    "parent_id": "parent_guid",
                    "ancestor_ids": [...],
                    "child_ids": [...],
                    ... (all available metadata fields)
                }
            ],
            "message": "Retrieved standard details" or error message,
            "error_type": null or error type if success is false
        }

        On success, the results array contains exactly one standard object with all available
        metadata fields including hierarchy relationships, content, and identifiers. On error
        (e.g., standard not found), success is false and the message provides guidance, such as
        suggesting to use find_relevant_standards for searching.

    Raises:
        This function does not raise exceptions. All errors are returned as JSON responses
        with success=false and appropriate error messages.
    """
    return get_standard_details_impl(standard_id)

# Chat interface function - see complete implementation in Chat Interface Implementation section below

# Create Gradio interface
demo = gr.TabbedInterface(
    [
        gr.Interface(
            fn=find_relevant_standards,
            inputs=[
                gr.Textbox(label="Activity Description", placeholder="Describe a learning activity..."),
                gr.Number(label="Max Results", value=5, minimum=1, maximum=20),
                gr.Dropdown(
                    label="Grade (optional)",
                    choices=["", "K", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "09-12"],
                    value=None,
                    info="Select a grade level to filter results"
                ),
                gr.Textbox(label="Subject (optional)", placeholder="e.g., Mathematics, ELA-Literacy"),
            ],
            outputs=gr.JSON(label="Results"),
            title="Find Relevant Standards",
            description="Search for educational standards relevant to a learning activity.",
            api_name="find_relevant_standards",
        ),
        gr.Interface(
            fn=get_standard_details,
            inputs=gr.Textbox(label="Standard ID", placeholder="Enter a standard GUID or identifier..."),
            outputs=gr.JSON(label="Standard Details"),
            title="Get Standard Details",
            description="Retrieve full metadata for a specific standard by its ID.",
            api_name="get_standard_details",
        ),
        gr.ChatInterface(
            fn=chat_with_standards,  # See complete implementation in Chat Interface Implementation section
            type="messages",  # Required in Gradio 6 - uses OpenAI-style message format
            title="Chat with Standards",
            description="Ask questions about educational standards. The AI will use MCP tools to find relevant information.",
            examples=["What standards apply to teaching fractions in 3rd grade?", "Find standards for reading comprehension"],
        ),
    ],
    ["Search", "Lookup", "Chat"],
)

if __name__ == "__main__":
    demo.launch(mcp_server=True)
```

### Chat Interface Implementation

**Priority: First Priority** - The chat interface is a required deliverable for this sprint.

**Minimum Viable Implementation:**

- Use Hugging Face Inference API with a free/open model that supports MCP tool calling
- Model should be able to call the MCP tools (`find_relevant_standards` and `get_standard_details`)
- Chat function should integrate with the MCP server to answer questions about educational requirements

**Model Selection (Researched and Verified):**

**Selected Model: `Qwen/Qwen2.5-7B-Instruct`**

This model has been verified to:

- Support tool/function calling via Hugging Face Inference API
- Be available through Inference Providers (Together AI, Featherless AI)
- Have good performance for chat applications
- Support the OpenAI-compatible function calling format used by InferenceClient
- Be actively maintained and widely used (57.9M+ downloads as of research date)

**Important:** The model requires specifying an inference provider (e.g., `provider="together"` or `provider="nebius"`) when using InferenceClient.

**Alternative (for more complex queries):** `Qwen/Qwen2.5-72B-Instruct` (larger, more capable, available via Nebius provider)

**Implementation Details:**

The chat function will use Hugging Face's `InferenceClient` with function calling. Since the MCP tools (`find_relevant_standards` and `get_standard_details`) are exposed by the same Gradio app, we can call them directly as Python functions rather than making HTTP requests to the MCP server endpoint. This is more efficient and simpler.

**Complete Chat Function Implementation:**

```python
import os
import json
from typing import Any
from huggingface_hub import InferenceClient
from src.search import find_relevant_standards_impl
from src.lookup import get_standard_details_impl

# Initialize the Hugging Face Inference Client
# Use HF_TOKEN from environment (automatically available in Hugging Face Spaces)
# Provider is required for models that need Inference Providers (e.g., Together AI, Nebius)
HF_TOKEN = os.environ.get("HF_TOKEN")
client = InferenceClient(
    provider="together",  # Required: specifies the inference provider for tool calling
    token=HF_TOKEN
)

# Define the function schemas in OpenAI format for the model
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_relevant_standards",
            "description": "Searches for educational standards relevant to a learning activity using semantic search. Use this when the user asks about standards for a specific activity, lesson, or educational objective.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity": {
                        "type": "string",
                        "description": "A natural language description of the learning activity, lesson, or educational objective. Be specific and descriptive."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of standards to return (1-20). Default is 5.",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    },
                    "grade": {
                        "type": "string",
                        "description": "Optional grade level filter. Valid values: K, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, or 09-12 for high school range.",
                        "enum": ["K", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "09-12"]
                    },
                    "subject": {
                        "type": "string",
                        "description": "Optional subject area filter (e.g., 'Mathematics', 'ELA-Literacy', 'Science')."
                    }
                },
                "required": ["activity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_standard_details",
            "description": "Retrieves complete metadata and content for a specific educational standard by its identifier (GUID or statement notation). Use this when the user asks about a specific standard or wants details about a standard mentioned in previous results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "standard_id": {
                        "type": "string",
                        "description": "The unique identifier for the standard. Can be a GUID (UUID-like string) or statement notation (e.g., '3.NF.A.1')."
                    }
                },
                "required": ["standard_id"]
            }
        }
    }
]

# Function registry for executing tool calls
AVAILABLE_FUNCTIONS = {
    "find_relevant_standards": find_relevant_standards_impl,
    "get_standard_details": get_standard_details_impl,
}

def chat_with_standards(message: str, history: list) -> str:
    """
    Chat function that uses MCP tools via Hugging Face Inference API with tool calling.

    This function integrates with Qwen2.5-7B-Instruct to answer questions about educational
    standards. The model can call find_relevant_standards and get_standard_details tools
    to retrieve information and provide accurate responses.

    Args:
        message: The user's current message/query
        history: Chat history in Gradio 6 messages format. Each message is a dict with
            "role" and "content" keys. In Gradio 6, content uses structured format:
            [{"type": "text", "text": "..."}, ...] for text content.

    Returns:
        The assistant's response as a string, incorporating information from MCP tools
        when relevant.
    """
    # Convert Gradio 6 history format to OpenAI messages format
    # Gradio 6 uses structured content: {"role": "user", "content": [{"type": "text", "text": "..."}]}
    messages = []
    if history:
        for msg in history:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")

                # Handle Gradio 6 structured content format
                if isinstance(content, list):
                    # Extract text from content blocks
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    content = " ".join(text_parts)

                messages.append({
                    "role": role,
                    "content": content
                })

    # Add system message to guide the model
    system_message = {
        "role": "system",
        "content": "You are a helpful assistant that answers questions about educational standards. You have access to tools that can search for standards and retrieve standard details. Use these tools when users ask about standards, learning activities, or educational requirements. Always provide clear, helpful responses based on the tool results."
    }

    # Add current user message
    messages.append({"role": "user", "content": message})

    # Prepare full message list with system message
    full_messages = [system_message] + messages

    try:
        # Initial API call with tools
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=full_messages,
            tools=TOOLS,
            tool_choice="auto",  # Let the model decide when to call functions
            temperature=0.7,
            max_tokens=1000,
        )

        response_message = response.choices[0].message

        # Check if model wants to call functions
        if response_message.tool_calls:
            # Add assistant's tool call request to messages
            full_messages.append(response_message)

            # Process each tool call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Execute the function
                if function_name in AVAILABLE_FUNCTIONS:
                    if function_name == "find_relevant_standards":
                        result = AVAILABLE_FUNCTIONS[function_name](
                            activity=function_args.get("activity", ""),
                            max_results=function_args.get("max_results", 5),
                            grade=function_args.get("grade"),
                            subject=function_args.get("subject")
                        )
                    elif function_name == "get_standard_details":
                        result = AVAILABLE_FUNCTIONS[function_name](
                            standard_id=function_args.get("standard_id", "")
                        )
                    else:
                        result = json.dumps({"error": f"Unknown function: {function_name}"})
                else:
                    result = json.dumps({"error": f"Function {function_name} not available"})

                # Add function result to messages
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": result,
                })

            # Get final response with function results
            final_response = client.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct",
                messages=full_messages,
                temperature=0.7,
                max_tokens=1000,
            )

            return final_response.choices[0].message.content
        else:
            # No tool calls, return direct response
            return response_message.content

    except Exception as e:
        # Error handling
        return f"I apologize, but I encountered an error: {str(e)}. Please try again or rephrase your question."
```

**Key Implementation Points:**

1. **Direct Function Calls**: Since the MCP tools are in the same Python process, we call the underlying implementation functions (`find_relevant_standards_impl` and `get_standard_details_impl`) directly rather than making HTTP requests to the MCP server endpoint.

2. **Tool Schema Conversion**: The MCP tools are converted to OpenAI function calling format, which is what `InferenceClient` expects. The schemas match the function signatures and docstrings.

3. **Tool Calling Workflow**:

   - First API call includes tools and lets model decide if/when to call them
   - If model requests tool calls, execute them and add results to conversation
   - Second API call generates final response incorporating tool results

4. **Error Handling**: All errors are caught and returned as user-friendly messages.

5. **Model Configuration**: Uses `Qwen/Qwen2.5-7B-Instruct` via Together AI provider with `tool_choice="auto"` to let the model decide when to use tools.

6. **Gradio 6 History Format**: The chat function handles Gradio 6's structured content format where content is a list of typed blocks (e.g., `[{"type": "text", "text": "..."}]`) rather than simple strings.

### Hugging Face Space Configuration

**CRITICAL: Space must be created in the MCP-1st-Birthday organization**

**Required Files:**

1. **`app.py`**: Main Gradio application entry point (as described above)

2. **`requirements.txt`**: Python dependencies

   - Extract from `pyproject.toml` or manually specify
   - Must include: `gradio[mcp]>=6.0.0`, `pinecone`, `python-dotenv`, `pydantic>=2.0.0`, `pydantic-settings>=2.0.0`, `huggingface_hub`
   - The `[mcp]` extra ensures all MCP dependencies are included
   - `huggingface_hub` is required for Inference API access in the chat interface

3. **`README.md`**: Updated with hackathon requirements (see README Requirements section below)

4. **`.env.example`**: Template for environment variables

   ```
   PINECONE_API_KEY=your_api_key_here
   PINECONE_INDEX_NAME=common-core-standards
   PINECONE_NAMESPACE=standards
   HF_TOKEN=your_huggingface_token_here
   # Note: MCP_SERVER_URL is not needed since we call functions directly
   ```

5. **Space Configuration** (via Hugging Face UI):
   - **Organization**: Must be `MCP-1st-Birthday` (create Space in this organization)
   - SDK: `gradio`
   - Python version: 3.12+
   - Environment variables: Set `PINECONE_API_KEY`, `HF_TOKEN`, and other required variables in Space settings
   - **Visibility**: Can be public or private (both work for MCP servers)

### Hackathon Registration and Submission Requirements

**Before Building:**

1. **Join the Organization** (REQUIRED):

   - Go to https://huggingface.co/MCP-1st-Birthday
   - Click "Request to join this org" (top right)
   - Wait for approval (usually automatic or quick)

2. **Complete Registration** (REQUIRED):

   - Complete the official registration form (linked on the hackathon page)
   - Registration link: Available on the hackathon page

3. **Team Members** (if applicable):
   - If working in a team (2-5 people), **all** members must:
     - Join the MCP-1st-Birthday organization individually
     - Complete the registration form individually
     - Be listed in the README with their Hugging Face usernames

**Submission Requirements (All Must Be Completed by November 30, 2025, 11:59 PM UTC):**

1. **Hugging Face Space** (REQUIRED):

   - Space must be in the `MCP-1st-Birthday` organization
   - Space must be functional and accessible
   - Code must be pushed to the Space repository

2. **README.md** (REQUIRED):

   - Must include track tag: `building-mcp-track-consumer`
   - Must include team member usernames (if team)
   - Must include demo video link
   - Must include social media post link
   - Must include clear documentation (see README Requirements section)

3. **Demo Video** (REQUIRED):

   - **Length:** 1-5 minutes
   - **Content:** Must show the MCP server in action, specifically demonstrating:
     - Integration with an MCP client (Claude Desktop, Cursor, or similar)
     - The MCP tools being used through the client
     - The Gradio web interface
     - The chat interface using MCP tools
   - **Hosting:** YouTube, Vimeo, or similar platform
   - **Link:** Must be included in the README

4. **Social Media Post** (REQUIRED):

   - Post about your project on X/Twitter, LinkedIn, or similar
   - Include information about the project and hackathon
   - **Link:** Must be included in the README (not just submission form)

5. **Functionality Requirements**:
   - Working MCP server (exposed via Gradio)
   - Integration with MCP client (demonstrated in video)
   - Published as Hugging Face Space

**Judging Criteria (To Guide Implementation):**

Projects will be evaluated on:

1. **Completeness**: Space, video, documentation, and social link all present
2. **Functionality**: Works effectively, uses Gradio 6 and MCP features
3. **Real-world Impact**: Useful tool with potential for real-world application
4. **Creativity**: Innovative or original idea and implementation
5. **Design/UI-UX**: Polished, intuitive, and easy to use
6. **Documentation**: Well-communicated in README and/or demo video

**Additional Considerations for Judging:**

- **Community Choice Award**: Based on social media engagement, Space interactions (Discussions tab), and Discord community engagement
- **Gradio 6 Features**: Use of Gradio 6 capabilities (MCP server, ChatInterface, etc.)
- **MCP Integration**: Effective use of MCP protocol and tool exposure

### README Requirements

**File: `README.md`**

The README is a critical component of the hackathon submission and must include all required elements. Follow this structure:

#### 1. **Hackathon Track Tag (REQUIRED)**

**Must be included in the README metadata or prominently at the top:**

Add the track tag `building-mcp-track-consumer` to classify this as a Consumer MCP Server entry. This tag is **mandatory** for submission eligibility.

**Placement options:**

- In the README frontmatter (if using YAML frontmatter)
- As a tag/badge at the top of the README
- In a "Hackathon" or "Submission" section

**Example:**

```markdown
---
tags:
  - building-mcp-track-consumer
  - mcp
  - gradio
  - education
---
```

Or as a badge:

```markdown
![Hackathon Track](https://img.shields.io/badge/Track-Consumer%20MCP%20Server-blue)
```

#### 2. **Project Title and Description**

Clear, compelling explanation of:

- What the MCP server does
- Its purpose and capabilities
- Why it's useful for consumers (teachers, students, parents, etc.)
- Key features and benefits

#### 3. **Team Information (If Applicable)**

**If working in a team (2-5 members):**

- Include Hugging Face usernames of **all** team members
- Format: "Built by @username1, @username2, @username3"
- All team members must be members of the MCP-1st-Birthday organization

**If working solo:**

- Optional: Include your Hugging Face username
- Format: "Built by @username"

#### 4. **Usage Instructions**

**A. Gradio Web Interface:**

- How to use the web interface
- What each tab/component does
- Example queries or use cases

**B. MCP Client Integration (REQUIRED for demo video):**

- How to connect an MCP client (Claude Desktop, Cursor, etc.) to the Space
- MCP server URL: `https://your-space-name.hf.space/gradio_api/mcp/`
- Step-by-step configuration instructions
- Example MCP client configuration:
  ```json
  {
    "mcpServers": {
      "common-core": {
        "url": "https://your-space-name.hf.space/gradio_api/mcp/"
      }
    }
  }
  ```
- Screenshots of the MCP client showing the tools available

#### 5. **Setup Instructions**

- Local development setup (if applicable)
- Environment variables needed
- Installation steps
- How to run locally

#### 6. **Visual Documentation**

- **Screenshots or GIFs** of the interface in action
- Show the Gradio web interface
- Show MCP client integration (if possible)
- Demonstrate key features

#### 7. **Demo Video Link (REQUIRED)**

**Must include a link to a demo video that:**

- **Length:** 1-5 minutes
- **Content Requirements:**
  - Shows the MCP server **in action**
  - **Specifically demonstrates integration with an MCP client** (Claude Desktop, Cursor, or similar)
  - Shows the MCP tools being used through the client
  - Demonstrates the Gradio web interface
  - Shows the chat interface using MCP tools
- **Platform:** YouTube, Vimeo, or other video hosting service
- **Format:** Include the video link prominently in the README

**Example section:**

```markdown
## 🎥 Demo Video

Watch the demo video showing the MCP server in action:

[![Demo Video](video-thumbnail-url)](video-url)

The video demonstrates:

- MCP server integration with Claude Desktop
- Using the Gradio web interface
- Chat interface with tool calling
```

#### 8. **Social Media Post Link (REQUIRED)**

**Must include a link to a social media post about the project:**

- Platform: X/Twitter, LinkedIn, or similar
- Content: Post about your project, the hackathon, and what you built
- **This link must be included in the README** (not just in submission form)
- Format: "Share on [Twitter](link) | [LinkedIn](link)"

**Example section:**

```markdown
## 📱 Social Media

Check out our project announcement:

- [Twitter/X Post](your-twitter-post-url)
- [LinkedIn Post](your-linkedin-post-url)
```

#### 9. **Technical Details**

- Architecture overview
- Technologies used (Gradio 6, MCP, etc.)
- How the MCP tools work
- API documentation (if applicable)

#### 10. **Acknowledgments**

- Hackathon organizers
- Libraries and tools used
- Any inspiration or references

**README Checklist for Hackathon Submission:**

- [ ] Track tag `building-mcp-track-consumer` included
- [ ] Team member usernames listed (if team)
- [ ] Clear project description
- [ ] Usage instructions for web interface
- [ ] MCP client integration instructions
- [ ] Screenshots/GIFs included
- [ ] Demo video link included (1-5 minutes, shows MCP client integration)
- [ ] Social media post link included
- [ ] Setup/installation instructions
- [ ] Technical details documented

### File Changes Summary

**Files to Create:**

- `app.py`: Main Gradio application with MCP server and chat interface
- `requirements.txt`: Python dependencies for Hugging Face Space
- `.env.example`: Environment variable template
- `README.md`: Updated with hackathon requirements (or update existing)

**Files to Delete:**

- `server.py`: Replaced by `app.py`

**Files to Modify:**

- `pyproject.toml`: Update Gradio to `gradio[mcp]>=6.0.0`, add `huggingface_hub`, remove standalone `mcp` dependency if present

**Files to Reference (Existing):**

- `src/search.py`: Contains `find_relevant_standards_impl()` function
- `src/lookup.py`: Contains `get_standard_details_impl()` function
- `src/pinecone_client.py`: Pinecone client implementation
- `src/mcp_config.py`: Configuration settings

## Technical Specifications (Verified from Documentation)

### Gradio MCP Server Syntax

**Enabling MCP Server:**

```python
demo.launch(mcp_server=True)
```

Or via environment variable:

```bash
export GRADIO_MCP_SERVER=True
```

**MCP Server Endpoints:**

- Schema: `{base_url}/gradio_api/mcp/schema`
- SSE Endpoint: `{base_url}/gradio_api/mcp/` (for MCP clients)

### Function Signature Requirements

Functions exposed as MCP tools must:

1. Have type hints for all parameters
2. Have detailed docstrings with Args and Returns sections
3. Return a value (not None, unless explicitly typed as `str | None`)

**Example:**

```python
def find_relevant_standards(
    activity: str,
    max_results: int = 5,
    grade: str | None = None,
    subject: str | None = None,
) -> str:
    """
    Returns educational standards relevant to the activity.

    Args:
        activity: Natural language description of the learning activity
        max_results: Maximum number of standards to return (default: 5)
        grade: Optional grade level filter (e.g., "K", "01", "05", "09")
        subject: Optional subject filter (e.g., "Mathematics", "ELA-Literacy")

    Returns:
        JSON string with structured response containing matching standards
    """
    # Implementation
```

### Repository Structure for Hugging Face Spaces

**Required Files:**

- `app.py` (or `main.py`): Entry point for the Gradio app
- `requirements.txt`: Python dependencies
- `README.md`: Project documentation

**Optional but Recommended:**

- `.env.example`: Environment variable template
- `src/`: Source code directory (already exists)

**Space Configuration:**

- SDK: Set to `gradio` in Hugging Face Space settings
- Python version: 3.12+ (matches project requirement)
- Environment variables: Configure in Space settings UI

### Exposing Functions as MCP Endpoints

**Automatic Conversion:**

- Any function passed to `gr.Interface()` or `gr.ChatInterface()` is automatically exposed as an MCP tool
- Function name becomes the tool name
- Docstring becomes the tool description
- Type hints define the parameter schema

**API Name Customization:**

```python
gr.Interface(
    fn=find_relevant_standards,
    # ... inputs and outputs ...
    api_name="find_relevant_standards",  # Custom API endpoint name
)
```

**API Visibility Control:**

```python
gr.Interface(
    fn=find_relevant_standards,
    # ... inputs and outputs ...
    api_visibility="public",  # "public", "private", or "undocumented"
)
```

**API Description Customization:**

```python
gr.Interface(
    fn=find_relevant_standards,
    # ... inputs and outputs ...
    api_description="Custom description for MCP tool",  # Overrides docstring
)
```

## Chat Interface MCP Integration

The chat interface must:

1. Use a Hugging Face model that supports tool calling (e.g., `Qwen/Qwen2.5-7B-Instruct`)
2. Specify an inference provider (e.g., `provider="together"`) for the model
3. Handle Gradio 6's structured content format for chat history
4. Handle tool calling: detect tool requests, execute functions directly, return results to model

**Implementation Notes:**

- The chat interface and MCP tools are in the same Gradio app
- We call the underlying Python functions directly rather than making HTTP requests to the MCP server
- The model must be configured to call tools when answering questions about educational standards
- **Gradio 6 History Format**: Content is now structured as `[{"type": "text", "text": "..."}]` rather than simple strings. The chat function must extract text from these content blocks.

## Testing and Validation

### Local Testing

1. Run `app.py` locally:

   ```bash
   python app.py
   ```

2. Verify MCP server is running:

   - Check console output for MCP server URL
   - Visit `http://localhost:7860/gradio_api/mcp/schema` to view tools

3. Test MCP client connection:

   - Configure Claude Desktop or Cursor to use `http://localhost:7860/gradio_api/mcp/`
   - Verify tools appear in the client

4. Test chat interface:
   - Interact with the chat interface in the Gradio UI
   - Verify it can call MCP tools and return educational standards information

### Hugging Face Space Deployment

1. Push code to Hugging Face Space
2. Verify Space builds and runs successfully
3. Check MCP server endpoint: `https://your-space-name.hf.space/gradio_api/mcp/schema`
4. Test MCP client connection using the Space URL
5. Test chat interface in the Space UI

## Risks and Assumptions

### Risks

1. **Chat Interface Complexity**: Implementing MCP tool calling with Hugging Face Inference API may be complex and require additional research or libraries.

2. **Model/Provider Availability**: The selected model (`Qwen/Qwen2.5-7B-Instruct`) requires an inference provider (Together AI or Featherless AI). Provider availability and rate limits may affect performance.

3. **MCP Client Configuration**: Users may need guidance on configuring MCP clients to connect to the Space.

4. **Gradio 6 Breaking Changes**: Gradio 6 introduces several breaking changes including structured content format for ChatInterface history. Implementation must handle these changes correctly.

### Assumptions

1. Gradio 6.0.0+ includes all necessary MCP server functionality without additional packages (with `gradio[mcp]` extras).

2. The existing `src/search.py` and `src/lookup.py` implementations can be directly called from Gradio functions without modification.

3. Hugging Face Spaces automatically sets `GRADIO_MCP_SERVER=True` when Gradio 6+ is detected.

4. The MCP server URL format for Hugging Face Spaces is `https://space-name.hf.space/gradio_api/mcp/`.

5. The `Qwen/Qwen2.5-7B-Instruct` model is available via Together AI or Featherless AI inference providers and supports tool calling.

6. Gradio 6 ChatInterface passes history in structured content format that must be parsed to extract text content.

## Dependencies

- **Gradio 6.0.0+**: Required for MCP server support (install with `gradio[mcp]` extras)
- **Hugging Face Hub/Inference API**: For chat interface model access
  - Requires `provider="together"` or similar for models that need inference providers
  - `Qwen/Qwen2.5-7B-Instruct` is available via Together AI and Featherless AI providers
- **Existing dependencies**: Pinecone, pydantic, etc. (unchanged)

## Deliverables

1. ✅ `app.py`: Gradio application with MCP server and chat interface
2. ✅ `requirements.txt`: Dependencies for Hugging Face Space
3. ✅ Updated `README.md`: Hackathon-compliant documentation with all required elements
4. ✅ `.env.example`: Environment variable template
5. ✅ Updated `pyproject.toml`: Gradio 6.0.0+ dependency with MCP extras
6. ✅ Deleted `server.py`: Old FastMCP implementation removed
7. ✅ Working Hugging Face Space: Deployed in MCP-1st-Birthday organization
8. ✅ Chat interface: Functional with MCP tool calling
9. ✅ Demo video: 1-5 minutes showing MCP client integration
10. ✅ Social media post: Link included in README

## Hackathon Submission Checklist

**Before Submission Deadline (November 30, 2025, 11:59 PM UTC):**

### Registration (Complete Before Building)

- [ ] Joined MCP-1st-Birthday organization on Hugging Face
- [ ] Completed official registration form
- [ ] All team members joined organization and registered (if team)

### Technical Implementation

- [ ] `app.py` created with Gradio MCP server
- [ ] `requirements.txt` includes all dependencies
- [ ] Space deployed and functional in MCP-1st-Birthday organization
- [ ] MCP server accessible at `/gradio_api/mcp/` endpoint
- [ ] Chat interface working with tool calling
- [ ] All MCP tools (`find_relevant_standards`, `get_standard_details`) functional

### Documentation (README.md)

- [ ] Track tag `building-mcp-track-consumer` included
- [ ] Team member usernames listed (if team)
- [ ] Clear project description and purpose
- [ ] Usage instructions for Gradio web interface
- [ ] MCP client integration instructions with configuration example
- [ ] Setup/installation instructions
- [ ] Screenshots or GIFs included
- [ ] **Demo video link included** (1-5 minutes, shows MCP client integration)
- [ ] **Social media post link included**
- [ ] Technical details documented

### Demo Video Requirements

- [ ] Video length: 1-5 minutes
- [ ] Shows MCP server in action
- [ ] **Demonstrates integration with MCP client** (Claude Desktop, Cursor, etc.)
- [ ] Shows MCP tools being used through the client
- [ ] Shows Gradio web interface
- [ ] Shows chat interface using MCP tools
- [ ] Video hosted on YouTube, Vimeo, or similar
- [ ] Link included in README

### Social Media Post

- [ ] Post created on X/Twitter, LinkedIn, or similar
- [ ] Post mentions the project and hackathon
- [ ] Link included in README (not just submission form)

### Space Configuration

- [ ] Space created in `MCP-1st-Birthday` organization
- [ ] SDK set to `gradio`
- [ ] Python version 3.12+
- [ ] Environment variables configured (PINECONE_API_KEY, HF_TOKEN, etc.)
- [ ] Space is accessible and functional

### Quality Checks

- [ ] Code follows best practices
- [ ] Error handling implemented
- [ ] UI is polished and intuitive
- [ ] Documentation is clear and complete
- [ ] All features work as expected

## Next Steps After Sprint

1. **Create Demo Video**:

   - Record 1-5 minute video showing MCP client integration
   - Demonstrate all key features
   - Upload to YouTube or Vimeo
   - Add link to README

2. **Create Social Media Post**:

   - Post about the project on X/Twitter or LinkedIn
   - Include project highlights and hackathon information
   - Add link to README

3. **Final README Polish**:

   - Ensure all required elements are present
   - Add screenshots/GIFs
   - Verify all links work
   - Check formatting and clarity

4. **Submit to Hackathon**:

   - Verify all checklist items are complete
   - Submit before November 30, 2025, 11:59 PM UTC
   - Engage with community (Discord, Space discussions)

5. **Future Enhancements** (Post-Hackathon):
   - Fine-tune chat interface model selection and configuration
   - Add error handling and user feedback improvements
   - Consider adding more MCP tools or resources
   - Optimize performance and user experience
