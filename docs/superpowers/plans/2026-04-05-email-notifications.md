# Email Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send a daily email to the family after the price scrape with a summary of all prices and alerts for any 10%+ price movements.

**Architecture:** A new `send_email.py` script queries Supabase for today's and yesterday's prices, builds an HTML email with alerts + summary table, and sends via Resend. The existing GitHub Actions workflow gets a new step to run it after the scrape.

**Tech Stack:** Python 3.11, Resend (`resend` package), Supabase (`supabase-py`), GitHub Actions

---

## File Structure

```
send_email.py                            # new: queries Supabase, builds HTML email, sends via Resend
requirements.txt                         # modified: add resend
.github/workflows/scrape-daily.yaml      # modified: add email step after scrape
```

---

### Task 1: Create `send_email.py`

**Files:**
- Create: `send_email.py`

- [ ] **Step 1: Create `send_email.py`**

```python
# send_email.py — Daily email summary after price scrape
# Sends to the family via Resend with price alerts + full summary.

import os
from datetime import date, timedelta

import resend
from supabase import create_client

from matches import MATCHES

RECIPIENTS = [
    "jalajsingh37@yahoo.com",
    "upendra_singh@yahoo.com",
    "pranjal.singh97@gmail.com",
]

ALERT_THRESHOLD = 0.10  # 10% change triggers an alert


def get_prices(sb, target_date):
    """Fetch all price_history rows for a given date."""
    resp = (
        sb.table("price_history")
        .select("*")
        .eq("date", target_date.isoformat())
        .execute()
    )
    return {row["match_id"]: row for row in resp.data}


def build_alerts(today_prices, yesterday_prices):
    """Compare today vs yesterday, return list of alert dicts for 10%+ moves."""
    alerts = []
    for match_id, today in today_prices.items():
        yesterday = yesterday_prices.get(match_id)
        if not yesterday:
            continue
        old_median = yesterday["median_price"]
        new_median = today["median_price"]
        if old_median == 0:
            continue
        pct_change = (new_median - old_median) / old_median
        if abs(pct_change) >= ALERT_THRESHOLD:
            alerts.append({
                "fixture": today["fixture"],
                "old_median": old_median,
                "new_median": new_median,
                "pct_change": pct_change,
            })
    return alerts


def build_html(today_prices, alerts, today_date):
    """Build the HTML email body."""
    tickets_per_match = {m["Match #"]: m["# Tickets"] for m in MATCHES}

    # Alerts section
    if alerts:
        alerts_html = "<h2 style='color:#d32f2f;'>&#9888; Price Alerts</h2><table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;width:100%;'>"
        alerts_html += "<tr style='background:#f5f5f5;'><th>Match</th><th>Yesterday</th><th>Today</th><th>Change</th></tr>"
        for a in alerts:
            direction = "&#9650;" if a["pct_change"] > 0 else "&#9660;"
            color = "#2e7d32" if a["pct_change"] > 0 else "#d32f2f"
            alerts_html += (
                f"<tr>"
                f"<td>{a['fixture']}</td>"
                f"<td>${a['old_median']:,}</td>"
                f"<td>${a['new_median']:,}</td>"
                f"<td style='color:{color};font-weight:bold;'>{direction} {abs(a['pct_change']):.1%}</td>"
                f"</tr>"
            )
        alerts_html += "</table>"
    else:
        alerts_html = "<p style='color:#666;'>No major price movements today.</p>"

    # Summary table
    summary_html = "<h2>&#9917; Full Summary</h2><table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;width:100%;'>"
    summary_html += "<tr style='background:#f5f5f5;'><th>Match</th><th>Get-In</th><th>Median</th><th>Demand</th></tr>"

    total_portfolio = 0
    for m in MATCHES:
        match_id = m["Match #"]
        p = today_prices.get(match_id)
        if not p:
            continue
        num_tickets = tickets_per_match.get(match_id, 4)
        total_portfolio += p["median_price"] * num_tickets
        summary_html += (
            f"<tr>"
            f"<td>{p['fixture']}</td>"
            f"<td>${p['get_in_price']:,}</td>"
            f"<td>${p['median_price']:,}</td>"
            f"<td>{p['demand']}</td>"
            f"</tr>"
        )

    summary_html += (
        f"<tr style='background:#e3f2fd;font-weight:bold;'>"
        f"<td>Total Portfolio Value</td>"
        f"<td colspan='3'>${total_portfolio:,}</td>"
        f"</tr>"
    )
    summary_html += "</table>"

    html = (
        f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
        f"<h1>&#9917; WC2026 Tickets — {today_date.strftime('%b %-d, %Y')}</h1>"
        f"{alerts_html}"
        f"<br>"
        f"{summary_html}"
        f"<br>"
        f"<p style='color:#999;font-size:12px;'>Prices from seatdata.io. Scraped daily at 9 AM ET.</p>"
        f"</div>"
    )
    return html


def main():
    resend.api_key = os.environ["RESEND_API_KEY"]
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    today_date = date.today()
    yesterday_date = today_date - timedelta(days=1)

    today_prices = get_prices(sb, today_date)

    if not today_prices:
        print("No price data for today. Skipping email.")
        return

    yesterday_prices = get_prices(sb, yesterday_date)
    alerts = build_alerts(today_prices, yesterday_prices)

    num_alerts = len(alerts)
    if num_alerts > 0:
        subject = f"WC2026 Tickets — {num_alerts} Price Alert{'s' if num_alerts != 1 else ''}! ({today_date.strftime('%b %-d, %Y')})"
    else:
        subject = f"WC2026 Tickets — Daily Price Update ({today_date.strftime('%b %-d, %Y')})"

    html = build_html(today_prices, alerts, today_date)

    print(f"Sending email to {len(RECIPIENTS)} recipients...")
    print(f"Subject: {subject}")
    print(f"Alerts: {num_alerts}")

    resend.Emails.send({
        "from": "WC2026 Tickets <onboarding@resend.dev>",
        "to": RECIPIENTS,
        "subject": subject,
        "html": html,
    })

    print("Email sent.")


if __name__ == "__main__":
    main()
```

Note on the `from` field: `onboarding@resend.dev` is Resend's default sandbox sender. If a custom domain is verified in Resend, update this to use that domain instead (e.g. `tickets@yourdomain.com`).

- [ ] **Step 2: Verify the script loads**

Run: `cd /Users/jalaj.singh/Downloads/wc2026-tickets-app && python -c "import send_email; print('send_email loaded OK')"`

Expected: `send_email loaded OK` (requires `resend` and `supabase` packages installed)

- [ ] **Step 3: Commit**

```bash
git add send_email.py
git commit -m "feat: add daily email summary with price alerts via Resend"
```

---

### Task 2: Update `requirements.txt`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add `resend` to requirements.txt**

The file currently contains:

```
streamlit
pandas
requests
beautifulsoup4
supabase
```

Add `resend` at the end:

```
streamlit
pandas
requests
beautifulsoup4
supabase
resend
```

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "deps: add resend package for email notifications"
```

---

### Task 3: Update GitHub Actions workflow

**Files:**
- Modify: `.github/workflows/scrape-daily.yaml`

- [ ] **Step 1: Add resend to pip install and add email step**

The workflow currently looks like:

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

Replace the entire file with:

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
        run: pip install requests beautifulsoup4 supabase resend

      - name: Scrape and store prices
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: python scrape_prices.py

      - name: Send daily email
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
        run: python send_email.py
```

Changes:
1. Added `resend` to the pip install step
2. Added a new "Send daily email" step after the scrape that runs `send_email.py` with the three required env vars

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/scrape-daily.yaml
git commit -m "ci: add email notification step to daily scrape workflow"
```

---

### Task 4: Add `RESEND_API_KEY` GitHub secret (manual)

**Files:** None (GitHub UI)

- [ ] **Step 1: Create a Resend account and API key**

1. Sign up at https://resend.com (free tier: 100 emails/day)
2. Go to API Keys → Create API Key
3. Copy the key

- [ ] **Step 2: Add the secret to GitHub**

Go to the repo → Settings → Secrets and variables → Actions → New repository secret:
- Name: `RESEND_API_KEY`
- Value: the API key from step 1

- [ ] **Step 3: Push all commits and trigger a manual run**

```bash
git push origin main
```

Go to repo → Actions → "Daily Price Scrape" → "Run workflow" → Run.

Watch the logs. Expected: scrape completes, then email step completes with output like:
```
Sending email to 3 recipients...
Subject: WC2026 Tickets — Daily Price Update (Apr 5, 2026)
Alerts: 0
Email sent.
```

- [ ] **Step 4: Verify email received**

Check the inboxes for jalajsingh37@yahoo.com, upendra_singh@yahoo.com, and pranjal.singh97@gmail.com. You should see the daily summary email.

Note: If using Resend's sandbox domain (`onboarding@resend.dev`), emails can only be sent to the email address that signed up for Resend. To send to all 3 recipients, verify a custom domain in Resend (Resend dashboard → Domains → Add Domain).
