import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json

# ----------------------------
# Default ticker list
# ----------------------------
default_tickers = [
    "HEIA.AS","FDP.AQ","FLTRL.NY","GNCL.XC","GFTUL.XC","TSCOL.XC",
    "BSN.F","GVR.IR","UPR.IR","RYA.IR","PTSB.IR","OIZ.IR",
    "MLC.IR","KRX.IR","KRZ.IR","KMR.IR","IRES.IR","IR5B.IR",
    "HSW.IR","GRP.IR","GL9.IR","EG7.IR","DQ7A.IR","DHG.IR",
    "C5H.IR","A5G.IR","BIRG.IR","VOD.L","DCC.L","HVO.L",
    "POLB.L","ABRONXX","ICON","SBUX","PEP","META","MSFT",
    "INTC","EBAY","COKE","AAPL","AMGN","ADI","GOOG","STT",
    "PFE","ORCL","NVS","MRK","JNJ","HPQ","GE","LLY","BSX",
    "ABBV","ABT","CRH","SW"
]

# Load saved tickers if available
try:
    with open("tickers.json", "r") as f:
        saved_tickers = json.load(f)
        tickers = saved_tickers
except FileNotFoundError:
    tickers = default_tickers

# ----------------------------
# Streamlit App Layout
# ----------------------------
st.title("Stock Prices & 5-Day Change")

st.subheader("Ticker List (editable)")
ticker_input = st.text_area("Enter tickers separated by commas:", value=",".join(tickers))
ticker_list = [t.strip() for t in ticker_input.split(",") if t.strip()]

# Option to save new ticker list
if st.button("Save as default"):
    with open("tickers.json", "w") as f:
        json.dump(ticker_list, f)
    st.success("Ticker list saved!")

# Date input
date_input = st.date_input("Select Date", datetime.today())
date_str = date_input.strftime("%Y-%m-%d")

# Run button
if st.button("Run"):
    results = []

    for ticker in ticker_list:
        stock = yf.Ticker(ticker)
        
        # fetch last 7 days to cover holidays/weekends
        start_date = date_input - timedelta(days=7)
        end_date = date_input + timedelta(days=1)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            results.append({
                "Ticker": ticker,
                "Name": stock.info.get("shortName", ""),
                "Exchange": stock.info.get("exchange", ""),
                "Currency": stock.info.get("currency", ""),
                "Close": "No data",
                "5d Change (%)": "N/A"
            })
            continue

        # get the closing price for selected date (or most recent before)
        available_dates = hist.index[hist.index <= pd.to_datetime(date_str)]
        last_row = hist.loc[available_dates[-1]]
        close_price = last_row["Close"]

        # calculate 5-day change
        if len(available_dates) >= 6:
            prev_close = hist.loc[available_dates[-6]]["Close"]
            change_5d = (close_price - prev_close) / prev_close * 100
            change_5d = round(change_5d, 2)
        else:
            change_5d = "N/A"

        results.append({
            "Ticker": ticker,
            "Name": stock.info.get("shortName", ""),
            "Exchange": stock.info.get("exchange", ""),
            "Currency": stock.info.get("currency", ""),
            "Close": close_price,
            "5d Change (%)": change_5d
        })

    df = pd.DataFrame(results)

    # Group by Exchange
    grouped = df.groupby("Exchange")
    for ex, group in grouped:
        currency = group["Currency"].iloc[0] if not group.empty else ""
        st.subheader(f"{ex} ({currency})")
        st.dataframe(group.drop(columns=["Exchange","Currency","Ticker"]))
