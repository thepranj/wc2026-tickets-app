# Historical Price Tracking — Design Spec

## Overview

Add persistent historical price tracking to the WC2026 ticket tracker app. A daily GitHub Actions cron job scrapes resale prices and stores them in Supabase (Postgres). The Streamlit app reads from Supabase to display historical charts.

## Motivation

The app currently hardcodes a `HISTORY` dataframe with manually entered values. This doesn't scale and creates gaps. Automated daily scraping + a real database gives the family a complete picture of how ticket values are trending over time.

## Tech Decisions

- **Database:** Supabase (free tier Postgres). Chosen because the app is deployed on Streamlit Community Cloud, which has an ephemeral filesystem — SQLite wouldn't persist. Supabase is free, standard Postgres, and works well with Streamlit's secrets management.
- **Scheduled job:** GitHub Actions cron. Free (2,000 min/month, this uses ~15 min/month), no extra accounts, lives in the same repo.
- **Python SDK:** `supabase-py` for DB writes/reads.

## Database Schema

### Table: `price_history`

| Column           | Type            | Notes                                      |
|------------------|-----------------|--------------------------------------------|
| `id`             | bigint (auto)   | Primary key                                |
| `match_id`       | int             | Matches the `Match #` from MATCHES list    |
| `fixture`        | text            | e.g. "Haiti vs Scotland"                   |
| `date`           | date            | Day the price was recorded                 |
| `get_in_price`   | int             | Cheapest available ticket                  |
| `median_price`   | int             | Median resale price                        |
| `comp_seat_price`| int (nullable)  | Comparable section average                 |
| `demand`         | text            | "High", "Moderate", or "Low"               |
| `change_7d`      | float           | 7-day percentage change                    |
| `created_at`     | timestamptz     | Auto-set on insert                         |

**Unique constraint** on `(match_id, date)` — upsert semantics so duplicate runs in a day don't create duplicate rows.

**Scale:** ~8 rows/day, ~2,800 rows/year. Trivial for Supabase free tier.

## File Structure Changes

```
fifa_tickets.py                          # modified: imports from matches.py + scraper.py, reads history from Supabase
matches.py                               # new: shared MATCHES list + FALLBACKS + TIER_TO_SECTION
scraper.py                               # new: shared fetch_prices_raw() function (extracted from fifa_tickets.py)
scrape_prices.py                         # new: standalone entry point for GitHub Actions
requirements.txt                         # updated: add supabase
.github/workflows/scrape-daily.yaml      # new: daily cron workflow
```

### matches.py

Extracted from `fifa_tickets.py`:
- `MATCHES` list (all 7 match dicts with fixture, date, venue, seats, URLs, etc.)
- `FALLBACKS` dict
- `TIER_TO_SECTION` mapping

Both `fifa_tickets.py` and `scrape_prices.py` import from here.

### scrape_prices.py

Standalone script that:
1. Imports `MATCHES`, `FALLBACKS`, `TIER_TO_SECTION` from `matches.py`
2. Imports `fetch_prices_raw()` from `scraper.py` (shared scraping logic extracted from `fifa_tickets.py`)
3. Loops through each match, scrapes seatdata.io
4. Upserts results into Supabase `price_history` table
5. Reads `SUPABASE_URL` and `SUPABASE_KEY` from environment variables

### .github/workflows/scrape-daily.yaml

- **Schedule:** `cron: '0 13 * * *'` (9am ET / 1pm UTC)
- **Manual trigger:** `workflow_dispatch` so it can be run on demand from GitHub UI
- **Steps:** checkout repo, install Python 3.11, install dependencies, run `scrape_prices.py`
- **Secrets:** `SUPABASE_URL` and `SUPABASE_KEY` stored as GitHub repo secrets, passed as env vars

### fifa_tickets.py changes

1. Import `MATCHES`, `FALLBACKS`, `TIER_TO_SECTION` from `matches.py` instead of defining them inline
2. Add Supabase client initialization using Streamlit secrets (`st.secrets["SUPABASE_URL"]`, `st.secrets["SUPABASE_KEY"]`)
3. Replace the hardcoded `HISTORY` dataframe with a query to `price_history`
4. Replace the existing single history chart with two new sections:

**Chart 1: Total Portfolio Value Over Time**
- Query: sum of `median_price * 4` (tickets per match) grouped by `date`
- Line chart, replaces the existing hardcoded `HISTORY` chart

**Chart 2: Per-Match Price Trends**
- Dropdown (`st.selectbox`) to pick a specific match by fixture name, defaulting to "All matches"
- When "All matches" selected: multi-line chart with one line per fixture showing median price over time
- When a specific match selected: single line chart for that match's median price over time

### requirements.txt

Add `supabase` (which pulls in `postgrest-py`, `httpx`, etc.)

## Secrets / Config

### GitHub repo secrets (for Actions)
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — Supabase anon/service key

### Streamlit secrets (for the app)
- `SUPABASE_URL` — same URL
- `SUPABASE_KEY` — same key
- `APP_PASSWORD` — already exists

## What Stays the Same

- The live price scraping on app visit (cached 24hrs) — unchanged
- The editable ticket table with sell/keep checkboxes — unchanged
- The financial summary metrics — unchanged
- The profit bar chart — unchanged
- Password gate — unchanged

## Future Extension Points

- Email summary: the GitHub Actions job could be extended to send a daily email digest after scraping (e.g. via SendGrid, Resend, or even Gmail SMTP)
- Alerts: price drop/spike notifications
- More matches: just add entries to `MATCHES` in `matches.py`
