import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
import json
import os

st.title("Stock Prices Viewer")

# --- JSON file to store tickers ---
TICKERS_FILE = "tickers.json"

# --- Default tickers ---
default_tickers = [
    "HEIA.AS", "FDP.AQ", "PDYPY", "GNCL.XC", "GFTUL.XC", "TSCOL.XC",
    "BSN.F", "GVR.IR", "UPR.IR", "RYA.IR", "PTSB.IR", "OIZ.IR",
    "MLC.IR", "KRX.IR", "KRZ.IR", "KMR.IR", "IRES.IR", "IR5B.IR",
    "HSW.IR", "GRP.IR", "GL9.IR", "EG7.IR", "DQ7A.IR", "DHG.IR",
    "C5H.IR", "A5G.IR", "BIRG.IR", "VOD.L", "DCC.L", "HVO.L",
    "POLB.L", "ABRONXX", "ICON", "SBUX", "PEP", "META", "MSFT",
    "INTC", "EBAY", "COKE", "AAPL", "AMGN", "ADI", "GOOG", "STT",
    "PFE", "ORCL", "NVS", "MRK", "JNJ", "HPQ", "GE", "LLY", "BSX",
    "ABBV", "ABT", "CRH", "SW"
]

# --- Load saved tickers or use default ---
if os.path.exists(TICKERS_FILE):
    try:
        with open(TICKERS_FILE, "r") as f:
            st.session_state.tickers = json.load(f)
    except Exception:
        st.session_state.tickers = default_tickers
else:
    st.session_state.tickers = default_tickers

# --- Date input ---
date_input = st.date_input("Select date", datetime.today())
date_str = date_input.strftime("%Y-%m-%d")

# --- Editable tickers list ---
tickers_text = st.text_area(
    "Enter tickers (comma separated):",
    value=", ".join(st.session_state.tickers),
    height=200
)

tickers_list = [t.strip() for t in tickers_text.split(",") if t.strip()]

# --- Save updated tickers to JSON ---
if st.button("Save as Default"):
    st.session_state.tickers = tickers_list
    with open(TICKERS_FILE, "w") as f:
        json.dump(st.session_state.tickers, f)
    st.success("Ticker list saved as default!")

# --- Run button ---
if st.button("Get Prices"):
    all_data = []
    for ticker in tickers_list:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=date_str, end=date_str)
            if hist.empty:
                st.warning(f"No data for {ticker} on {date_str}")
                continue
            close_price = hist['Close'].iloc[0]

            # Calculate 5-day % change
            hist_5d = stock.history(period="6d")
            if len(hist_5d) < 6:
                pct_change_5d = None
            else:
                pct_change_5d = (hist_5d['Close'][-1] - hist_5d['Close'][0]) / hist_5d['Close'][0] * 100

            all_data.append({
                "Ticker": ticker,
                "Name": stock.info.get('shortName', ''),
                "Exchange": stock.info.get('exchange', ''),
                "Currency": stock.info.get('currency', ''),
                "Close": close_price,
                "5-Day % Change": pct_change_5d
            })
        except Exception as e:
            st.error(f"Error fetching {ticker}: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        # Group by exchange
        for exchange, group in df.groupby('Exchange'):
            currency = group['Currency'].iloc[0] if not group.empty else ""
            st.subheader(f"{exchange} ({currency})")
            display_cols = ["Name", "Close", "5-Day % Change"]
            st.dataframe(group[display_cols].sort_values("Name"))
