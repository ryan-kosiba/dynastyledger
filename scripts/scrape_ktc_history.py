"""Scrape historical player values from KeepTradeCut (KTC).

KTC renders an SVG value chart via JavaScript on each player's detail page.
This script uses Playwright to render the page, clicks the "all-time" button
to expand the full history, then parses the SVG hover-group elements to
extract date/value pairs.

Usage:
    python scripts/scrape_ktc_history.py
"""

import re
import sys
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import insert_player_values

PLAYER_SLUG = "saquon-barkley-1"
PLAYER_NAME = "Saquon Barkley"
BASE_URL = "https://keeptradecut.com/dynasty-rankings/players"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"


def scrape_ktc_history(player_slug: str, player_name: str) -> pd.DataFrame:
    """Scrape full value history for a single player from KTC."""
    # Extract the numeric KTC player ID from the slug (e.g. "saquon-barkley-1" -> 1)
    player_id = int(player_slug.rsplit("-", 1)[-1])
    url = f"{BASE_URL}/{player_slug}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Dismiss the KTC voting modal via JavaScript
        page.evaluate("""
            const modal = document.querySelector('#pdpKTCModal');
            if (modal) {
                modal.style.display = 'none';
                modal.classList.remove('show');
            }
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) backdrop.remove();
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
        """)

        # Click the "all-time" button to show full history
        page.click("#all-time", timeout=5000)

        # Wait for SVG hover groups to render
        page.wait_for_selector("g.hoverGroup", timeout=10000)
        page.wait_for_timeout(1000)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    # Scope to the value chart only — the rank chart also has hoverGroups
    value_chart = soup.find(id="block-value-graph")
    hover_groups = value_chart.find_all("g", class_="hoverGroup") if value_chart else []

    records = []
    for group in hover_groups:
        date_el = group.find("text", class_="hoverDate")
        val_el = group.find("text", class_=lambda c: c and "hoverVal" in c)

        if date_el and val_el:
            date_text = date_el.get_text(strip=True).replace(".", "")
            val_text = val_el.get_text(strip=True)
            val_clean = re.sub(r"[^\d.]", "", val_text)
            if date_text and val_clean:
                records.append(
                    {
                        "player_id": player_id,
                        "name": player_name,
                        "date": date_text,
                        "value": int(float(val_clean)),
                    }
                )

    df = pd.DataFrame(records, columns=["player_id", "name", "date", "value"])
    df["date"] = pd.to_datetime(df["date"], format="%b %d, %Y")
    df = df.sort_values("date").reset_index(drop=True)
    return df


def main():
    print(f"Scraping KTC history for {PLAYER_NAME} ({PLAYER_SLUG})...")
    df = scrape_ktc_history(PLAYER_SLUG, PLAYER_NAME)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug_underscored = PLAYER_SLUG.replace("-", "_")
    output_path = OUTPUT_DIR / f"ktc_history_{slug_underscored}.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} records to {output_path}")

    # Write to database
    insert_player_values(df)
    print(f"Inserted {len(df)} records into database")

    print(df.head(10))


if __name__ == "__main__":
    main()
