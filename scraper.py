# scraper.py — Shared price scraping logic

import re
import requests
from bs4 import BeautifulSoup
from matches import FALLBACKS, TIER_TO_SECTION


def fetch_prices_raw(url: str, match_id: int, tier: str) -> dict:
    """Scrape resale prices from seatdata.io for a single match.

    Returns dict with keys: get_in, median, change, demand, comp_price.
    Falls back to FALLBACKS on any error.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        # Get-in price
        get_in_match = re.search(r"Current Get-In Price[^$]*\$\s*([\d,]+)", text)
        get_in = int(get_in_match.group(1).replace(",", "")) if get_in_match else FALLBACKS[match_id]["get_in"]

        # 7D change
        change_match = re.search(r"([\d.]+)%\s*from last week", text)
        change = float(change_match.group(1)) if change_match else FALLBACKS[match_id]["change"]

        # Demand
        if "High demand" in text:
            demand = "🟢 High"
        elif "Moderate demand" in text:
            demand = "🟡 Moderate"
        else:
            demand = "🔴 Low"

        # Median
        median_match = re.search(r"currently \$([\d,]+)", text)
        median = int(median_match.group(1).replace(",", "")) if median_match else FALLBACKS[match_id]["median"]

        # Section breakdown — find the table rows
        target_section = TIER_TO_SECTION.get(tier, "Lower Bowl")
        comp_price = None
        rows = soup.find_all("tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) >= 2 and target_section in cells[0]:
                price_match = re.search(r"\$([\d,]+)", cells[1])
                if price_match:
                    comp_price = int(price_match.group(1).replace(",", ""))
                break

        return {
            "get_in": get_in,
            "median": median,
            "change": change,
            "demand": demand,
            "comp_price": comp_price,
        }

    except Exception:
        return {**FALLBACKS[match_id], "comp_price": None}
