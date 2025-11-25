
import requests
from bs4 import BeautifulSoup
from schools_scraper.abc_scraper import ABCScraper

def debug_racecard():
    scraper = ABCScraper(use_tomorrow=True)
    print("Fetching guide...")
    data = scraper.parse_guide()
    
    # Find Ten Carat Harry
    target = next((d for d in data if "Ten Carat Harry" in d["horse"]), None)
    
    if not target:
        print("Ten Carat Harry not found in guide.")
        return

    print(f"Found target: {target['horse']}")
    print(f"Race URL: {target['race_url']}")
    
    # Fetch Racecard
    print("Fetching racecard...")
    resp = scraper.session.get(target['race_url'])
    soup = BeautifulSoup(resp.content, "html.parser")
    
    # Find horse
    horse_link = soup.find("a", string=lambda t: t and "Ten Carat Harry" in t.strip())
    if not horse_link:
        print("Horse link not found in racecard.")
        return
    
    print(f"Found Horse Link: {horse_link}")

    # Check for Draw text globally
    if "(2)" in soup.get_text():
        print("Global check: '(2)' found in page text.")
    else:
        print("Global check: '(2)' NOT found in page text. Page might be missing data?")

    # Traverse up
    row = horse_link
    found_row = None
    for i in range(12): 
        row = row.parent
        if not row: break
        
        classes = row.get('class', [])
        print(f"Level {i} tag: {row.name} class: {classes}")
        
        # We want a container that looks like a list item or row
        if "Runner__StyledRunnerItem" in str(classes) or row.name == "section" or (row.name == "div" and "hr-racing-runner-wrapper" in str(classes)):
             found_row = row
             # Keep going up? No, usually the item wrapper is what we want.
             # But let's see if this wrapper contains "(2)"
             if "(2)" in row.get_text():
                 print("  -> Contains '(2)'!")
                 break
             else:
                 print("  -> Does NOT contain '(2)'. Continuing up...")

    if found_row:
        print(f"\n--- ROW HTML (Level {found_row.name}) ---")
        print(found_row.prettify()[:2000])
        print("\n--- ROW TEXT ---")
        print(found_row.get_text("|", strip=True))
    else:
        print("Could not find containing row with metadata and Draw (2).")

if __name__ == "__main__":
    debug_racecard()

