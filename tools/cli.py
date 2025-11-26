"""CLI entry point for EduMatch Data Management."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from tools import api_client, data_manager
from tools.config import get_settings
from tools.pinecone_processor import process_and_save

settings = get_settings()

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)
logger.add(
    settings.log_file,
    rotation=settings.log_rotation,
    retention=settings.log_retention,
    format="{time} | {level} | {message}",
)

app = typer.Typer(help="Common Core MCP CLI - Manage educational standards data")
console = Console()


@app.command()
def jurisdictions(
    search: str = typer.Option(
        None,
        "--search",
        "-s",
        help="Filter by jurisdiction name (case-insensitive partial match)",
    ),
    type: str = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by jurisdiction type: school, organization, state, or nation",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force refresh from API, ignoring local cache"
    ),
):
    """
    List all available jurisdictions (states/organizations).

    By default, jurisdictions are loaded from local cache (data/raw/jurisdictions.json)
    to avoid repeated API calls. Use --force to fetch fresh data from the API and update
    the cache. The cache is automatically created on first use.

    Filters can be combined: use --search to filter by name and --type to filter by type.
    """
    try:
        if force:
            console.print("[yellow]Forcing refresh from API...[/yellow]")

        # Validate type filter if provided
        if type:
            valid_types = {"school", "organization", "state", "nation"}
            if type.lower() not in valid_types:
                console.print(
                    f"[red]Error: Invalid type '{type}'. Must be one of: {', '.join(sorted(valid_types))}[/red]"
                )
                raise typer.Exit(code=1)

        results = api_client.get_jurisdictions(
            search_term=search, type_filter=type, force_refresh=force
        )

        table = Table("ID", "Title", "Type", title="Jurisdictions")
        for j in results:
            table.add_row(j.id, j.title, j.type)

        console.print(table)
        console.print(f"\n[green]Found {len(results)} jurisdictions[/green]")

        if not force:
            console.print("[dim]Tip: Use --force to refresh from API[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to fetch jurisdictions")
        raise typer.Exit(code=1)


@app.command()
def jurisdiction_details(
    jurisdiction_id: str = typer.Argument(..., help="Jurisdiction ID"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force refresh from API, ignoring local cache"
    ),
):
    """
    Download and display jurisdiction metadata including standard set references.

    By default, jurisdiction metadata is loaded from local cache (data/raw/jurisdictions/{id}/data.json)
    to avoid repeated API calls. Use --force to fetch fresh data from the API and update the cache.
    The cache is automatically created on first use.

    Note: This command downloads metadata about standard sets (IDs, titles, subjects) but NOT
    the full standard set content. Use the 'download' command to get full standard set data.
    """
    try:
        if force:
            console.print("[yellow]Forcing refresh from API...[/yellow]")

        jurisdiction_data = api_client.get_jurisdiction_details(
            jurisdiction_id, force_refresh=force
        )

        # Display jurisdiction info
        console.print(f"\n[bold]Jurisdiction:[/bold] {jurisdiction_data.title}")
        console.print(f"[bold]Type:[/bold] {jurisdiction_data.type}")
        console.print(f"[bold]ID:[/bold] {jurisdiction_data.id}")

        # Display standard sets
        standard_sets = jurisdiction_data.standardSets
        if standard_sets:
            table = Table(
                "Set ID", "Subject", "Title", "Grade Levels", title="Standard Sets"
            )
            for s in standard_sets:
                grade_levels = ", ".join(s.educationLevels)
                table.add_row(
                    s.id,
                    s.subject,
                    s.title,
                    grade_levels or "N/A",
                )

            console.print("\n")
            console.print(table)
            console.print(f"\n[green]Found {len(standard_sets)} standard sets[/green]")
        else:
            console.print("\n[yellow]No standard sets found[/yellow]")

        if not force:
            console.print("[dim]Tip: Use --force to refresh from API[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to fetch jurisdiction details")
        raise typer.Exit(code=1)


@app.command("download-sets")
def download_sets(
    set_id: str = typer.Argument(None, help="Standard set ID (if downloading by ID)"),
    jurisdiction: str = typer.Option(
        None,
        "--jurisdiction",
        "-j",
        help="Jurisdiction ID (if downloading by jurisdiction)",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force refresh from API, ignoring local cache"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt when downloading by jurisdiction",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be downloaded without actually downloading",
    ),
    education_levels: str = typer.Option(
        None,
        "--education-levels",
        help="Comma-separated grade levels (e.g., '03,04,05')",
    ),
    publication_status: str = typer.Option(
        None,
        "--publication-status",
        help="Publication status filter (e.g., 'Published', 'Deprecated')",
    ),
    valid_year: str = typer.Option(
        None, "--valid-year", help="Valid year filter (e.g., '2012')"
    ),
    title: str = typer.Option(
        None, "--title", help="Partial title match (case-insensitive)"
    ),
    subject: str = typer.Option(
        None, "--subject", help="Partial subject match (case-insensitive)"
    ),
):
    """
    Download standard sets either by ID or by jurisdiction with filtering.

    When downloading by jurisdiction, filters can be applied and all filters combine with AND logic.
    A confirmation prompt will be shown listing all standard sets that will be downloaded.

    Use --dry-run to preview what would be downloaded without actually downloading anything.
    """
    try:
        # Validate arguments
        if not set_id and not jurisdiction:
            console.print(
                "[red]Error: Must provide either set_id or --jurisdiction[/red]"
            )
            raise typer.Exit(code=1)

        if set_id and jurisdiction:
            console.print(
                "[red]Error: Cannot specify both set_id and --jurisdiction[/red]"
            )
            raise typer.Exit(code=1)

        # Download by ID
        if set_id:
            if dry_run:
                console.print(
                    f"[yellow][DRY RUN] Would download standard set: {set_id}[/yellow]"
                )
                cache_path = Path("data/raw/standardSets") / set_id / "data.json"
                console.print(f"  Would cache to: {cache_path}")
                return

            with console.status(f"[bold blue]Downloading standard set {set_id}..."):
                api_client.download_standard_set(set_id, force_refresh=force)

            cache_path = Path("data/raw/standardSets") / set_id / "data.json"
            console.print("[green]✓ Successfully downloaded standard set[/green]")
            console.print(f"  Cached to: {cache_path}")

            # Process the downloaded set
            try:
                with console.status(f"[bold blue]Processing standard set {set_id}..."):
                    processed_path = process_and_save(set_id)
                console.print("[green]✓ Successfully processed standard set[/green]")
                console.print(f"  Processed to: {processed_path}")
            except FileNotFoundError:
                console.print(
                    "[yellow]Warning: data.json not found, skipping processing[/yellow]"
                )
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to process standard set: {e}[/yellow]"
                )
                logger.exception(f"Failed to process standard set {set_id}")

            return

        # Download by jurisdiction
        if jurisdiction:
            # Parse education levels
            education_levels_list = None
            if education_levels:
                education_levels_list = [
                    level.strip() for level in education_levels.split(",")
                ]

            # Get jurisdiction metadata
            jurisdiction_data = api_client.get_jurisdiction_details(
                jurisdiction, force_refresh=False
            )
            all_sets = jurisdiction_data.standardSets

            # Apply filters using the API client's filter function
            from tools.api_client import _filter_standard_set

            filtered_sets = [
                s
                for s in all_sets
                if _filter_standard_set(
                    s,
                    education_levels=education_levels_list,
                    publication_status=publication_status,
                    valid_year=valid_year,
                    title_search=title,
                    subject_search=subject,
                )
            ]

            if not filtered_sets:
                console.print(
                    "[yellow]No standard sets match the provided filters.[/yellow]"
                )
                return

            # Display filtered sets
            if dry_run:
                console.print(
                    f"\n[yellow][DRY RUN] Standard sets that would be downloaded ({len(filtered_sets)}):[/yellow]"
                )
            else:
                console.print(
                    f"\n[bold]Standard sets to download ({len(filtered_sets)}):[/bold]"
                )

            table = Table(
                "Set ID",
                "Subject",
                "Title",
                "Grade Levels",
                "Status",
                "Year",
                "Downloaded",
                title="Standard Sets",
            )
            for s in filtered_sets:
                display_id = s.id[:20] + "..." if len(s.id) > 20 else s.id
                # Check if already downloaded
                set_data_path = settings.standard_sets_dir / s.id / "data.json"
                is_downloaded = set_data_path.exists()
                downloaded_status = (
                    "[green]✓[/green]" if is_downloaded else "[yellow]✗[/yellow]"
                )
                table.add_row(
                    display_id,
                    s.subject,
                    s.title[:40],
                    ", ".join(s.educationLevels),
                    s.document.publicationStatus or "N/A",
                    s.document.valid,
                    downloaded_status,
                )
            console.print(table)

            # If dry run, show summary and exit
            if dry_run:
                console.print(
                    f"\n[yellow][DRY RUN] Would download {len(filtered_sets)} standard set(s)[/yellow]"
                )
                console.print(
                    "[dim]Run without --dry-run to actually download these standard sets.[/dim]"
                )
                return

            # Confirmation prompt
            if not yes:
                if not typer.confirm(
                    f"\nDownload {len(filtered_sets)} standard set(s)?"
                ):
                    console.print("[yellow]Download cancelled.[/yellow]")
                    return

            # Download each standard set
            console.print(
                f"\n[bold blue]Downloading {len(filtered_sets)} standard set(s)...[/bold blue]"
            )
            downloaded = 0
            failed = 0

            for i, standard_set in enumerate(filtered_sets, 1):
                set_id = standard_set.id
                try:
                    with console.status(
                        f"[bold blue][{i}/{len(filtered_sets)}] Downloading {set_id[:20]}..."
                    ):
                        api_client.download_standard_set(set_id, force_refresh=force)
                    downloaded += 1

                    # Process the downloaded set
                    try:
                        with console.status(
                            f"[bold blue][{i}/{len(filtered_sets)}] Processing {set_id[:20]}..."
                        ):
                            process_and_save(set_id)
                    except FileNotFoundError:
                        console.print(
                            f"[yellow]Warning: Skipping processing for {set_id[:20]}... (data.json not found)[/yellow]"
                        )
                    except Exception as e:
                        console.print(
                            f"[yellow]Warning: Failed to process {set_id[:20]}...: {e}[/yellow]"
                        )
                        logger.exception(f"Failed to process standard set {set_id}")

                except Exception as e:
                    console.print(f"[red]✗ Failed to download {set_id}: {e}[/red]")
                    logger.exception(f"Failed to download standard set {set_id}")
                    failed += 1

            # Summary
            console.print(
                f"\n[green]✓ Successfully downloaded {downloaded} standard set(s)[/green]"
            )
            if failed > 0:
                console.print(
                    f"[red]✗ Failed to download {failed} standard set(s)[/red]"
                )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to download standard sets")
        raise typer.Exit(code=1)


@app.command("list")
def list_datasets():
    """List all downloaded standard sets and their processing status."""
    try:
        datasets = data_manager.list_downloaded_standard_sets()

        if not datasets:
            console.print("[yellow]No standard sets downloaded yet.[/yellow]")
            console.print("[dim]Use 'download-sets' to download standard sets.[/dim]")
            return

        # Check for processed.json files
        for d in datasets:
            set_dir = settings.standard_sets_dir / d.set_id
            processed_file = set_dir / "processed.json"
            d.processed = processed_file.exists()

        # Count processed vs unprocessed
        processed_count = sum(1 for d in datasets if d.processed)
        unprocessed_count = len(datasets) - processed_count

        table = Table(
            "Set ID",
            "Jurisdiction",
            "Subject",
            "Title",
            "Grades",
            "Status",
            "Processed",
            title="Downloaded Standard Sets",
        )
        for d in datasets:
            # Truncate long set IDs
            display_id = d.set_id[:25] + "..." if len(d.set_id) > 25 else d.set_id

            table.add_row(
                display_id,
                d.jurisdiction,
                d.subject[:30],
                d.title[:30],
                ", ".join(d.education_levels),
                d.publication_status,
                "[green]✓[/green]" if d.processed else "[yellow]✗[/yellow]",
            )

        console.print(table)
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Total: {len(datasets)} standard sets")
        console.print(f"  Processed: [green]{processed_count}[/green]")
        console.print(f"  Unprocessed: [yellow]{unprocessed_count}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to list datasets")
        raise typer.Exit(code=1)


@app.command("pinecone-init")
def pinecone_init():
    """
    Initialize Pinecone index.

    Checks if the configured index exists and creates it if not.
    Uses integrated embeddings with llama-text-embed-v2 model.
    """
    try:
        from tools.pinecone_client import PineconeClient

        console.print("[bold]Initializing Pinecone...[/bold]")

        # Initialize Pinecone client (validates API key)
        try:
            client = PineconeClient()
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

        console.print(f"  Index name: [cyan]{client.index_name}[/cyan]")
        console.print(f"  Namespace: [cyan]{client.namespace}[/cyan]")

        # Check and create index if needed
        with console.status("[bold blue]Checking index status..."):
            created = client.ensure_index_exists()

        if created:
            console.print(
                f"\n[green]Successfully created index '{client.index_name}'[/green]"
            )
            console.print("[dim]Index configuration:[/dim]")
            console.print("  Cloud: aws")
            console.print("  Region: us-east-1")
            console.print("  Embedding model: llama-text-embed-v2")
            console.print("  Field map: text -> content")
        else:
            console.print(
                f"\n[green]Index '{client.index_name}' already exists[/green]"
            )

            # Show index stats
            with console.status("[bold blue]Fetching index stats..."):
                stats = client.get_index_stats()

            console.print("\n[bold]Index Statistics:[/bold]")
            console.print(f"  Total vectors: [cyan]{stats['total_vector_count']}[/cyan]")

            namespaces = stats.get("namespaces", {})
            if namespaces:
                console.print(f"  Namespaces: [cyan]{len(namespaces)}[/cyan]")
                table = Table("Namespace", "Vector Count", title="Namespace Details")
                for ns_name, ns_info in namespaces.items():
                    vector_count = getattr(ns_info, "vector_count", 0)
                    table.add_row(ns_name or "(default)", str(vector_count))
                console.print(table)
            else:
                console.print("  Namespaces: [yellow]None (empty index)[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to initialize Pinecone")
        raise typer.Exit(code=1)


@app.command("pinecone-upload")
def pinecone_upload(
    set_id: str = typer.Option(
        None, "--set-id", help="Upload a specific standard set by ID"
    ),
    all: bool = typer.Option(
        False, "--all", help="Upload all downloaded standard sets with processed.json"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-upload even if .pinecone_uploaded marker exists",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be uploaded without actually uploading",
    ),
    batch_size: int = typer.Option(
        96, "--batch-size", help="Number of records per batch (default: 96)"
    ),
):
    """
    Upload processed standard sets to Pinecone.

    Use --set-id to upload a specific set, or --all to upload all sets with processed.json.
    If neither is provided, you'll be prompted to confirm uploading all sets.
    """
    try:
        from tools.pinecone_client import PineconeClient
        from tools.pinecone_models import ProcessedStandardSet
        import json

        # Initialize Pinecone client
        try:
            client = PineconeClient()
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

        # Validate index exists
        try:
            client.validate_index()
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

        # Discover standard sets with processed.json
        standard_sets_dir = settings.standard_sets_dir
        if not standard_sets_dir.exists():
            console.print("[yellow]No standard sets directory found.[/yellow]")
            console.print(
                "[dim]Use 'download-sets' to download standard sets first.[/dim]"
            )
            return

        # Find all sets with processed.json
        sets_to_upload = []
        for set_dir in standard_sets_dir.iterdir():
            if not set_dir.is_dir():
                continue

            processed_file = set_dir / "processed.json"
            if not processed_file.exists():
                continue

            set_id_from_dir = set_dir.name

            # Check if already uploaded (unless --force)
            # Mark all sets during discovery; filtering by --set-id happens later
            if not force and PineconeClient.is_uploaded(set_dir):
                sets_to_upload.append(
                    (set_id_from_dir, set_dir, True)
                )  # True = already uploaded
            else:
                sets_to_upload.append(
                    (set_id_from_dir, set_dir, False)
                )  # False = needs upload

        if not sets_to_upload:
            console.print(
                "[yellow]No standard sets with processed.json found.[/yellow]"
            )
            console.print(
                "[dim]Use 'download-sets' to download and process standard sets first.[/dim]"
            )
            return

        # Filter by --set-id if provided
        if set_id:
            sets_to_upload = [
                (sid, sdir, skipped)
                for sid, sdir, skipped in sets_to_upload
                if sid == set_id
            ]
            if not sets_to_upload:
                console.print(
                    f"[yellow]Standard set '{set_id}' not found or has no processed.json.[/yellow]"
                )
                return

        # If neither --set-id nor --all provided, prompt for confirmation
        if not set_id and not all:
            console.print(
                f"\n[bold]Found {len(sets_to_upload)} standard set(s) with processed.json:[/bold]"
            )
            table = Table("Set ID", "Status", title="Standard Sets")
            for sid, sdir, skipped in sets_to_upload:
                status = (
                    "[yellow]Already uploaded[/yellow]"
                    if skipped
                    else "[green]Ready[/green]"
                )
                table.add_row(sid, status)
            console.print(table)

            if not typer.confirm(
                f"\nUpload {len(sets_to_upload)} standard set(s) to Pinecone?"
            ):
                console.print("[yellow]Upload cancelled.[/yellow]")
                return

        # Show what would be uploaded (dry-run or preview)
        if dry_run or not all:
            console.print(
                f"\n[bold]Standard sets to upload ({len(sets_to_upload)}):[/bold]"
            )
            table = Table("Set ID", "Records", "Status", title="Upload Preview")
            for sid, sdir, skipped in sets_to_upload:
                if skipped and not force:
                    table.add_row(
                        sid, "N/A", "[yellow]Skipped (already uploaded)[/yellow]"
                    )
                    continue

                # Load processed.json to count records
                try:
                    with open(sdir / "processed.json", encoding="utf-8") as f:
                        processed_data = json.load(f)
                    record_count = len(processed_data.get("records", []))
                    status = (
                        "[green]Ready[/green]"
                        if not dry_run
                        else "[yellow]Would upload[/yellow]"
                    )
                    table.add_row(sid, str(record_count), status)
                except Exception as e:
                    table.add_row(sid, "Error", f"[red]Failed to read: {e}[/red]")
            console.print(table)

        if dry_run:
            console.print(
                f"\n[yellow][DRY RUN] Would upload {len([s for s in sets_to_upload if not s[2] or force])} standard set(s)[/yellow]"
            )
            console.print("[dim]Run without --dry-run to actually upload.[/dim]")
            return

        # Perform uploads
        uploaded_count = 0
        failed_count = 0
        skipped_count = 0

        for i, (sid, sdir, already_uploaded) in enumerate(sets_to_upload, 1):
            if already_uploaded and not force:
                skipped_count += 1
                continue

            try:
                # Load processed.json
                with open(sdir / "processed.json", encoding="utf-8") as f:
                    processed_data = json.load(f)

                processed_set = ProcessedStandardSet(**processed_data)
                records = processed_set.records

                if not records:
                    console.print(
                        f"[yellow]Skipping {sid} (no records)[/yellow]"
                    )
                    skipped_count += 1
                    continue

                # Upload records
                with console.status(
                    f"[bold blue][{i}/{len(sets_to_upload)}] Uploading {sid} ({len(records)} records)"
                ):
                    client.batch_upsert(records, batch_size=batch_size)

                # Mark as uploaded
                PineconeClient.mark_uploaded(sdir)
                uploaded_count += 1
                console.print(
                    f"[green]✓ [{i}/{len(sets_to_upload)}] Uploaded {sid} ({len(records)} records)[/green]"
                )

            except FileNotFoundError:
                console.print(
                    f"[red]✗ [{i}/{len(sets_to_upload)}] Failed: {sid} (processed.json not found)[/red]"
                )
                logger.exception(f"Failed to upload standard set {sid}")
                failed_count += 1
            except Exception as e:
                console.print(
                    f"[red]✗ [{i}/{len(sets_to_upload)}] Failed: {sid} ({e})[/red]"
                )
                logger.exception(f"Failed to upload standard set {sid}")
                failed_count += 1

        # Summary
        console.print("\n[bold]Upload Summary:[/bold]")
        console.print(f"  Uploaded: [green]{uploaded_count}[/green]")
        if skipped_count > 0:
            console.print(f"  Skipped: [yellow]{skipped_count}[/yellow]")
        if failed_count > 0:
            console.print(f"  Failed: [red]{failed_count}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to upload to Pinecone")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
