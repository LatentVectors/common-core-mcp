"""Gradio MCP server for Common Core Standards search and lookup."""

import os
import json
from typing import Any

from dotenv import load_dotenv
import gradio as gr
from huggingface_hub import InferenceClient

# Load environment variables from .env file
load_dotenv()

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
            "description": "Retrieves complete metadata and content for a specific educational standard by its GUID (_id field). Use this when you have the exact GUID from a previous search result. This function ONLY accepts GUIDs, not statement notations or other identifiers. For searching by content or notation, use find_relevant_standards instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "standard_id": {
                        "type": "string",
                        "description": "The standard's GUID (_id field) - must be a valid GUID format (e.g., 'EA60C8D165F6481B90BFF782CE193F93'). This function does NOT accept statement notations or other identifier formats."
                    }
                },
                "required": ["standard_id"]
            }
        }
    }
]

def find_relevant_standards(
    activity: str,
    max_results: int = 5,
    grade: str | None = None,
) -> str:
    """
    Searches for educational standards relevant to a learning activity using semantic search.

    This function performs a vector similarity search over the Common Core Standards database
    to find standards that match the described learning activity. Results are ranked by relevance
    and can be filtered by grade level.

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

    # Ensure max_results is an integer (gr.Number returns float by default)
    max_results = int(max_results)

    return find_relevant_standards_impl(activity, max_results, grade)


def get_standard_details(standard_id: str) -> str:
    """
    Retrieves complete metadata and content for a specific educational standard by its GUID.

    This function performs a direct lookup using the standard's GUID (_id field) only.
    It does NOT accept statement notations, ASN identifiers, or any other identifier formats.
    Use find_relevant_standards to search for standards by content or metadata.

    Args:
        standard_id: The standard's GUID (_id field) - must be a valid GUID format
            (e.g., "EA60C8D165F6481B90BFF782CE193F93"). This is the GUID returned in
            search results from find_relevant_standards.

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


def chat_with_standards(message: str, history: list):
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
        Structured content as a list of content blocks. When tool calls are made, includes:
        - Expandable JSON blocks showing tool call results
        - The final assistant response as text
        When no tool calls are made, returns a simple text response.
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
        "content": "You are a helpful assistant for parents and teachers. Your role is to help them plan educational activities and find educational requirements for activities they might have already done. You have access to tools that can search for standards and retrieve standard details. Use these tools when users ask about standards, learning activities, or educational requirements. Always provide clear, helpful responses based on the tool results."
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

            # Store tool call results for display
            tool_results = []

            # Process each tool call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Execute the function
                if function_name == "find_relevant_standards":
                    print(f"Finding relevant standards for activity: {function_args.get('activity', '')}")
                    result = find_relevant_standards_impl(
                        activity=function_args.get("activity", ""),
                        max_results=function_args.get("max_results", 5),
                        grade=function_args.get("grade"),
                    )
                elif function_name == "get_standard_details":
                    print(f"Getting standard details for standard ID: {function_args.get('standard_id', '')}")
                    result = get_standard_details_impl(
                        standard_id=function_args.get("standard_id", "")
                    )
                else:
                    result = json.dumps({"error": f"Function {function_name} not available"})

                # Parse result JSON for display
                try:
                    result_data = json.loads(result) if isinstance(result, str) else result
                except json.JSONDecodeError:
                    result_data = {"raw_result": result}

                # Store tool call info for display
                tool_results.append({
                    "function": function_name,
                    "arguments": function_args,
                    "result": result_data
                })

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

            # Build structured response with tool call results and final answer
            response_blocks = []
            
            # Add tool call results as expandable JSON blocks using markdown
            for i, tool_result in enumerate(tool_results):
                # Format arguments and result as pretty JSON
                args_json = json.dumps(tool_result["arguments"], indent=2)
                result_json = json.dumps(tool_result["result"], indent=2)
                
                # Create collapsible markdown section
                tool_markdown = f"""<details>
<summary><strong>🔧 Tool Call: {tool_result["function"]}</strong></summary>

**Arguments:**
```json
{args_json}
```

**Result:**
```json
{result_json}
```
</details>
"""
                response_blocks.append({
                    "type": "text",
                    "text": tool_markdown
                })
            
            # Add separator before final response
            response_blocks.append({
                "type": "text",
                "text": "---\n"
            })
            
            # Add final assistant response as text
            response_blocks.append({
                "type": "text",
                "text": final_response.choices[0].message.content
            })

            return response_blocks
        else:
            # No tool calls, return direct response as text
            return response_message.content

    except Exception as e:
        # Error handling
        return f"I apologize, but I encountered an error: {str(e)}. Please try again or rephrase your question."


# Create Gradio interface
demo = gr.TabbedInterface(
    [
        gr.ChatInterface(
            fn=chat_with_standards,  # See complete implementation above
            title="Chat with Standards",
            description="Ask questions about educational standards. The AI will use MCP tools to find relevant information.",
            examples=["What standards apply to teaching fractions in 3rd grade?", "Find standards for reading comprehension"],
            api_visibility="private",  # Hide from MCP server - only expose search and lookup tools
        ),
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
    ],
    ["Chat", "Search", "Lookup"],
)

if __name__ == "__main__":
    demo.launch(mcp_server=True)

