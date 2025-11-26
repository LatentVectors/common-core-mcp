"""Manages local data storage and metadata tracking."""

from __future__ import annotations

import json
from dataclasses import dataclass

from loguru import logger

from tools.config import get_settings
from tools.models import StandardSetResponse

settings = get_settings()

# Data directories (from config)
RAW_DATA_DIR = settings.raw_data_dir
STANDARD_SETS_DIR = settings.standard_sets_dir
PROCESSED_DATA_DIR = settings.processed_data_dir


@dataclass
class StandardSetInfo:
    """Information about a downloaded standard set with processing status."""

    set_id: str
    title: str
    subject: str
    education_levels: list[str]
    jurisdiction: str
    publication_status: str
    valid_year: str
    processed: bool


def list_downloaded_standard_sets() -> list[StandardSetInfo]:
    """
    List all downloaded standard sets from the standardSets directory.

    Returns:
        List of StandardSetInfo with standard set info and processing status
    """
    if not STANDARD_SETS_DIR.exists():
        return []

    datasets = []
    for set_dir in STANDARD_SETS_DIR.iterdir():
        if not set_dir.is_dir():
            continue

        data_file = set_dir / "data.json"
        if not data_file.exists():
            continue

        try:
            with open(data_file, encoding="utf-8") as f:
                raw_data = json.load(f)

            # Parse the API response wrapper
            response = StandardSetResponse(**raw_data)
            standard_set = response.data

            # Build the dataset info
            dataset_info = StandardSetInfo(
                set_id=standard_set.id,
                title=standard_set.title,
                subject=standard_set.subject,
                education_levels=standard_set.educationLevels,
                jurisdiction=standard_set.jurisdiction.title,
                publication_status=standard_set.document.publicationStatus or "Unknown",
                valid_year=standard_set.document.valid,
                processed=False,  # TODO: Check against processed directory
            )

            datasets.append(dataset_info)

        except (json.JSONDecodeError, IOError, Exception) as e:
            logger.warning(f"Failed to read {data_file}: {e}")
            continue

    logger.debug(f"Found {len(datasets)} downloaded standard sets")
    return datasets
