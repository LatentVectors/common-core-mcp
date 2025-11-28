"""Direct ID lookup implementation for educational standards."""

from __future__ import annotations

import json

from pinecone.exceptions import PineconeException

from src.pinecone_client import PineconeClient


def get_standard_details_impl(standard_id: str) -> str:
    """
    Implementation of direct standard lookup by GUID only.

    This function only accepts GUIDs (_id field) from Pinecone. It does NOT accept
    statement_notation or other identifier formats. Use find_relevant_standards to
    search for standards by content or metadata.

    Args:
        standard_id: The standard's GUID (_id field) - must be a valid GUID format
            (e.g., "EA60C8D165F6481B90BFF782CE193F93")

    Returns:
        JSON string with structured response containing standard details
    """
    # Input validation
    if not standard_id or not standard_id.strip():
        return json.dumps(
            {
                "success": False,
                "results": [],
                "message": "Standard ID cannot be empty",
                "error_type": "invalid_input",
            }
        )

    try:
        # Initialize client and fetch standard
        client = PineconeClient()
        result = client.fetch_standard(standard_id.strip())

        # Handle not found
        if result is None:
            return json.dumps(
                {
                    "success": False,
                    "results": [],
                    "message": f"Standard with GUID '{standard_id}' not found. This function only accepts GUIDs (e.g., 'EA60C8D165F6481B90BFF782CE193F93'). For statement notations or other identifiers, use find_relevant_standards with a keyword search instead.",
                    "error_type": "not_found",
                }
            )

        # Format successful result
        response = {
            "success": True,
            "results": [result],
            "message": "Retrieved standard details",
        }

        return json.dumps(response, indent=2)

    except PineconeException as e:
        return json.dumps(
            {
                "success": False,
                "results": [],
                "message": f"Pinecone API error: {str(e)}",
                "error_type": "api_error",
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "results": [],
                "message": f"Unexpected error: {str(e)}",
                "error_type": "api_error",
            }
        )

