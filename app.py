# --- Install required packages ---
# pip install yfinance pandas streamlit --quiet

import streamlit as st
import yfinance as yf
import pandas as pd
import io
import json
import os

# --- File to store default tickers ---
DEFAULT_FILE = "default_tickers.json"

# --- Load or set default tickers ---
default_tickers = [
    "HEIA.AS", "FDP.AQ", "FLTRL.XC", "GNCL.XC", "GFTUL.XC", "TSCOL.XC", 
    "BSN.F", "GVR.IR", "UPR.IR", "RYA.IR", "PTSB.IR", "OIZ.IR", "MLC.IR",
    "KRX.IR", "KRZ.IR", "KMR.IR", "IRES.IR", "IR5B.IR", "HSW.IR", "GRP.IR",
    "GL9.IR", "EG7.IR", "DQ7A.IR", "DHG.IR", "C5H.IR", "A5G.IR", "BIRG.IR",
    "VOD.L", "DCC.L", "HVO.L", "POLB.L", "ABRONXX", "ICON", "SBUX", "PEP",
    "META", "MSFT", "INTC", "EBAY", "COKE", "AAPL", "AMGN", "ADI", "GOOG",
    "STT", "PFE", "ORCL", "NVS", "MRK", "JNJ", "HPQ", "GE", "LLY", "BSX",
    "ABBV", "ABT", "CRH", "SW"
]

# Save default list to JSON if file doesn't exist
if not os.path.exists(DEFAULT_FILE):
    with open(DEFAULT_FILE, "w") as f:
        json.dump(default_tickers, f)

# Load from file
with open(DEFAULT_FILE, "r") as f:
    saved_tickers = json.load(f)

# --- Sidebar for user input ---
st.sidebar.header("Stock Settings")

# Manual editable ticker list
user_tickers = st.sidebar.text_area(
    "Enter ticker symbols (comma-separated):",
    value=",".join(saved_tickers)
)
tickers = [t.strip() for t in user_tickers.split(",") if t.strip()]

# Option to save new default list
save_default = st.sidebar.checkbox("Save as default list")
if save_default:
    with open(DEFAULT_FILE, "w") as f:
        json.dump(tickers, f)
    st.sidebar.success("Default list updated!")

# Date selector
date = st.sidebar.date_input("Select date")

st.header(f"Stock Prices for {date}")

# --- Fetch data from Yahoo Finance ---
data_list = []
for ticker in tickers:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="10d")  # last 10 days to calculate 5-day %
        if date.strftime("%Y-%m-%d") in hist.index.strftime("%Y-%m-%d"):
            row = hist.loc[date.strftime("%Y-%m-%d")]
            close_price = row["Close"]
            # Calculate 5-day % change
            five_day_price = hist["Close"].shift(5).loc[date.strftime("%Y-%m-%d")]
            pct_change_5d = ((close_price - five_day_price) / five_day_price * 100) if not pd.isna(five_day_price) else None

            data_list.append({
                "Name": stock.info.get("shortName", ticker),
                "Exchange": stock.info.get("exchange", "N/A"),
                "Currency": stock.info.get("currency", ""),
                "Close": close_price,
                "5d %": pct_change_5d
            })
    except Exception as e:
        st.warning(f"Failed to fetch {ticker}: {e}")

# --- Display grouped by exchange ---
if data_list:
    df = pd.DataFrame(data_list)
    grouped = df.groupby("Exchange")
    for exch, group in grouped:
        st.subheader(f"{exch} ({group['Currency'].iloc[0]})")
        st.dataframe(group.sort_values("Name").drop(columns=["Exchange", "Currency"]))
    
    # --- CSV Download ---
    csv_buffer = io.StringIO()
    df_sorted = df.sort_values(["Exchange", "Name"]).drop(columns="Exchange")
    df_sorted.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode()
    
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name=f"stock_prices_{date}.csv",
        mime="text/csv"
    )
else:
    st.info("No data found for selected tickers and date.")
