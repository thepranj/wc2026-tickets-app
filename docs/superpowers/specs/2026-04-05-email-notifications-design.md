# Email Notifications — Design Spec

## Overview

After the daily price scrape, send an email summary to the family via Resend. The email highlights any big price movements (10%+ change) at the top, followed by a full summary table of all matches.

## Recipients

Hardcoded in the script:
- jalajsingh37@yahoo.com
- upendra_singh@yahoo.com
- pranjal.singh97@gmail.com

## Email Structure

### Subject Line

`WC2026 Tickets — Daily Price Update (Apr 5, 2026)`

With alerts: `WC2026 Tickets — 2 Price Alerts! (Apr 5, 2026)`

### Body (HTML)

**Section 1: Price Alerts (if any)**
- Shown only when one or more matches have a median price change of 10%+ (up or down) compared to the previous day's recorded price in Supabase
- Each alert shows: fixture name, yesterday's median, today's median, % change, direction arrow (up/down)
- If no matches moved 10%+, shows: "No major price movements today."

**Section 2: Full Summary Table**
- All matches in a table with columns: Fixture, Get-In Price, Median Price, Demand
- Final row: Total Portfolio Value (sum of median_price × 4 tickets for each match)

## Implementation

### New file: `send_email.py`

1. Queries Supabase `price_history` table for today's prices and yesterday's prices
2. Compares median prices per match, flags any with 10%+ change
3. Builds an HTML email with alerts section + summary table
4. Sends via Resend API (`resend` Python package) to the 3 hardcoded recipients
5. Reads `RESEND_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` from environment variables

### Modified: `.github/workflows/scrape-daily.yaml`

Add a new step after the scrape step:

```yaml
- name: Send daily email
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
    RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
  run: python send_email.py
```

Also add `resend` to the pip install step.

### Modified: `requirements.txt`

Add `resend`.

### New GitHub secret

- `RESEND_API_KEY` — Resend API key from resend.com dashboard

## Alert Threshold

A match is flagged when its median price changes 10% or more (up or down) from the previous day. The comparison is:

```
abs(today_median - yesterday_median) / yesterday_median >= 0.10
```

If there is no previous day data (e.g. first day of tracking), no alert is generated for that match.

## Edge Cases

- **First day (no yesterday data):** Email sends the full summary table with no alerts section. No comparison possible.
- **Scrape fails for a match:** That match uses fallback prices (handled by `scraper.py`). The email still includes it — it just won't show a meaningful change.
- **Resend API fails:** The GitHub Actions step will fail and show in the Actions log. The scrape data is already written to Supabase at that point, so no data loss.

## What Stays the Same

- `scrape_prices.py` — unchanged
- `scraper.py`, `matches.py` — unchanged
- `fifa_tickets.py` (Streamlit app) — unchanged
- Cron schedule — unchanged (9am ET daily)

## Resend Setup (Manual)

1. Sign up at resend.com (free tier: 100 emails/day)
2. Verify a sending domain or use their onboarding domain
3. Create an API key
4. Add `RESEND_API_KEY` as a GitHub repo secret
