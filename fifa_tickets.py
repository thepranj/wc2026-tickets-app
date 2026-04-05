import re
import requests
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from matches import MATCHES, FALLBACKS, TIER_TO_SECTION

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


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_prices(url: str, match_id: int, tier: str) -> dict:
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

# ── Fetch all prices ──────────────────────────────────────────────────────────
st.title("⚽ FIFA World Cup 2026™ — My Tickets")

with st.spinner("Fetching latest prices from seatdata.io…"):
    # Fetch all prices — pass tier now
    live_prices = {m["Match #"]: fetch_prices(m["url"], m["Match #"], m["Tier"]) for m in MATCHES}

fetched_at = datetime.now().strftime("%-I:%M %p, %b %-d %Y")
st.caption(f"Prices from [seatdata.io](https://seatdata.io) · Auto-refreshes every 24 hrs · Last fetched {fetched_at}")

# ── Build dataframe ───────────────────────────────────────────────────────────
tickets = []
for m in MATCHES:
    p = live_prices[m["Match #"]]
    tickets.append({
        "Sell?":                    True,
        "Match #":                  m["Match #"],
        "Fixture":                  m["Fixture"],
        "Date":                     m["Date"],
        "Time":                     m["Time"],
        "Venue":                    m["Venue"],
        "Venue Map":                m["Venue Map"],
        "Stage":                    m["Stage"],
        "Category":                 m["Category"],
        "Seats" :                   m["Seats"],
        "# Tickets":                m["# Tickets"],
        "Face Value / Ticket":      m["Face Value / Ticket"],
        "Resale Get-In / Ticket":   p["get_in"],
        "Comp Seat Avg / Ticket":   p["comp_price"],
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
        "Sell?", "Match #", "Fixture", "Date", "Time", "Venue", "Venue Map", "Stage", "Category", "Seats",
        "# Tickets", "Face Value / Ticket", "Resale Get-In / Ticket", "Comp Seat Avg / Ticket",
        "Resale Median / Ticket", "Profit at Median", "7D Change", "Demand",
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Sell?":                    st.column_config.CheckboxColumn("Sell?", width="small"),
        "Match #":                  st.column_config.NumberColumn(width="small"),
        "Time":                     st.column_config.TextColumn("Kick-off", width="small"),
        "# Tickets":                st.column_config.NumberColumn(width="small"),
        "Venue Map":                st.column_config.LinkColumn("Map", display_text="🗺️ View Map"),
        "Face Value / Ticket":      st.column_config.NumberColumn(format="$%d"),
        "Resale Get-In / Ticket":   st.column_config.NumberColumn(format="$%d"),
        "Comp Seat Avg / Ticket":   st.column_config.NumberColumn("Comp Seat Avg", format="$%d"),
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

# ── Historical tracking (hardcoded + today's live data) ──────────────────────

HISTORY = pd.DataFrame([
    {"Date": "2026-04-03", "Expected from Sales (Gross)": 55664},
    # add more rows here each day manually, e.g.:
    # {"Date": "2026-04-04", "Expected from Sales (Gross)": 75200},
])

# Compute today's total (all tickets sold at median)
today_str = datetime.now().strftime("%Y-%m-%d")
today_total = base_df["Total Resale (Median)"].sum()

# Append today if not already in history
if today_str not in HISTORY["Date"].values:
    today_row = pd.DataFrame([{"Date": today_str, "Expected from Sales (Gross)": today_total}])
    HISTORY = pd.concat([HISTORY, today_row], ignore_index=True)

HISTORY["Date"] = pd.to_datetime(HISTORY["Date"])
HISTORY = HISTORY.sort_values("Date").set_index("Date")

st.divider()
st.subheader("📈 Expected Total from Sales Over Time (All Tickets, Gross)")
st.line_chart(HISTORY)