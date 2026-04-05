# scrape_prices.py — Daily price scraper for GitHub Actions
# Scrapes resale prices for all matches and upserts to Supabase.

import os
from datetime import date

from supabase import create_client

from matches import MATCHES
from scraper import fetch_prices_raw


def main():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    sb = create_client(url, key)

    today = date.today().isoformat()
    print(f"Scraping prices for {len(MATCHES)} matches on {today}...")

    for m in MATCHES:
        match_id = m["Match #"]
        fixture = m["Fixture"]
        print(f"  Match #{match_id}: {fixture}...", end=" ")

        prices = fetch_prices_raw(m["url"], match_id, m["Tier"])

        row = {
            "match_id": match_id,
            "fixture": fixture,
            "date": today,
            "get_in_price": prices["get_in"],
            "median_price": prices["median"],
            "comp_seat_price": prices["comp_price"],
            "demand": prices["demand"],
            "change_7d": prices["change"],
        }

        sb.table("price_history").upsert(row, on_conflict="match_id,date").execute()
        print(f"get_in=${prices['get_in']}, median=${prices['median']}, demand={prices['demand']}")

    print("Done.")


if __name__ == "__main__":
    main()
