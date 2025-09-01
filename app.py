import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import io
import csv
import json
import os

# --- Master list persistence ---
MASTER_FILE = "master_stocks.json"

# Hard-coded backup master list (used only if no JSON file exists yet)
DEFAULT_MASTER_STOCKS = [
    {"ticker": "STT", "name": "State Street Corporation", "region": "US", "currency": "USD"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "region": "US", "currency": "USD"},
    # ... (rest of your list unchanged)
    {"ticker": "YZA.IR", "name": "Arytza", "region": "Ireland", "currency": "EUR"},
]

# Load from file if available
if os.path.exists(MASTER_FILE):
    with open(MASTER_FILE, "r") as f:
        MASTER_STOCKS = json.load(f)
else:
    MASTER_STOCKS = DEFAULT_MASTER_STOCKS.copy()
    with open(MASTER_FILE, "w") as f:
        json.dump(MASTER_STOCKS, f, indent=2)

# --- Streamlit UI ---
st.title("📊 Stock Dashboard")
st.write("View stock prices with 5-day % change and year-to-date % change.")

# Add stock form
st.subheader("➕ Add a custom stock")
with st.form("add_stock_form", clear_on_submit=True):
    new_ticker = st.text_input("Ticker symbol (e.g. NVDA)").strip().upper()
    new_name = st.text_input("Company name (e.g. NVIDIA Corporation)").strip()
    new_region = st.selectbox("Region", ["Ireland", "UK", "Europe", "US"])
    new_currency = st.selectbox("Currency", ["EUR", "GBp", "USD"])
    add_button = st.form_submit_button("Add stock")

if add_button and new_ticker and new_name:
    new_stock = {
        "ticker": new_ticker,
        "name": new_name,
        "region": new_region,
        "currency": new_currency,
    }
    MASTER_STOCKS.append(new_stock)
    with open(MASTER_FILE, "w") as f:
        json.dump(MASTER_STOCKS, f, indent=2)
    st.success(f"Added {new_name} ({new_ticker}) to master list ✅")

# Remove stock option
st.subheader("🗑️ Remove stock(s) from master list")
stock_labels = [f"{s['name']} ({s['ticker']})" for s in MASTER_STOCKS]
stocks_to_remove = st.multiselect("Select stock(s) to remove", stock_labels)
if st.button("Remove selected"):
    if stocks_to_remove:
        before_count = len(MASTER_STOCKS)
        MASTER_STOCKS = [s for s in MASTER_STOCKS if f"{s['name']} ({s['ticker']})" not in stocks_to_remove]
        with open(MASTER_FILE, "w") as f:
            json.dump(MASTER_STOCKS, f, indent=2)
        removed_count = before_count - len(MASTER_STOCKS)
        st.success(f"Removed {removed_count} stock(s) from master list ✅")
    else:
        st.warning("No stocks selected for removal.")

date_str = st.date_input("Select date")

# Allow user to edit stock list
stock_options = {f"{s['name']} ({s['ticker']})": s for s in MASTER_STOCKS}
selected_labels = st.multiselect(
    "Select stocks to include:", list(stock_options.keys()), default=list(stock_options.keys())
)
SELECTED_STOCKS = [stock_options[label] for label in selected_labels]

if st.button("Run"):
    rows = []
    for stock in SELECTED_STOCKS:
        ticker = stock["ticker"]
        try:
            data = yf.download(
                ticker, start=f"{date_str.year}-01-01", end=date_str + timedelta(days=1), progress=False
            )
            if data.empty:
                continue

            valid_dates = data.index[data.index <= pd.to_datetime(date_str)]
            if len(valid_dates) == 0:
                continue
            sel_date = valid_dates[-1]

            price = float(data.loc[sel_date, "Close"])

            # 5-day % change
            past_dates = data.index[data.index <= sel_date - timedelta(days=5)]
            change_5d = None
            if len(past_dates) > 0:
                past_price = float(data.loc[past_dates[-1], "Close"])
                change_5d = (price - past_price) / past_price * 100

            # YTD % change
            ytd_price = float(data.iloc[0]["Close"])
            change_ytd = (price - ytd_price) / ytd_price * 100

            rows.append({
                "Company": stock["name"],
                "Region": stock["region"],
                "Currency": stock["currency"],
                "Price": round(price, 1),
                "5D % Change": round(change_5d, 1) if change_5d is not None else None,
                "YTD % Change": round(change_ytd, 1),
            })
        except Exception:
            continue

    if rows:
        df = pd.DataFrame(rows).sort_values(by=["Region", "Company"])
        grouped = df.groupby(["Region", "Currency"])

        # Display in Streamlit
        for (region, currency), gdf in grouped:
            st.subheader(f"{region} ({currency})")
            st.dataframe(gdf.drop(columns=["Region", "Currency"]), use_container_width=True)

        # --- CSV Output ---
        REGION_LABELS = {
            "Ireland": "Ireland (€)",
            "UK": "UK (£)",
            "Europe": "Europe (€)",
            "US": "US ($)"
        }

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        for region in ["Ireland", "UK", "Europe", "US"]:
            for (r, currency), gdf in grouped:
                if r != region:
                    continue
                writer.writerow([REGION_LABELS[r], "Last price", "5D %change", "YTD % change"])
                for _, row in gdf.iterrows():
                    company = row['Company'].replace('"', '')  
                    price = f"{row['Price']:.1f}" if pd.notnull(row['Price']) else ""
                    c5 = f"{row['5D % Change']:.1f}" if pd.notnull(row['5D % Change']) else ""
                    cy = f"{row['YTD % Change']:.1f}" if pd.notnull(row['YTD % Change']) else ""
                    writer.writerow([company, price, c5, cy])

        csv_bytes = '\ufeff' + output.getvalue()  
        st.download_button("💾 Download CSV", csv_bytes, "stock_data.csv", "text/csv")
    else:
        st.warning("No stock data available for that date.")
