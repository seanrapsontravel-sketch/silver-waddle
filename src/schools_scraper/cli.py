"""CLI interface for the schools scraper."""

from pathlib import Path
from typing import Optional

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from schools_scraper.analysis import Analyzer
from schools_scraper.config import config
from schools_scraper.database import Database
from schools_scraper.gpt import GPTClient
from schools_scraper.io import write_csv, write_parquet
from schools_scraper.newsletter import scrape_newsletter, scrape_newsletter_range
from schools_scraper.scraper import Scraper
from schools_scraper.search import NewsletterSearch
from schools_scraper.abc_scraper import ABCScraper, run_scheduled_job

app = typer.Typer(help="Schools scraper CLI")
console = Console()


@app.command()
def scrape(
    url: str = typer.Argument(..., help="URL to scrape"),
    table_name: str = typer.Option("scraped_data", help="Table name to store data"),
    base_url: Optional[str] = typer.Option(None, help="Base URL for relative links"),
) -> None:
    """Scrape a website and store data in the database."""
    console.print(f"[green]Scraping {url}...[/green]")

    with Scraper(base_url=base_url) as scraper:
        soup = scraper.scrape_page(url)
        if soup is None:
            console.print("[red]Failed to scrape page[/red]")
            raise typer.Exit(1)

        # Example: extract title and text
        title = soup.find("title")
        title_text = title.get_text() if title else "No title"

        # Store in database
        with Database() as db:
            # Create table schema (customize based on your needs)
            schema = {
                "url": "VARCHAR",
                "title": "VARCHAR",
                "scraped_at": "TIMESTAMP",
            }
            db.create_table(table_name, schema)

            data = {
                "url": url,
                "title": title_text,
                "scraped_at": "CURRENT_TIMESTAMP",
            }
            db.insert(table_name, data)

        console.print(f"[green]✓ Scraped and stored in table '{table_name}'[/green]")


@app.command()
def query(
    sql: str = typer.Argument(..., help="SQL query to execute"),
    output: Optional[str] = typer.Option(None, help="Output file path (CSV or Parquet)"),
) -> None:
    """Execute a SQL query on the database."""
    with Database() as db:
        df = db.query(sql)

        if output:
            if output.endswith(".parquet"):
                write_parquet(df, output)
                console.print(f"[green]✓ Saved to {output}[/green]")
            else:
                write_csv(df, output)
                console.print(f"[green]✓ Saved to {output}[/green]")
        else:
            console.print("\n[bold]Query Results:[/bold]")
            console.print(df.to_string())


@app.command()
def analyze(
    table_name: str = typer.Argument(..., help="Table name to analyze"),
    column: Optional[str] = typer.Option(None, help="Column to group by"),
) -> None:
    """Analyze data in a table."""
    with Analyzer() as analyzer:
        if column:
            console.print(f"[green]Counting by {column}...[/green]")
            df = analyzer.count_by_column(table_name, column)
        else:
            console.print(f"[green]Getting descriptive statistics...[/green]")
            df = analyzer.describe_table(table_name)

        console.print("\n[bold]Results:[/bold]")
        console.print(df.to_string())


@app.command()
def gpt_prompt(
    prompt: str = typer.Argument(..., help="Prompt to send to GPT"),
    model: str = typer.Option("gpt-4o-mini", help="GPT model to use"),
) -> None:
    """Send a prompt to GPT."""
    try:
        client = GPTClient()
        console.print(f"[green]Sending prompt to {model}...[/green]")
        response = client.prompt(prompt, model=model)
        console.print("\n[bold]GPT Response:[/bold]")
        console.print(response)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def gpt_analyze(
    table_name: str = typer.Argument(..., help="Table name to analyze"),
    question: str = typer.Option("What insights can you find in this data?", help="Question about the data"),
    model: str = typer.Option("gpt-4o-mini", help="GPT model to use"),
) -> None:
    """Analyze database table using GPT."""
    try:
        client = GPTClient()
        with Database() as db:
            df = db.get_table(table_name)
            console.print(f"[green]Analyzing {table_name} with GPT...[/green]")
            response = client.analyze_dataframe(df, question, model=model)
            console.print("\n[bold]GPT Analysis:[/bold]")
            console.print(response)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def scrape_newsletter_page(
    url: str = typer.Argument(..., help="Newsletter URL to scrape"),
    table_name: str = typer.Option("newsletters", help="Table name to store data"),
) -> None:
    """Scrape a newsletter page and store all content in the database."""
    console.print(f"[green]Scraping newsletter: {url}...[/green]")

    try:
        result = scrape_newsletter(url, table_name)
        console.print(f"[green]✓ Successfully scraped newsletter[/green]")
        console.print(f"  Title: {result['title']}")
        console.print(f"  Text length: {result['text_length']:,} characters")
        console.print(f"  Paragraphs: {result['paragraphs_count']}")
        console.print(f"  Links: {result['links_count']}")
        console.print(f"  Images: {result['images_count']}")
        console.print(f"  Stored in table: {result['table']}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def scrape_newsletter_range_cmd(
    start_id: int = typer.Argument(..., help="Starting newsletter ID"),
    end_id: int = typer.Argument(..., help="Ending newsletter ID (inclusive)"),
    base_url: str = typer.Option(
        "https://www.westst.org.uk/parentportal/newsletter/?id={id}",
        help="Base URL template with {id} placeholder"
    ),
    table_name: str = typer.Option("newsletters", help="Table name to store data"),
    delay: float = typer.Option(1.0, help="Delay between requests in seconds"),
) -> None:
    """Scrape multiple newsletter pages by ID range."""
    console.print(f"[green]Scraping newsletters from ID {start_id} to {end_id}...[/green]")
    console.print(f"Total pages: {end_id - start_id + 1}")
    console.print(f"Delay: {delay}s between requests\n")

    try:
        results = scrape_newsletter_range(
            base_url=base_url,
            start_id=start_id,
            end_id=end_id,
            table_name=table_name,
            delay=delay,
            continue_on_error=True,
        )

        console.print(f"\n[bold]Scraping Summary:[/bold]")
        console.print(f"  Total: {results['total']}")
        console.print(f"  [green]Successful: {results['success_count']}[/green]")
        console.print(f"  [red]Failed: {results['fail_count']}[/red]")

        if results["failed"]:
            console.print(f"\n[red]Failed IDs:[/red]")
            for failed in results["failed"][:10]:  # Show first 10
                console.print(f"  ID {failed['id']}: {failed['error']}")
            if len(results["failed"]) > 10:
                console.print(f"  ... and {len(results['failed']) - 10} more")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_tables() -> None:
    """List all tables in the database."""
    with Database() as db:
        tables = db.query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        )

        if tables.empty:
            console.print("[yellow]No tables found[/yellow]")
        else:
            table = Table(title="Database Tables")
            table.add_column("Table Name", style="cyan")
            for _, row in tables.iterrows():
                table.add_row(row["table_name"])
            console.print(table)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (keywords)"),
    table_name: str = typer.Option("newsletters", help="Table name to search"),
    limit: int = typer.Option(20, help="Maximum number of results"),
    output: Optional[str] = typer.Option(None, help="Output file path (CSV or Parquet)"),
) -> None:
    """Search newsletters using full-text search."""
    console.print(f"[green]Searching for: {query}[/green]")

    try:
        with NewsletterSearch() as search_engine:
            results = search_engine.search_advanced(
                query=query, table_name=table_name, limit=limit
            )

        if results.empty:
            console.print("[yellow]No results found[/yellow]")
            return

        if output:
            if output.endswith(".parquet"):
                write_parquet(results, output)
                console.print(f"[green]✓ Saved {len(results)} results to {output}[/green]")
            else:
                write_csv(results, output)
                console.print(f"[green]✓ Saved {len(results)} results to {output}[/green]")
        else:
            console.print(f"\n[bold]Found {len(results)} results:[/bold]\n")
            # Display key columns in a table
            display_table = Table(title="Search Results")
            display_table.add_column("ID", style="cyan")
            display_table.add_column("Title", style="green")
            display_table.add_column("Heading", style="yellow")
            display_table.add_column("Relevance", style="magenta")
            display_table.add_column("Date", style="blue")

            for _, row in results.head(limit).iterrows():
                title = str(row.get("title", ""))[:50] + "..." if len(str(row.get("title", ""))) > 50 else str(row.get("title", ""))
                heading = str(row.get("heading", ""))[:40] + "..." if len(str(row.get("heading", ""))) > 40 else str(row.get("heading", ""))
                relevance = str(row.get("relevance_score", 0))
                date = str(row.get("scraped_at", ""))[:10] if pd.notna(row.get("scraped_at")) else ""

                display_table.add_row(
                    str(row.get("id", "")),
                    title,
                    heading,
                    relevance,
                    date,
                )

            console.print(display_table)

            if len(results) > limit:
                console.print(f"\n[yellow]Showing first {limit} of {len(results)} results[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to answer about newsletters"),
    table_name: str = typer.Option("newsletters", help="Table name to search"),
    model: str = typer.Option("gpt-4o-mini", help="GPT model to use"),
    max_newsletters: int = typer.Option(20, help="Maximum newsletters to search"),
    max_chars: int = typer.Option(10000, help="Maximum characters of text to include"),
) -> None:
    """Answer a question by searching newsletters and using GPT."""
    console.print(f"[green]Searching newsletters for: {question}[/green]")
    console.print("[dim]This may take a moment...[/dim]\n")

    try:
        client = GPTClient()
        answer, sources = client.answer_question(
            question=question,
            table_name=table_name,
            model=model,
            max_newsletters=max_newsletters,
            max_chars=max_chars,
        )

        console.print("\n[bold cyan]Answer:[/bold cyan]")
        console.print(answer)
        
        if sources:
            console.print("\n[bold]Sources:[/bold]")
            for source in sources:
                if source.get("url"):
                    console.print(f"  • {source.get('title', 'Untitled')}: {source['url']}")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development"),
) -> None:
    """Start the web server for the frontend."""
    import uvicorn
    from schools_scraper.api import app as api_app

    console.print(f"[green]Starting web server on http://{host}:{port}[/green]")
    console.print(f"[dim]Open http://localhost:{port} in your browser[/dim]\n")

    uvicorn.run(api_app, host=host, port=port, reload=reload)


@app.command()
def scrape_abc(
    output: Optional[str] = typer.Option(None, help="Output path for CSV file"),
    daemon: bool = typer.Option(False, help="Run as a daemon scheduled for 9am daily"),
    time: str = typer.Option("09:00", help="Time to run daily scrape (HH:MM)"),
    email: bool = typer.Option(False, help="Send email notification if matches found"),
    tomorrow: bool = typer.Option(False, help="Scrape tomorrow's guide instead of today's"),
) -> None:
    """Scrape Sporting Life ABC Guide."""
    import schedule
    import time as time_lib
    from datetime import datetime

    if daemon:
        console.print(f"[green]Starting ABC Guide Scraper Daemon[/green]")
        console.print(f"Scheduled to run daily at {time}")
        # Daemon always emails
        console.print("Email notifications enabled for daemon mode")
        console.print("Press Ctrl+C to stop")

        # Run once immediately on start? Maybe optional. 
        # For now, we just schedule.
        
        schedule.every().day.at(time).do(run_scheduled_job, output_path=output)
        
        while True:
            schedule.run_pending()
            time_lib.sleep(60)
    else:
        # One-off run
        scraper = ABCScraper(use_tomorrow=tomorrow)
        df = scraper.run(send_email=email)
        
        if not df.empty:
            if output:
                df.to_csv(output, index=False)
                console.print(f"[green]✓ Saved to {output}[/green]")
            else:
                # Just print head if not saving
                pass


if __name__ == "__main__":
    app()

