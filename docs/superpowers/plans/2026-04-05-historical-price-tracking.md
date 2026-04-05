# Historical Price Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent daily price tracking via Supabase + GitHub Actions, with historical charts in the Streamlit app.

**Architecture:** A shared `matches.py` holds match data. A shared `scraper.py` holds the scraping function. `scrape_prices.py` is the GitHub Actions entry point that scrapes and writes to Supabase daily. The Streamlit app reads history from Supabase for two chart views (total portfolio + per-match with dropdown filter).

**Tech Stack:** Python 3.11, Streamlit, Supabase (Postgres via `supabase-py`), GitHub Actions, BeautifulSoup4, pandas

---

## File Structure

```
matches.py                               # new: MATCHES, FALLBACKS, TIER_TO_SECTION extracted from fifa_tickets.py
scraper.py                               # new: fetch_prices_raw() extracted from fifa_tickets.py
scrape_prices.py                         # new: GitHub Actions entry point — scrape + upsert to Supabase
fifa_tickets.py                          # modified: import from matches.py/scraper.py, read history from Supabase, new charts
requirements.txt                         # modified: add supabase
.github/workflows/scrape-daily.yaml      # new: daily cron workflow
```

---

### Task 1: Extract shared match data into `matches.py`

**Files:**
- Create: `matches.py`
- Modify: `fifa_tickets.py`

- [ ] **Step 1: Create `matches.py` with extracted data**

```python
# matches.py — Shared match data for the WC2026 ticket tracker

MATCHES = [
    {
        "Match #": 5,
        "Fixture": "Haiti vs Scotland",
        "Date": "Sat, Jun 13 2026",
        "Time": "9:00 PM ET",
        "Venue": "Boston Stadium",
        "Venue Map": "https://www.stadiumsportus.com/stadiums/gillette-stadium/seating-map",
        "Stage": "Group Stage",
        "Category": "Cat 2",
        "Seats": "Block 224, Row 6, Seats 7–10",
        "Tier": "Middle Tier",
        "# Tickets": 4,
        "Face Value / Ticket": 400.00,
        "url": "https://seatdata.io/events/haiti-vs-scotland-world-cup-group-c-foxborough-jun-13-2026/1126436/",
    },
    {
        "Match #": 30,
        "Fixture": "Scotland vs Morocco",
        "Date": "Fri, Jun 19 2026",
        "Time": "6:00 PM ET",
        "Venue": "Boston Stadium",
        "Venue Map": "https://www.stadiumsportus.com/stadiums/gillette-stadium/seating-map",
        "Stage": "Group Stage",
        "Category": "Cat 1",
        "Seats": "Block 137, Row 2, Seats 7–10",
        "Tier": "Lower Tier",
        "# Tickets": 4,
        "Face Value / Ticket": 600.00,
        "url": "https://seatdata.io/events/scotland-vs-morocco-world-cup-group-c-foxborough-jun-19-2026/1126446/",
    },
    {
        "Match #": 42,
        "Fixture": "France vs Iraq",
        "Date": "Mon, Jun 22 2026",
        "Time": "5:00 PM ET",
        "Venue": "Philadelphia Stadium",
        "Venue Map": "https://www.stadiumsportus.com/stadiums/lincoln-financial-field/seating-map?map=23",
        "Stage": "Group Stage",
        "Category": "Cat 2",
        "Seats": "Block 225, Row 27, Seats 17–20",
        "Tier": "Upper Tier",
        "# Tickets": 4,
        "Face Value / Ticket": 430.00,
        "url": "https://seatdata.io/events/france-vs-tbd-world-cup-group-i-philadelphia-jun-22-2026/1126440/",
    },
    {
        "Match #": 68,
        "Fixture": "Croatia vs Ghana",
        "Date": "Sat, Jun 27 2026",
        "Time": "5:00 PM ET",
        "Venue": "Philadelphia Stadium",
        "Venue Map": "https://www.stadiumsportus.com/stadiums/lincoln-financial-field/seating-map?map=23",
        "Stage": "Group Stage",
        "Category": "Cat 1",
        "Seats": "Block 131, Row 19, Seats 9–12",
        "Tier": "Lower Tier",
        "# Tickets": 4,
        "Face Value / Ticket": 500.00,
        "url": "https://seatdata.io/events/croatia-vs-ghana-world-cup-group-l-philadelphia-jun-27-2026/1126430/",
    },
    {
        "Match #": 74,
        "Fixture": "1E vs 3A/B/C/D/F",
        "Date": "Mon, Jun 29 2026",
        "Time": "4:30 PM ET",
        "Venue": "Boston Stadium",
        "Venue Map": "https://www.stadiumsportus.com/stadiums/gillette-stadium/seating-map",
        "Stage": "Round of 32",
        "Category": "Cat 1",
        "Seats": "Block 141, Row 24, Seats 13–16",
        "Tier": "Lower Tier",
        "# Tickets": 4,
        "Face Value / Ticket": 620.00,
        "url": "https://seatdata.io/events/1e-vs-3abcdf-world-cup-round-of-32-foxborough-jun-29-2026/1126437/",
    },
    {
        "Match #": 89,
        "Fixture": "Winner M74 vs Winner M77",
        "Date": "Sat, Jul 04 2026",
        "Time": "5:00 PM ET",
        "Venue": "Philadelphia Stadium",
        "Venue Map": "https://www.stadiumsportus.com/stadiums/lincoln-financial-field/seating-map?map=23",
        "Stage": "Round of 16",
        "Category": "Cat 1",
        "Seats": "Block 107, Row 13, Seats 13–16",
        "Tier": "Lower Tier",
        "# Tickets": 4,
        "Face Value / Ticket": 840.00,
        "url": "https://seatdata.io/events/w74-vs-w77-world-cup-round-of-16-philadelphia-jul-04-2026/1126431/",
    },
    {
        "Match #": 97,
        "Fixture": "Winner M89 vs Winner M90",
        "Date": "Thu, Jul 09 2026",
        "Time": "4:00 PM ET",
        "Venue": "Boston Stadium",
        "Venue Map": "https://www.stadiumsportus.com/stadiums/gillette-stadium/seating-map",
        "Stage": "Quarter-Final",
        "Category": "Cat 2",
        "Seats": "Block 334, Row 13, Seats 21–24",
        "Tier": "Upper Tier",
        "# Tickets": 4,
        "Face Value / Ticket": 890.00,
        "url": "https://seatdata.io/events/w89-vs-w90-world-cup-quarter-finals-foxborough-jul-09-2026/1126456/",
    },
]

FALLBACKS = {
    5:  {"get_in": 485,  "median": 1200, "change": 6.4,  "demand": "🟡 Moderate"},
    30: {"get_in": 550,  "median": 1469, "change": 4.4,  "demand": "🔴 Low"},
    42: {"get_in": 463,  "median": 1000, "change": 0.3,  "demand": "🟡 Moderate"},
    68: {"get_in": 466,  "median": 1334, "change": 30.3, "demand": "🔴 Low"},
    74: {"get_in": 539,  "median": 1768, "change": 0.5,  "demand": "🔴 Low"},
    89: {"get_in": 816,  "median": 2500, "change": 13.0, "demand": "🔴 Low"},
    97: {"get_in": 1127, "median": 2787, "change": 0.0,  "demand": "🔴 Low"},
}

TIER_TO_SECTION = {
    "Lower Tier": "Lower Bowl",
    "Upper Tier": "Upper Bowl",
    "Middle Tier": "Club Level",
}
```

- [ ] **Step 2: Update `fifa_tickets.py` — replace inline data with imports**

Remove the `MATCHES = [...]`, `FALLBACKS = {…}`, and `TIER_TO_SECTION = {…}` blocks (lines 28–152) and replace with:

```python
from matches import MATCHES, FALLBACKS, TIER_TO_SECTION
```

This import goes after the existing standard library / third-party imports (after line 6).

- [ ] **Step 3: Verify the app still runs**

Run: `cd /Users/jalaj.singh/Downloads/wc2026-tickets-app && python -c "from matches import MATCHES, FALLBACKS, TIER_TO_SECTION; print(f'{len(MATCHES)} matches loaded')"`

Expected: `7 matches loaded`

- [ ] **Step 4: Commit**

```bash
git add matches.py fifa_tickets.py
git commit -m "refactor: extract shared match data into matches.py"
```

---

### Task 2: Extract scraping logic into `scraper.py`

**Files:**
- Create: `scraper.py`
- Modify: `fifa_tickets.py`

- [ ] **Step 1: Create `scraper.py` with the shared scraping function**

Extract the scraping logic from `fifa_tickets.py` (the `fetch_prices` function, lines 154–203) into a plain function that doesn't depend on Streamlit:

```python
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
```

- [ ] **Step 2: Update `fifa_tickets.py` — use `scraper.py` instead of inline function**

Remove the `fetch_prices` function and its `@st.cache_data` decorator (lines 154–203). Replace the `TIER_TO_SECTION` import if not done already. The Streamlit app still needs caching, so wrap the imported function:

Replace the old `@st.cache_data` function block with:

```python
from scraper import fetch_prices_raw

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_prices(url: str, match_id: int, tier: str) -> dict:
    return fetch_prices_raw(url, match_id, tier)
```

This keeps the Streamlit caching behavior while delegating to the shared function.

- [ ] **Step 3: Verify the scraper module loads**

Run: `cd /Users/jalaj.singh/Downloads/wc2026-tickets-app && python -c "from scraper import fetch_prices_raw; print('scraper loaded OK')"`

Expected: `scraper loaded OK`

- [ ] **Step 4: Commit**

```bash
git add scraper.py fifa_tickets.py
git commit -m "refactor: extract scraping logic into scraper.py"
```

---

### Task 3: Create the Supabase table

**Files:** None (database setup via Supabase dashboard)

- [ ] **Step 1: Create the `price_history` table in Supabase**

Go to the Supabase dashboard → SQL Editor and run:

```sql
CREATE TABLE price_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id INT NOT NULL,
    fixture TEXT NOT NULL,
    date DATE NOT NULL,
    get_in_price INT NOT NULL,
    median_price INT NOT NULL,
    comp_seat_price INT,
    demand TEXT NOT NULL,
    change_7d DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (match_id, date)
);
```

- [ ] **Step 2: Verify the table exists**

In the Supabase dashboard → Table Editor, confirm `price_history` appears with the correct columns.

- [ ] **Step 3: Note the Supabase project URL and anon key**

From Supabase dashboard → Settings → API:
- Copy `Project URL` (looks like `https://xxxxx.supabase.co`)
- Copy `anon` / `public` key

You'll need these for the next tasks.

---

### Task 4: Create the GitHub Actions scraper script

**Files:**
- Create: `scrape_prices.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Update `requirements.txt`**

```
streamlit
pandas
requests
beautifulsoup4
supabase
```

- [ ] **Step 2: Create `scrape_prices.py`**

```python
# scrape_prices.py — Daily price scraper for GitHub Actions
# Scrapes resale prices for all matches and upserts to Supabase.

import os
from datetime import date, timezone

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
```

- [ ] **Step 3: Verify the script loads (without running against Supabase)**

Run: `cd /Users/jalaj.singh/Downloads/wc2026-tickets-app && python -c "import scrape_prices; print('script loaded OK')"`

Expected: `script loaded OK`

- [ ] **Step 4: Commit**

```bash
git add scrape_prices.py requirements.txt
git commit -m "feat: add daily price scraper for GitHub Actions + Supabase"
```

---

### Task 5: Create the GitHub Actions workflow

**Files:**
- Create: `.github/workflows/scrape-daily.yaml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Daily Price Scrape

on:
  schedule:
    # 9 AM ET = 1 PM UTC
    - cron: "0 13 * * *"
  workflow_dispatch: # allow manual runs from GitHub UI

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install requests beautifulsoup4 supabase

      - name: Scrape and store prices
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: python scrape_prices.py
```

Note: we only install the packages the scraper needs (not streamlit/pandas — the Actions job doesn't run the app).

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/scrape-daily.yaml
git commit -m "ci: add daily cron workflow for price scraping"
```

---

### Task 6: Add GitHub repo secrets

**Files:** None (GitHub UI)

- [ ] **Step 1: Add secrets to the GitHub repo**

Go to the repo on GitHub → Settings → Secrets and variables → Actions → New repository secret:

- Name: `SUPABASE_URL`, Value: your Supabase project URL
- Name: `SUPABASE_KEY`, Value: your Supabase anon key

- [ ] **Step 2: Push all commits to GitHub**

```bash
git push origin main
```

- [ ] **Step 3: Trigger a manual run to verify**

Go to repo → Actions → "Daily Price Scrape" → "Run workflow" → Run.

Watch the logs. Expected: the job completes successfully, printing scraped prices for all 7 matches.

- [ ] **Step 4: Verify data landed in Supabase**

In the Supabase dashboard → Table Editor → `price_history`, confirm 7 rows exist for today's date.

---

### Task 7: Update Streamlit app to show historical charts from Supabase

**Files:**
- Modify: `fifa_tickets.py`

- [ ] **Step 1: Add Supabase client initialization**

At the top of `fifa_tickets.py`, after the existing imports and the `from matches import ...` line, add:

```python
from supabase import create_client

@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
```

- [ ] **Step 2: Replace hardcoded HISTORY with Supabase query**

Remove the entire hardcoded `HISTORY` block and the old line chart (everything from the `# ── Historical tracking` comment to the end of the file, lines 337–358). Replace with:

```python
# ── Historical charts (from Supabase) ────────────────────────────────────────

sb = get_supabase()
history_resp = sb.table("price_history").select("*").order("date").execute()
history_data = history_resp.data

if history_data:
    hist_df = pd.DataFrame(history_data)
    hist_df["date"] = pd.to_datetime(hist_df["date"])

    # Chart 1: Total portfolio value over time
    st.divider()
    st.subheader("Total Portfolio Value Over Time")

    # Each match has 4 tickets
    tickets_per_match = {m["Match #"]: m["# Tickets"] for m in MATCHES}
    hist_df["total_value"] = hist_df.apply(
        lambda r: r["median_price"] * tickets_per_match.get(r["match_id"], 4), axis=1
    )
    portfolio_df = hist_df.groupby("date")["total_value"].sum().reset_index()
    portfolio_df = portfolio_df.set_index("date")
    st.line_chart(portfolio_df, y="total_value", y_label="Total Value ($)", x_label="Date")

    # Chart 2: Per-match price trends with dropdown
    st.divider()
    st.subheader("Per-Match Price Trends")

    fixtures = ["All matches"] + sorted(hist_df["fixture"].unique().tolist())
    selected = st.selectbox("Filter by match", fixtures)

    if selected == "All matches":
        pivot = hist_df.pivot_table(index="date", columns="fixture", values="median_price")
        st.line_chart(pivot)
    else:
        match_df = hist_df[hist_df["fixture"] == selected][["date", "median_price"]].set_index("date")
        st.line_chart(match_df, y="median_price", y_label="Median Price ($)", x_label="Date")
else:
    st.info("No historical price data yet. Data will appear after the first daily scrape runs.")
```

- [ ] **Step 3: Add Supabase secrets to Streamlit**

In the Streamlit Cloud dashboard → App settings → Secrets, add:

```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "your-anon-key-here"
```

(The existing `APP_PASSWORD` secret stays.)

- [ ] **Step 4: Commit**

```bash
git add fifa_tickets.py
git commit -m "feat: add historical price charts from Supabase"
```

- [ ] **Step 5: Push and verify on Streamlit Cloud**

```bash
git push origin main
```

Open the deployed app. Scroll to the bottom. You should see:
- "Total Portfolio Value Over Time" line chart
- "Per-Match Price Trends" with a dropdown defaulting to "All matches"

If the daily scrape hasn't run yet, you'll see the "No historical price data yet" info message.
