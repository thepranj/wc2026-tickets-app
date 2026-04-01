import re
import requests
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="FIFA World Cup 2026 – My Tickets", page_icon="⚽", layout="wide")

# ── Password gate ─────────────────────────────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True
    st.title("⚽ FIFA World Cup 2026™")
    pw = st.text_input("Password", type="password", placeholder="Enter password to continue")
    if pw:
        if pw == st.secrets["APP_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

# ── Static match data ─────────────────────────────────────────────────────────
MATCHES = [
    {
        "Match #": 5,
        "Fixture": "Haiti vs Scotland",
        "Date": "Sat, Jun 13 2026",
        "Time": "9:00 PM ET",
        "Venue": "Boston Stadium",
        "Stage": "Group Stage",
        "Category": "Cat 2",
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
        "Stage": "Group Stage",
        "Category": "Cat 1",
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
        "Stage": "Group Stage",
        "Category": "Cat 2",
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
        "Stage": "Group Stage",
        "Category": "Cat 1",
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
        "Stage": "Round of 32",
        "Category": "Cat 1",
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
        "Stage": "Round of 16",
        "Category": "Cat 1",
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
        "Stage": "Quarter-Final",
        "Category": "Cat 2",
        "# Tickets": 4,
        "Face Value / Ticket": 890.00,
        "url": "https://seatdata.io/events/w89-vs-w90-world-cup-quarter-finals-foxborough-jul-09-2026/1126456/",
    },
]

# Fallback prices in case scraping fails
FALLBACKS = {
    5:  {"get_in": 485,  "median": 1200, "change": 6.4,  "demand": "🟡 Moderate"},
    30: {"get_in": 550,  "median": 1469, "change": 4.4,  "demand": "🔴 Low"},
    42: {"get_in": 463,  "median": 1000, "change": 0.3,  "demand": "🟡 Moderate"},
    68: {"get_in": 466,  "median": 1334, "change": 30.3, "demand": "🔴 Low"},
    74: {"get_in": 539,  "median": 1768, "change": 0.5,  "demand": "🔴 Low"},
    89: {"get_in": 816,  "median": 2500, "change": 13.0, "demand": "🔴 Low"},
    97: {"get_in": 1127, "median": 2787, "change": 0.0,  "demand": "🔴 Low"},
}

# ── Scraper (cached for 24 hours) ─────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_prices(url: str, match_id: int) -> dict:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        # Get-in price: "$ 485"
        get_in_match = re.search(r"Current Get-In Price[^$]*\$\s*([\d,]+)", text)
        get_in = int(get_in_match.group(1).replace(",", "")) if get_in_match else FALLBACKS[match_id]["get_in"]

        # 7D change: "6.4% from last week"
        change_match = re.search(r"([\d.]+)%\s*from last week", text)
        change = float(change_match.group(1)) if change_match else FALLBACKS[match_id]["change"]

        # Demand level
        if "High demand" in text:
            demand = "🟢 High"
        elif "Moderate demand" in text:
            demand = "🟡 Moderate"
        else:
            demand = "🔴 Low"

        # Median: "currently $1,200"
        median_match = re.search(r"currently \$([\d,]+)", text)
        median = int(median_match.group(1).replace(",", "")) if median_match else FALLBACKS[match_id]["median"]

        return {"get_in": get_in, "median": median, "change": change, "demand": demand}

    except Exception:
        return FALLBACKS[match_id]

# ── Fetch all prices ──────────────────────────────────────────────────────────
st.title("⚽ FIFA World Cup 2026™ — My Tickets")

with st.spinner("Fetching latest prices from seatdata.io…"):
    live_prices = {m["Match #"]: fetch_prices(m["url"], m["Match #"]) for m in MATCHES}

fetched_at = datetime.now().strftime("%-I:%M %p, %b %-d %Y")
st.caption(f"Prices from [seatdata.io](https://seatdata.io) · Auto-refreshes every 24 hrs · Last fetched {fetched_at}")

# ── Build dataframe ───────────────────────────────────────────────────────────
tickets = []
for m in MATCHES:
    p = live_prices[m["Match #"]]
    tickets.append({
        "Sell?":                    False,
        "Match #":                  m["Match #"],
        "Fixture":                  m["Fixture"],
        "Date":                     m["Date"],
        "Time":                     m["Time"],
        "Venue":                    m["Venue"],
        "Stage":                    m["Stage"],
        "Category":                 m["Category"],
        "# Tickets":                m["# Tickets"],
        "Face Value / Ticket":      m["Face Value / Ticket"],
        "Resale Get-In / Ticket":   p["get_in"],
        "Resale Median / Ticket":   p["median"],
        "7D Change":                p["change"],
        "Demand":                   p["demand"],
    })

base_df = pd.DataFrame(tickets)
base_df["Total Face Value"]      = base_df["Face Value / Ticket"] * base_df["# Tickets"]
base_df["Total Resale (Median)"] = base_df["Resale Median / Ticket"] * base_df["# Tickets"]
base_df["Profit at Median"]      = base_df["Total Resale (Median)"] - base_df["Total Face Value"]

total_spent = base_df["Total Face Value"].sum()

# ── Editable table with Sell? checkboxes ─────────────────────────────────────
st.subheader("My Tickets — Check games you want to sell")

edited = st.data_editor(
    base_df[[
        "Sell?", "Match #", "Fixture", "Date", "Time", "Venue", "Stage", "Category",
        "# Tickets", "Face Value / Ticket", "Resale Get-In / Ticket",
        "Resale Median / Ticket", "Profit at Median", "7D Change", "Demand",
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Sell?":                    st.column_config.CheckboxColumn("Sell?", width="small"),
        "Match #":                  st.column_config.NumberColumn(width="small"),
        "Time":                     st.column_config.TextColumn("Kick-off", width="small"),
        "# Tickets":                st.column_config.NumberColumn(width="small"),
        "Face Value / Ticket":      st.column_config.NumberColumn(format="$%d"),
        "Resale Get-In / Ticket":   st.column_config.NumberColumn(format="$%d"),
        "Resale Median / Ticket":   st.column_config.NumberColumn(format="$%d"),
        "Profit at Median":         st.column_config.NumberColumn(format="$%d"),
        "7D Change":                st.column_config.NumberColumn("7D Change", format="%.1f%%", width="small"),
        "Demand":                   st.column_config.TextColumn("Demand", width="small"),
    },
    disabled=[c for c in base_df.columns if c != "Sell?"],
)

# ── Derive sell/keep splits ───────────────────────────────────────────────────
base_df["Sell?"] = edited["Sell?"].values

sell_df = base_df[base_df["Sell?"] == True].copy()
keep_df = base_df[base_df["Sell?"] == False].copy()

sell_revenue      = sell_df["Total Resale (Median)"].sum()
sell_revenue_fees = sell_revenue * 0.85
sell_face         = sell_df["Total Face Value"].sum()
sell_net          = sell_revenue_fees - sell_face
tickets_selling   = int(sell_df["# Tickets"].sum())
tickets_attending = int(keep_df["# Tickets"].sum())

st.divider()

# ── Summary metrics ───────────────────────────────────────────────────────────
st.subheader("Summary")
c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Tickets Attending",  tickets_attending)
c2.metric("Tickets Selling",    tickets_selling)
c3.metric("Total Spent",        f"${total_spent:,.0f}")
c4.metric("Expected from Sales",
          f"${sell_revenue:,.0f}" if tickets_selling else "—",
          delta=f"+${sell_revenue - sell_face:,.0f} gross" if tickets_selling else None)
c5.metric("After 15% Fees",
          f"${sell_revenue_fees:,.0f}" if tickets_selling else "—",
          delta=f"+${sell_net:,.0f} net" if tickets_selling else None)
c6.metric("Net ROI (after fees)",
          f"{sell_net / total_spent * 100:.0f}%" if tickets_selling else "—")

# ── Sell vs Keep breakdown ────────────────────────────────────────────────────
if tickets_selling > 0:
    st.divider()
    col_sell, col_keep = st.columns(2)

    with col_sell:
        st.markdown("##### 🟢 Selling")
        sell_summary = sell_df[["Fixture", "Date", "Total Resale (Median)", "Profit at Median"]].copy()
        sell_summary.rename(columns={
            "Total Resale (Median)": "Revenue (gross)",
            "Profit at Median":      "Profit (gross)",
        }, inplace=True)
        sell_summary["Revenue (net, -15%)"] = (sell_summary["Revenue (gross)"] * 0.85).map("${:,.0f}".format)
        sell_summary["Revenue (gross)"]     = sell_summary["Revenue (gross)"].map("${:,.0f}".format)
        sell_summary["Profit (gross)"]      = sell_summary["Profit (gross)"].map("${:,.0f}".format)
        st.dataframe(sell_summary, use_container_width=True, hide_index=True)

    with col_keep:
        st.markdown("##### 🎟️ Attending")
        keep_summary = keep_df[["Fixture", "Date", "Venue", "Stage"]].copy()
        if keep_summary.empty:
            st.info("No games selected to attend.")
        else:
            st.dataframe(keep_summary, use_container_width=True, hide_index=True)

# ── Profit bar chart ──────────────────────────────────────────────────────────
if tickets_selling > 0:
    st.divider()
    st.subheader("Profit by Game Being Sold (at Median Resale)")
    chart_df = sell_df[["Fixture", "Profit at Median"]].set_index("Fixture")
    st.bar_chart(chart_df)
