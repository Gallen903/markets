import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Markets Table", layout="wide")

st.title("Stock Prices Dashboard")

# --- Default stock list ---
default_stocks = [
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NMS", "currency": "USD"},
    {"ticker": "META", "name": "Meta Platforms, Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "MRK", "name": "Merck & Co., Inc.", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "GOOG", "name": "Alphabet Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "RYA.IR", "name": "Ryanair Holdings plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "HEIA.AS", "name": "Heineken N.V.", "exchange": "AMS", "currency": "EUR"},
    {"ticker": "VOD.L", "name": "Vodafone Group Public Limited Company", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "FLTRL.XC", "name": "Flutter Entertainment plc", "exchange": "CXE", "currency": "GBp"},
    # Add the rest of your stocks here following the same format
]

# --- Sidebar for manual ticker addition ---
st.sidebar.header("Add Custom Tickers")
custom_tickers_input = st.sidebar.text_area(
    "Enter tickers, one per line in format TICKER,Name,Exchange,Currency",
    value=""
)

if custom_tickers_input:
    for line in custom_tickers_input.strip().split("\n"):
        try:
            ticker, name, exchange, currency = [x.strip() for x in line.split(",")]
            default_stocks.append({
                "ticker": ticker,
                "name": name,
                "exchange": exchange,
                "currency": currency
            })
        except:
            st.sidebar.error(f"Invalid line: {line}")

# --- Date selection ---
date_input = st.sidebar.date_input("Select Date")

# --- Run button ---
if st.sidebar.button("Run"):
    date_str = pd.to_datetime(date_input)
    all_data = []

    for stock in default_stocks:
        try:
            ticker = yf.Ticker(stock["ticker"])
            hist = ticker.history(period="15d")
            hist.index = pd.to_datetime(hist.index.date)

            if hist.empty:
                raise ValueError("No data")

            # Closest available trading day
            closest_date = hist.index[hist.index <= date_str].max()
            if pd.isna(closest_date):
                close_price = None
                pct_change = None
            else:
                close_price = hist.loc[closest_date]["Close"]

                idx = hist.index.get_loc(closest_date)
                if idx >= 5:
                    prev_close = hist.iloc[idx-5]["Close"]
                    pct_change = (close_price / prev_close - 1) * 100
                else:
                    pct_change = None

            all_data.append({
                "Company": stock["name"],
                "Exchange": stock["exchange"],
                "Currency": stock["currency"],
                "Close": close_price,
                "5D % Change": pct_change
            })
        except:
            all_data.append({
                "Company": stock["name"],
                "Exchange": stock["exchange"],
                "Currency": stock["currency"],
                "Close": None,
                "5D % Change": None
            })

    df = pd.DataFrame(all_data)
    df_grouped = df.sort_values(["Exchange", "Company"])

    for exch, group in df_grouped.groupby("Exchange"):
        st.subheader(f"{exch} ({group['Currency'].iloc[0]})")
        st.dataframe(group.drop(columns="Exchange").reset_index(drop=True))
