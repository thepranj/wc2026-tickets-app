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
