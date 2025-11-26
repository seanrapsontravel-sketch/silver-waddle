"""Scraper for Sporting Life ABC Guide."""

import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import requests
import schedule
from bs4 import BeautifulSoup
from rich.console import Console

from schools_scraper.config import config
from schools_scraper.email_service import EmailService

console = Console()


class ABCScraper:
    """Scraper for the Sporting Life ABC Guide."""

    BASE_URL = "https://www.sportinglife.com/racing/abc-guide"
    TOMORROW_URL = "https://www.sportinglife.com/racing/abc-guide/tomorrow"
    
    # Horses to watch (partial matches allowed)
    WATCHLIST = [
        "Harry", "Lilly", "Lily", "Izzey", "Izz", "Izzy", 
        "Mason", "Ronnie", "Ronny", "Maddie", "Maddy"
    ]
    
    def __init__(self, use_tomorrow: bool = False) -> None:
        """Initialize the scraper.
        
        Args:
            use_tomorrow: If True, scrapes tomorrow's guide instead of today's.
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        })
        self.url = self.TOMORROW_URL if use_tomorrow else self.BASE_URL

    def fetch_guide(self) -> Optional[BeautifulSoup]:
        """Fetch the ABC guide page.

        Returns:
            BeautifulSoup object or None if failed.
        """
        try:
            response = self.session.get(self.url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            console.print(f"[red]Error fetching ABC guide: {e}[/red]")
            return None

    def parse_guide(self) -> List[Dict[str, str]]:
        """Parse the ABC guide data.

        Returns:
            List of dictionaries containing horse data.
        """
        soup = self.fetch_guide()
        if not soup:
            return []

        data = []
        
        # Sporting Life usually uses standard tables or grid layouts
        # Based on the provided text, it looks like a table structure
        # We'll look for rows that contain horse information
        
        # This is a general approach; specific class names might be needed
        # if the HTML structure is complex.
        
        # Try to find the main table or list items
        # In the text provided: | Horse | Race | Day | Odds |
        
        # Look for rows
        rows = soup.find_all("div", class_="abc-guide-row") # Hypothetical class
        if not rows:
            # Fallback to table rows if it uses a table
            rows = soup.find_all("tr")

        for row in rows:
            try:
                # Extract data based on text or structure
                # This part often requires inspection of the actual HTML
                # For now, we'll try to find links to horses which are distinct
                
                # Horse Name
                horse_elem = row.find("a", href=lambda x: x and "/racing/profiles/horse/" in x)
                if not horse_elem:
                    continue
                
                horse_name = horse_elem.get_text(strip=True)
                horse_url = "https://www.sportinglife.com" + horse_elem["href"]
                
                # Race Info
                # Look for the race link. For Tomorrow, this links directly to /racing/racecards/...
                # For Today, it might be /racing/results/...
                # We prioritize capturing the EXACT href provided.
                race_elem = row.find("a", href=lambda x: x and ("/racing/results/" in x or "/racing/racecards/" in x))
                race_info = race_elem.get_text(strip=True) if race_elem else "Unknown"
                race_url = ("https://www.sportinglife.com" + race_elem["href"]) if race_elem else ""
                
                # Day
                day_elem = row.find(text=lambda x: x and x.strip() in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Today", "Tomorrow"])
                day = day_elem.strip() if day_elem else "Unknown"
                
                # Odds
                odds = "SP"
                cells = row.find_all(["td", "div"])
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if "/" in text and any(c.isdigit() for c in text) and len(text) < 10:
                        odds = text
                        break

                data.append({
                    "horse": horse_name,
                    "horse_url": horse_url,
                    "race": race_info,
                    "race_url": race_url,
                    "day": day,
                    "odds": odds,
                    "scraped_at": datetime.now().isoformat()
                })
                
            except Exception:
                continue
                
        return data

    def fetch_racecard_details(self, race_url: str, horse_name: str) -> Dict[str, str]:
        """Fetch detailed racecard information for a horse.

        Args:
            race_url: URL of the racecard.
            horse_name: Name of the horse to find.

        Returns:
            Dictionary with details (Draw, Jockey, Trainer, Commentary).
        """
        details = {
            "draw": "N/A",
            "jockey": "Unknown",
            "trainer": "Unknown",
            "commentary": "No commentary available."
        }
        
        if not race_url:
            return details

        try:
            # Step 1: Check if the URL is already a Racecard URL (Option 1 - Primary)
            if "/racecards/" in race_url:
                target_url = race_url
            
            # Step 2: If it's a results URL, try to find the racecard link (Option 2 - Fallback)
            elif "/results/" in race_url:
                # First, visit the results page to find the Racecard tab
                # This is safer than guessing the URL structure
                resp = self.session.get(race_url, timeout=config.REQUEST_TIMEOUT)
                resp.raise_for_status()
                soup_res = BeautifulSoup(resp.content, "html.parser")
                
                # Find link to racecard
                # Text is usually "Racecard"
                racecard_link = soup_res.find("a", string=lambda t: t and "Racecard" in t)
                if racecard_link and racecard_link.get("href"):
                    target_url = "https://www.sportinglife.com" + racecard_link["href"]
                else:
                    # Fallback: Construct the URL manually if link not found
                    new_url = race_url.replace("/results/", "/racecards/")
                    import re
                    match = re.search(r"(/racecards/[\d-]+/[^/]+)/(\d+)", new_url)
                    if match:
                        base_part = match.group(1)
                        id_part = match.group(2)
                        target_url = new_url.replace(f"{base_part}/{id_part}", f"{base_part}/racecard/{id_part}")
                    else:
                        target_url = new_url
            else:
                # Unknown format, try accessing directly
                target_url = race_url

            # Step 3: Fetch the Racecard
            response = self.session.get(target_url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find the horse's row in the racecard
            horse_link = soup.find("a", string=lambda t: t and horse_name.lower() == t.strip().lower())
            
            if not horse_link:
                horse_link = soup.find("a", string=lambda t: t and horse_name.lower() in t.lower())

            if horse_link:
                # Traverse up to the runner container
                # We look for a container with class "Runner__StyledRunnerContainer" or similar
                # Based on debug, it's usually 3-4 levels up.
                
                row = horse_link
                runner_container = None
                
                for _ in range(8): 
                    row = row.parent
                    if not row: break
                    
                    # Check classes
                    classes = str(row.get('class', []))
                    if "Runner__StyledRunnerContainer" in classes or "hr-racing-runner-wrapper" in classes:
                        runner_container = row
                        break
                    
                    # Fallback: if we hit a section, maybe went too far, but use it if nothing else
                    if row.name == "section":
                        # But section might contain multiple runners, so be careful.
                        # Prefer the div inside it.
                        pass

                if runner_container:
                    # Get text with separators to help regex
                    all_text = runner_container.get_text("|", strip=True)
                    
                    import re
                    # Debug: console.print(f"[dim]Text found: {all_text[:100]}...[/dim]")
                    
                    # Regex for Jockey: J:|Name|
                    # The separator might be | or spaces depending on get_text
                    # We used "|" separator above.
                    # Pattern: J:|[spaces]Name|[spaces]|
                    j_match = re.search(r"J:\|(.*?)\|", all_text)
                    if j_match:
                        details["jockey"] = j_match.group(1).strip().replace("|", "")
                    else:
                        # Try standard space pattern if | missing
                        j_match_space = re.search(r"J:\s*(.*?)\s*(?:\||T:)", all_text)
                        if j_match_space:
                             details["jockey"] = j_match_space.group(1).strip()
                        
                    # Trainer: T:|Name|
                    t_match = re.search(r"T:\|(.*?)\|", all_text)
                    if t_match:
                        details["trainer"] = t_match.group(1).strip().replace("|", "")
                    else:
                         t_match_space = re.search(r"T:\s*(.*?)\s*(?:\||OR:)", all_text)
                         if t_match_space:
                             details["trainer"] = t_match_space.group(1).strip()
                        
                    # Draw: (d)
                    # Usually at start: 1|(2)|Name
                    # Regex: ^\d+\s*\|\s*\((\d+)\) or just \((\d+)\)
                    # Be careful of other numbers in parens like (ex) or (5) for jockey allowance
                    # Draw is usually near the start of the string
                    d_match = re.search(r"\|\((\d+)\)\|", all_text)
                    if d_match:
                        details["draw"] = d_match.group(1)
                    else:
                        # Try simpler search
                        d_match_simple = re.search(r"\((\d+)\)", all_text)
                        if d_match_simple:
                            # Validate it's likely a draw (small number)
                            if int(d_match_simple.group(1)) < 40:
                                details["draw"] = d_match_simple.group(1)

                    # Commentary
                    # Strategy: Look for the text block between the Metadata end and "Form:"
                    # Metadata usually ends with "D" or Odds "15/8"
                    # Split by "Form:" and take the segment before it?
                    # Text: ...|D|15/8|Commentary Text|Form:|...
                    
                    if "Form:" in all_text:
                        pre_form = all_text.split("Form:")[0]
                        # The commentary is likely the last "segment" of pre_form
                        segments = pre_form.split("|")
                        # Filter out short segments (odds, D, etc)
                        long_segments = [s for s in segments if len(s) > 20]
                        if long_segments:
                            details["commentary"] = long_segments[-1].strip()
                    else:
                        # Fallback: Find longest segment
                         segments = all_text.split("|")
                         longest = max(segments, key=len)
                         if len(longest) > 30:
                             details["commentary"] = longest.strip()

                    # Odds Extraction from Text
                    # Text usually looks like: ...|D|15/8|Commentary... or ...|D|2.88|...
                    # We look for a segment matching strictly odds format
                    segments = all_text.split("|")
                    for segment in segments:
                        s = segment.strip()
                        # Fractional: digit/digit
                        if re.match(r"^\d+/\d+$", s):
                            details["odds"] = s
                            break
                        # Decimal: digit.digit (e.g. 2.88, 10.0)
                        elif re.match(r"^\d+\.\d{1,2}$", s):
                            details["odds"] = s
                            break



        except Exception as e:
            console.print(f"[red]Error fetching details for {horse_name}: {e}[/red]")
            
        return details

    def run(self, filter_watchlist: bool = True, send_email: bool = False) -> pd.DataFrame:
        """Run the scraper and return a DataFrame.

        Args:
            filter_watchlist: If True, highlights or filters for horses on the watchlist.
            send_email: If True, sends an email with the matches.

        Returns:
            DataFrame with scraped data.
        """
        console.print(f"[green]Fetching ABC Guide from {self.url}...[/green]")
        data = self.parse_guide()
        
        if not data:
            console.print("[yellow]No data found or failed to parse.[/yellow]")
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        console.print(f"[green]✓ Found {len(df)} entries[/green]")
        
        matches = []
        # Check for watchlist matches
        if filter_watchlist:
            console.print("\n[bold cyan]Checking Watchlist Matches...[/bold cyan]")
            for _, row in df.iterrows():
                horse_name = row['horse']
                # Check if any watchlist name is in the horse name (case insensitive)
                matched_terms = [term for term in self.WATCHLIST if term.lower() in horse_name.lower()]
                
                if matched_terms:
                    row['matched_terms'] = ", ".join(matched_terms)
                    
                    # Fetch extra details
                    console.print(f"[dim]Fetching details for {horse_name}...[/dim]")
                    details = self.fetch_racecard_details(row['race_url'], horse_name)
                    
                    # Merge details into row (which is a Series, so we convert to dict or update)
                    # Since we are iterating rows, updating 'row' updates the object in memory but not the DF directly unless we assign back
                    # But 'matches' list holds the Series objects.
                    for k, v in details.items():
                        row[k] = v
                    
                    matches.append(row)
                    console.print(f"[bold green]MATCH FOUND:[/bold green] {horse_name} (matched: {', '.join(matched_terms)})")
                    console.print(f"  Race: {row['race']}")
                    console.print(f"  Odds: {row['odds']}")
                    console.print(f"  Draw: {row.get('draw', 'N/A')} | Jockey: {row.get('jockey', 'Unknown')}")
                    console.print(f"  Link: {row['horse_url']}\n")
            
            if not matches:
                console.print("[yellow]No horses from the watchlist found today.[/yellow]")
            else:
                df['is_watchlist'] = df['horse'].apply(
                    lambda x: any(term.lower() in x.lower() for term in self.WATCHLIST)
                )

        # Send email if requested
        if send_email:
            if matches:
                console.print(f"[bold green]Found {len(matches)} matches. Sending email...[/bold green]")
                success = self.send_match_email(matches)
                if not success:
                    console.print("[red]FATAL: Email failed to send. Check SMTP credentials in GitHub Secrets.[/red]")
                    import sys
                    sys.exit(1)
            else:
                console.print("[bold yellow]No watchlist matches found today. No email will be sent.[/bold yellow]")
        
        return df

    def send_match_email(self, matches: List[pd.Series]) -> bool:
        """Send email with matches.
        
        Returns:
            True if successful, False otherwise.
        """
        email = EmailService()
        date_str = datetime.now().strftime("%d-%m-%Y")
        subject = f"🐎 Watchlist Matches Found ({len(matches)}) - {date_str}"
        
        # Build beautiful HTML Body
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: #1a472a; color: white; padding: 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                .header p {{ margin: 5px 0 0; opacity: 0.9; }}
                .content {{ padding: 20px; }}
                .card {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #fff; border-left: 5px solid #2ecc71; }}
                .horse-name {{ font-size: 18px; font-weight: bold; color: #2c3e50; margin: 0 0 5px; }}
                .horse-name a {{ text-decoration: none; color: inherit; }}
                .horse-name a:hover {{ text-decoration: underline; }}
                .details {{ font-size: 14px; color: #666; line-height: 1.5; }}
                .match-tag {{ display: inline-block; background: #e8f5e9; color: #27ae60; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-left: 8px; }}
                .odds {{ float: right; font-weight: bold; color: #e74c3c; background: #fdeea2; padding: 2px 8px; border-radius: 4px; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #7f8c8d; border-top: 1px solid #eee; }}
                .btn {{ display: inline-block; background: #1a472a; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; margin-top: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🐎 Watchlist Match Report</h1>
                    <p>{date_str}</p>
                </div>
                <div class="content">
                    <p style="margin-bottom: 20px;">Hello! We found <strong>{len(matches)}</strong> horses from your watchlist in today's ABC Guide.</p>
        """
        
        for match in matches:
            matched_term = match.get('matched_terms', 'Unknown')
            odds_display = match['odds'] if match['odds'] != 'SP' else 'SP'
            draw_display = f" (Draw: {match.get('draw', '-')})" if match.get('draw') and match.get('draw') != 'N/A' else ""
            commentary = match.get('commentary', 'No commentary available.')
            
            body += f"""
            <div class="card">
                <div class="horse-name">
                    <a href="{match['horse_url']}">{match['horse']}</a>
                    <span class="match-tag">Matched: {matched_term}</span>
                    <span class="odds">{odds_display}</span>
                </div>
                <div class="details">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span>📍 <strong>Race:</strong> {match['race']}</span>
                        <span>🗓 <strong>Day:</strong> {match['day']}</span>
                    </div>
                    <div style="background: #f9f9f9; padding: 8px; border-radius: 4px; margin-bottom: 10px;">
                        <strong>Jockey:</strong> {match.get('jockey', 'Unknown')} | 
                        <strong>Trainer:</strong> {match.get('trainer', 'Unknown')} {draw_display}
                    </div>
                    <div style="margin-bottom: 10px; font-style: italic; color: #555;">
                        "{commentary}"
                    </div>
                    <a href="{match['race_url']}" class="btn">View Racecard</a>
                </div>
            </div>
            """
            
        body += """
                </div>
                <div class="footer">
                    <p>Automated report from Schools Scraper | Sporting Life ABC Guide</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return email.send_notification(subject, body)


def run_scheduled_job(output_path: Optional[str] = None):
    """Job to run on schedule."""
    console.print(f"\n[bold]Running scheduled scrape at {datetime.now().strftime('%H:%M:%S')}[/bold]")
    scraper = ABCScraper()
    # Enable email for scheduled jobs
    df = scraper.run(send_email=True)
    
    if not df.empty:
        # Determine output file
        if output_path:
            # Add timestamp to filename if it's a directory or base name
            if output_path.endswith(".csv"):
                # Inject date: file.csv -> file_2023-01-01.csv
                base = output_path[:-4]
                date_str = datetime.now().strftime("%Y-%m-%d")
                file_path = f"{base}_{date_str}.csv"
            else:
                file_path = f"{output_path}/abc_guide_{datetime.now().strftime('%Y-%m-%d')}.csv"
        else:
            file_path = f"data/exports/abc_guide_{datetime.now().strftime('%Y-%m-%d')}.csv"
            
        # Create dir if needed
        import os
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        
        df.to_csv(file_path, index=False)
        console.print(f"[green]✓ Saved to {file_path}[/green]")
    else:
        console.print("[red]Scrape failed or empty[/red]")


