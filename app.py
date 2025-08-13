# app.py
import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Prices App", layout="wide")
st.title("Stock Prices and 5-Day Change")

# Default ticker list with company names and exchanges
stocks = [
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NMS", "currency": "USD"},
    {"ticker": "GOOG", "name": "Alphabet Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "META", "name": "Meta Platforms, Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "HEIA.AS", "name": "Heineken N.V.", "exchange": "AMS", "currency": "EUR"},
    {"ticker": "FDP.AQ", "name": "FD Technologies PLC", "exchange": "AQS", "currency": "GBp"},
    {"ticker": "FLTRL.N", "name": "Flutter Entertainment plc (New York)", "exchange": "NMS", "currency": "USD"},
    {"ticker": "GNCL.XC", "name": "Greencore Group plc", "exchange": "CXE", "currency": "GBp"},
    {"ticker": "GFTUL.XC", "name": "Grafton Group plc", "exchange": "CXE", "currency": "GBp"},
    {"ticker": "TSCOL.XC", "name": "Tesco PLC", "exchange": "CXE", "currency": "GBp"},
]

# Sidebar date picker
date_str = st.sidebar.date_input("Select Date").strftime("%Y-%m-%d")

# Run button
if st.sidebar.button("Run"):
    results = []

    for stock in stocks:
        ticker = stock["ticker"]
        name = stock["name"]
        exchange = stock["exchange"]
        currency = stock["currency"]

        try:
            hist = yf.Ticker(ticker).history(period="60d")
            
            if hist.empty:
                results.append({
                    "Company": name,
                    "Exchange": exchange,
                    "Currency": currency,
                    "Close": "No data",
                    "5D %": "N/A"
                })
                continue

            # Remove timezone to avoid TypeError
            hist.index = hist.index.tz_localize(None)

            # get available dates <= selected date
            available_dates = hist.index[hist.index <= pd.to_datetime(date_str)]

            if len(available_dates) == 0:
                close_price = "No data"
                change_5d = "N/A"
            else:
                last_row = hist.loc[available_dates[-1]]
                close_price = last_row["Close"]

                if len(available_dates) >= 6:
                    prev_close = hist.loc[available_dates[-6]]["Close"]
                    change_5d = round((close_price - prev_close) / prev_close * 100, 2)
                else:
                    change_5d = "N/A"

            results.append({
                "Company": name,
                "Exchange": exchange,
                "Currency": currency,
                "Close": close_price,
                "5D %": change_5d
            })
        except Exception as e:
            results.append({
                "Company": name,
                "Exchange": exchange,
                "Currency": currency,
                "Close": "Error",
                "5D %": "Error"
            })

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Group by exchange and sort alphabetically
    for exch, group in df.groupby("Exchange"):
        st.subheader(f"{exch} ({group['Currency'].iloc[0]})")
        st.dataframe(group.sort_values("Company").reset_index(drop=True))
