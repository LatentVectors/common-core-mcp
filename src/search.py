"""Semantic search implementation for educational standards."""

from __future__ import annotations

import json

from pinecone.exceptions import PineconeException

from src.pinecone_client import PineconeClient


def find_relevant_standards_impl(
    activity: str,
    max_results: int = 5,
    grade: str | None = None,
) -> str:
    """
    Implementation of semantic search over educational standards.

    Args:
        activity: Description of the learning activity
        max_results: Maximum number of standards to return (default: 5)
        grade: Optional grade level filter (e.g., "K", "01", "05", "09")

    Returns:
        JSON string with structured response containing matching standards
    """
    # Input validation
    if not activity or not activity.strip():
        return json.dumps(
            {
                "success": False,
                "results": [],
                "message": "Activity description cannot be empty",
                "error_type": "invalid_input",
            }
        )

    try:
        # Initialize client and perform search
        client = PineconeClient()
        results = client.search_standards(
            query_text=activity.strip(),
            top_k=max_results,
            grade=grade,
        )

        # Handle empty results
        if not results:
            return json.dumps(
                {
                    "success": False,
                    "results": [],
                    "message": "No matching standards found",
                    "error_type": "no_results",
                }
            )

        # Format successful results
        response = {
            "success": True,
            "results": results,
            "message": f"Found {len(results)} matching standards",
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

