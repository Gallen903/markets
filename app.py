import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json

# --- 1. Load default tickers ---
default_tickers = [
    "AAPL","MSFT","GOOG","META","PEP","SBUX",
    "AMGN","ADI","COKE","ABT","ABBV","CRH",
    "SW","HPQ","GE","LLY","BSX","MRK","JNJ","ORCL","NVS","PFE"
]

# Check if saved default exists
if os.path.exists("default_tickers.json"):
    with open("default_tickers.json", "r") as f:
        default_tickers = json.load(f)

# --- 2. Editable stock list ---
st.title("Stock Prices Viewer")

tickers_input = st.text_area(
    "Enter stock tickers (comma-separated):",
    ",".join(default_tickers),
    height=150
)
tickers_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# Save as default button
if st.button("Save as Default"):
    with open("default_tickers.json", "w") as f:
        json.dump(tickers_list, f)
    st.success("Default tickers updated!")

# --- 3. Date input ---
date = st.date_input("Select Date")

# --- 4. Fetch stock data ---
@st.cache_data
def get_prices(tickers, date):
    df_list = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=date, end=date + pd.Timedelta(days=1))
            if not hist.empty:
                close_price = hist['Close'][0]
                # 5-day change
                hist_5d = stock.history(period="6d")
                if len(hist_5d) >= 2:
                    change_5d = (hist_5d['Close'][-1] - hist_5d['Close'][0]) / hist_5d['Close'][0] * 100
                else:
                    change_5d = None
                df_list.append({
                    "Ticker": ticker,
                    "Name": stock.info.get("longName", ticker),
                    "Exchange": stock.info.get("exchange", "N/A"),
                    "Currency": stock.info.get("currency", "N/A"),
                    "Close": close_price,
                    "5d Change %": change_5d
                })
        except Exception as e:
            st.warning(f"Could not fetch data for {ticker}: {e}")
    return pd.DataFrame(df_list)

if st.button("Fetch Prices"):
    if tickers_list:
        df = get_prices(tickers_list, pd.to_datetime(date))
        if not df.empty:
            # --- 5. Group by exchange and sort ---
            for exchange, group in df.groupby("Exchange"):
                st.subheader(f"{exchange} ({group['Currency'].iloc[0]})")
                st.dataframe(group.drop(columns="Exchange").sort_values("Name"))
        else:
            st.warning("No data available for the selected date.")
    else:
        st.warning("Please enter at least one ticker.")
import io

# --- CSV Download ---
if not df.empty:
    # Convert DataFrame to CSV
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
