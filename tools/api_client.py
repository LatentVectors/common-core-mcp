"""API client for Common Standards Project with retry logic and rate limiting."""

from __future__ import annotations

import json
import time
from typing import Any

import requests
from loguru import logger

from tools.config import get_settings
from tools.models import (
    Jurisdiction,
    JurisdictionDetails,
    StandardSet,
    StandardSetReference,
)

settings = get_settings()

# Cache file for jurisdictions
JURISDICTIONS_CACHE_FILE = settings.raw_data_dir / "jurisdictions.json"

# Rate limiting: Max requests per minute
MAX_REQUESTS_PER_MINUTE = settings.max_requests_per_minute
_request_timestamps: list[float] = []


class APIError(Exception):
    """Raised when API request fails after all retries."""

    pass


def _get_headers() -> dict[str, str]:
    """Get authentication headers for API requests."""
    if not settings.csp_api_key:
        logger.error("CSP_API_KEY not found in .env file")
        raise ValueError("CSP_API_KEY environment variable not set")
    return {"Api-Key": settings.csp_api_key}


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
    endpoint: str, params: dict[str, Any] | None = None, max_retries: int = 3
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
    url = f"{settings.csp_base_url}{endpoint}"
    headers = _get_headers()

    for attempt in range(max_retries):
        try:
            _enforce_rate_limit()

            logger.debug(
                f"API request: {endpoint} (attempt {attempt + 1}/{max_retries})"
            )
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
                logger.warning(
                    f"Server rate limit hit. Waiting {retry_after} seconds..."
                )
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            logger.info(f"API request successful: {endpoint}")
            return response.json()

        except requests.exceptions.Timeout:
            wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
            logger.warning(f"Request timeout. Retrying in {wait_time}s...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                raise APIError(f"Request timeout after {max_retries} attempts")

        except requests.exceptions.ConnectionError:
            wait_time = 2**attempt
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
            wait_time = 2**attempt
            logger.warning(
                f"Server error {response.status_code}. Retrying in {wait_time}s..."
            )
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                raise APIError(f"Server error after {max_retries} attempts")

    raise APIError("Request failed after all retries")


def get_jurisdictions(
    search_term: str | None = None,
    type_filter: str | None = None,
    force_refresh: bool = False,
) -> list[Jurisdiction]:
    """
    Fetch all jurisdictions from the API or local cache.

    Jurisdictions are cached locally in data/raw/jurisdictions.json to avoid
    repeated API calls. Use force_refresh=True to fetch fresh data from the API.

    Args:
        search_term: Optional filter for jurisdiction title (case-insensitive partial match)
        type_filter: Optional filter for jurisdiction type (case-insensitive).
                     Valid values: "school", "organization", "state", "nation"
        force_refresh: If True, fetch fresh data from API and update cache

    Returns:
        List of Jurisdiction models
    """
    jurisdictions: list[Jurisdiction] = []
    raw_data: list[dict[str, Any]] = []

    # Check cache first (unless forcing refresh)
    if not force_refresh and JURISDICTIONS_CACHE_FILE.exists():
        try:
            logger.info("Loading jurisdictions from cache")
            with open(JURISDICTIONS_CACHE_FILE, encoding="utf-8") as f:
                cached_response = json.load(f)
            raw_data = cached_response.get("data", [])
            logger.info(f"Loaded {len(raw_data)} jurisdictions from cache")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache: {e}. Fetching from API...")
            force_refresh = True

    # Fetch from API if cache doesn't exist or force_refresh is True
    if force_refresh or not raw_data:
        logger.info("Fetching jurisdictions from API")
        response = _make_request("/jurisdictions")
        raw_data = response.get("data", [])

        # Save to cache
        try:
            settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
            with open(JURISDICTIONS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(response, f, indent=2, ensure_ascii=False)
            logger.info(
                f"Cached {len(raw_data)} jurisdictions to {JURISDICTIONS_CACHE_FILE}"
            )
        except IOError as e:
            logger.warning(f"Failed to save cache: {e}")

    # Parse into Pydantic models
    jurisdictions = [Jurisdiction(**j) for j in raw_data]

    # Apply type filter if provided (case-insensitive)
    if type_filter:
        type_lower = type_filter.lower()
        original_count = len(jurisdictions)
        jurisdictions = [j for j in jurisdictions if j.type.lower() == type_lower]
        logger.info(
            f"Filtered to {len(jurisdictions)} jurisdictions of type '{type_filter}' (from {original_count})"
        )

    # Apply search filter if provided (case-insensitive partial match)
    if search_term:
        search_lower = search_term.lower()
        original_count = len(jurisdictions)
        jurisdictions = [j for j in jurisdictions if search_lower in j.title.lower()]
        logger.info(
            f"Filtered to {len(jurisdictions)} jurisdictions matching '{search_term}' (from {original_count})"
        )

    return jurisdictions


def get_jurisdiction_details(
    jurisdiction_id: str, force_refresh: bool = False, hide_hidden_sets: bool = True
) -> JurisdictionDetails:
    """
    Fetch jurisdiction metadata including standard set references.

    Jurisdiction metadata is cached locally in data/raw/jurisdictions/{jurisdiction_id}/data.json
    to avoid repeated API calls. Use force_refresh=True to fetch fresh data from the API.

    Note: This returns metadata about standard sets (IDs, titles, subjects) but NOT the
    full standard set content. Use download_standard_set() to get full standard set data.

    Args:
        jurisdiction_id: The jurisdiction GUID
        force_refresh: If True, fetch fresh data from API and update cache
        hide_hidden_sets: If True, hide deprecated/outdated sets (default: True)

    Returns:
        JurisdictionDetails model with jurisdiction metadata and standardSets array
    """
    cache_dir = settings.raw_data_dir / "jurisdictions" / jurisdiction_id
    cache_file = cache_dir / "data.json"
    raw_data: dict[str, Any] = {}

    # Check cache first (unless forcing refresh)
    if not force_refresh and cache_file.exists():
        try:
            logger.info(f"Loading jurisdiction {jurisdiction_id} from cache")
            with open(cache_file, encoding="utf-8") as f:
                cached_response = json.load(f)
            raw_data = cached_response.get("data", {})
            logger.info(f"Loaded jurisdiction metadata from cache")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache: {e}. Fetching from API...")
            force_refresh = True

    # Fetch from API if cache doesn't exist or force_refresh is True
    if force_refresh or not raw_data:
        logger.info(f"Fetching jurisdiction {jurisdiction_id} from API")
        params = {"hideHiddenSets": "true" if hide_hidden_sets else "false"}
        response = _make_request(f"/jurisdictions/{jurisdiction_id}", params=params)
        raw_data = response.get("data", {})

        # Save to cache
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(response, f, indent=2, ensure_ascii=False)
            logger.info(f"Cached jurisdiction metadata to {cache_file}")
        except IOError as e:
            logger.warning(f"Failed to save cache: {e}")

    # Parse into Pydantic model
    return JurisdictionDetails(**raw_data)


def download_standard_set(set_id: str, force_refresh: bool = False) -> StandardSet:
    """
    Download full standard set data with caching.

    Standard set data is cached locally in data/raw/standardSets/{set_id}/data.json
    to avoid repeated API calls. Use force_refresh=True to fetch fresh data from the API.

    Args:
        set_id: The standard set GUID
        force_refresh: If True, fetch fresh data from API and update cache

    Returns:
        StandardSet model with complete standard set data including hierarchy
    """
    cache_dir = settings.raw_data_dir / "standardSets" / set_id
    cache_file = cache_dir / "data.json"
    raw_data: dict[str, Any] = {}

    # Check cache first (unless forcing refresh)
    if not force_refresh and cache_file.exists():
        try:
            logger.info(f"Loading standard set {set_id} from cache")
            with open(cache_file, encoding="utf-8") as f:
                cached_response = json.load(f)
            raw_data = cached_response.get("data", {})
            logger.info(f"Loaded standard set from cache")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache: {e}. Fetching from API...")
            force_refresh = True

    # Fetch from API if cache doesn't exist or force_refresh is True
    if force_refresh or not raw_data:
        logger.info(f"Downloading standard set {set_id} from API")
        response = _make_request(f"/standard_sets/{set_id}")
        raw_data = response.get("data", {})

        # Save to cache
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(response, f, indent=2, ensure_ascii=False)
            logger.info(f"Cached standard set to {cache_file}")
        except IOError as e:
            logger.warning(f"Failed to save cache: {e}")

    # Parse into Pydantic model
    return StandardSet(**raw_data)


def _filter_standard_set(
    standard_set: StandardSetReference,
    education_levels: list[str] | None = None,
    publication_status: str | None = None,
    valid_year: str | None = None,
    title_search: str | None = None,
    subject_search: str | None = None,
) -> bool:
    """
    Check if a standard set matches all provided filters (AND logic).

    Args:
        standard_set: StandardSetReference model from jurisdiction metadata
        education_levels: List of grade levels to match (any match)
        publication_status: Publication status to match
        valid_year: Valid year string to match
        title_search: Partial string match on title (case-insensitive)
        subject_search: Partial string match on subject (case-insensitive)

    Returns:
        True if standard set matches all provided filters
    """
    # Filter by education levels (any match)
    if education_levels:
        set_levels = {level.upper() for level in standard_set.educationLevels}
        filter_levels = {level.upper() for level in education_levels}
        if not set_levels.intersection(filter_levels):
            return False

    # Filter by publication status
    if publication_status:
        if (
            standard_set.document.publicationStatus
            and standard_set.document.publicationStatus.lower()
            != publication_status.lower()
        ):
            return False

    # Filter by valid year
    if valid_year:
        if standard_set.document.valid != valid_year:
            return False

    # Filter by title search (partial match, case-insensitive)
    if title_search:
        if title_search.lower() not in standard_set.title.lower():
            return False

    # Filter by subject search (partial match, case-insensitive)
    if subject_search:
        if subject_search.lower() not in standard_set.subject.lower():
            return False

    return True


def download_standard_sets_by_jurisdiction(
    jurisdiction_id: str,
    force_refresh: bool = False,
    education_levels: list[str] | None = None,
    publication_status: str | None = None,
    valid_year: str | None = None,
    title_search: str | None = None,
    subject_search: str | None = None,
) -> list[str]:
    """
    Download standard sets for a jurisdiction with optional filtering.

    Args:
        jurisdiction_id: The jurisdiction GUID
        force_refresh: If True, force refresh all downloads (ignores cache)
        education_levels: List of grade levels to filter by
        publication_status: Publication status to filter by
        valid_year: Valid year string to filter by
        title_search: Partial string match on title
        subject_search: Partial string match on subject

    Returns:
        List of downloaded standard set IDs
    """
    # Get jurisdiction metadata
    jurisdiction_data = get_jurisdiction_details(jurisdiction_id, force_refresh=False)
    standard_sets = jurisdiction_data.standardSets

    # Apply filters
    filtered_sets = [
        s
        for s in standard_sets
        if _filter_standard_set(
            s,
            education_levels=education_levels,
            publication_status=publication_status,
            valid_year=valid_year,
            title_search=title_search,
            subject_search=subject_search,
        )
    ]

    # Download each filtered standard set
    downloaded_ids = []
    for standard_set in filtered_sets:
        set_id = standard_set.id
        try:
            download_standard_set(set_id, force_refresh=force_refresh)
            downloaded_ids.append(set_id)
        except Exception as e:
            logger.error(f"Failed to download standard set {set_id}: {e}")

    return downloaded_ids
