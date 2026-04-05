import streamlit as st
import pandas as pd
from datetime import datetime
from matches import MATCHES
from scraper import fetch_prices_raw
from supabase import create_client

@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

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
    return fetch_prices_raw(url, match_id, tier)

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