import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# ==== DEFAULT STOCK LIST ====
DEFAULT_STOCKS = [
    {"ticker": "STT", "name": "State Street Corporation", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "SBUX", "name": "Starbucks Corporation", "exchange": "NMS", "currency": "USD"},
    {"ticker": "PEP", "name": "PepsiCo, Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "NVS", "name": "Novartis AG", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "META", "name": "Meta Platforms, Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NMS", "currency": "USD"},
    {"ticker": "MRK", "name": "Merck & Co., Inc.", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "INTC", "name": "Intel Corporation", "exchange": "NMS", "currency": "USD"},
    {"ticker": "ICON", "name": "Icon Energy Corp.", "exchange": "NCM", "currency": "USD"},
    {"ticker": "HPQ", "name": "HP Inc.", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "HEIA.AS", "name": "Heineken N.V.", "exchange": "AMS", "currency": "EUR"},
    {"ticker": "GE", "name": "GE Aerospace", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "FDP.AQ", "name": "FD Technologies PLC", "exchange": "AQS", "currency": "GBp"},
    {"ticker": "LLY", "name": "Eli Lilly and Company", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "EBAY", "name": "eBay Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "BSN.F", "name": "Danone S.A.", "exchange": "FRA", "currency": "EUR"},
    {"ticker": "COKE", "name": "Coca-Cola Consolidated, Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "BSX", "name": "Boston Scientific Corporation", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "AMGN", "name": "Amgen Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "ADI", "name": "Analog Devices, Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "ABRONXX", "name": "HSBC USA Inc. Dual Directional Barrier Note ABRONXX", "exchange": "NAS", "currency": "USD"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "GVR.IR", "name": "Glenveagh Properties PLC", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "GOOG", "name": "Alphabet Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "ABT", "name": "Abbott Laboratories", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "CRH", "name": "CRH plc", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "VOD.L", "name": "Vodafone Group Public Limited Company", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "UPR.IR", "name": "Uniphar plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "RYA.IR", "name": "Ryanair Holdings plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "PTSB.IR", "name": "Permanent TSB Group Holdings plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "OIZ.IR", "name": "Origin Enterprises plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "MLC.IR", "name": "Malin Corporation plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "KRX.IR", "name": "Kingspan Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "KRZ.IR", "name": "Kerry Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "KMR.IR", "name": "Kenmare Resources plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "IRES.IR", "name": "Irish Residential Properties REIT Plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "IR5B.IR", "name": "Irish Continental Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "HSW.IR", "name": "Hostelworld Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "GRP.IR", "name": "Greencoat Renewables", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "GL9.IR", "name": "Glanbia plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "EG7.IR", "name": "FBD Holdings plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "DQ7A.IR", "name": "Donegal Investment Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "DHG.IR", "name": "Dalata Hotel Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "C5H.IR", "name": "Cairn Homes plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "A5G.IR", "name": "AIB Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "BIRG.IR", "name": "Bank of Ireland Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "DCC.L", "name": "DCC plc", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "FLTRL.XC", "name": "Flutter Entertainment plc", "exchange": "NYS", "currency": "GBp"},
    {"ticker": "GNCL.XC", "name": "Greencore Group plc", "exchange": "CXE", "currency": "GBp"},
    {"ticker": "GFTUL.XC", "name": "Grafton Group plc", "exchange": "CXE", "currency": "GBp"},
    {"ticker": "HVO.L", "name": "hVIVO plc", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "POLB.L", "name": "Poolbeg Pharma PLC", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "SW", "name": "Smurfit Westrock Plc", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "TSCOL.XC", "name": "TSCOL.XC", "exchange": "CXE", "currency": "GBp"}
]

# ==== FILE TO STORE CUSTOM DEFAULT LIST ====
DEFAULT_FILE = "default_stocks.json"

def load_default_stocks():
    if os.path.exists(DEFAULT_FILE):
        with open(DEFAULT_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_STOCKS

def save_default_stocks(stocks):
    with open(DEFAULT_FILE, "w") as f:
        json.dump(stocks, f)

# ==== STREAMLIT UI ====
st.title("📈 Market Prices Widget")

stocks = load_default_stocks()

# Editable stock list
st.subheader("Edit Stock List")
stock_text = st.text_area("Edit as JSON:", json.dumps(stocks, indent=2))
if st.button("Save as Default List"):
    try:
        new_stocks = json.loads(stock_text)
        save_default_stocks(new_stocks)
        st.success("✅ Default list updated!")
    except Exception as e:
        st.error(f"Error saving list: {e}")

# Date selection
date_str = st.date_input("Select Date", datetime.today()).strftime("%Y-%m-%d")

if st.button("Run"):
    tickers = [s["ticker"] for s in stocks]
    data_rows = []
    
    for stock in stocks:
        try:
            hist = yf.download(stock["ticker"], start=(datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d"), end=(datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"))
            if hist.empty:
                data_rows.append({**stock, "Price": "No data", "5d %": "No data"})
                continue
            
            # Get closest date available
            available_dates = hist.index[hist.index <= pd.to_datetime(date_str)]
            if available_dates.empty:
                data_rows.append({**stock, "Price": "No data", "5d %": "No data"})
                continue
            
            price_date = available_dates[-1]
            price = hist.loc[price_date]["Close"]
            
            # 5-day change
            past_date = price_date - timedelta(days=7)
            past_dates = hist.index[hist.index <= past_date]
            if past_dates.empty:
                change_5d = None
            else:
                old_price = hist.loc[past_dates[-1]]["Close"]
                change_5d = ((price - old_price) / old_price) * 100
            
            data_rows.append({
                **stock,
                "Price": round(price, 2),
                "5d %": round(change_5d, 1) if change_5d is not None else "No data"
            })
        except Exception as e:
            data_rows.append({**stock, "Price": "Error", "5d %": "Error"})

    # Create dataframe grouped by exchange
    df = pd.DataFrame(data_rows)
    df_grouped = df.groupby(["exchange", "currency"])

    for (exchange, currency), group in df_grouped:
        st.subheader(f"{exchange} ({currency})")
        st.dataframe(group[["name", "Price", "5d %"]])

    # Download CSV
    csv = df.to_csv(index=False)
    st.download_button("📥 Download CSV", csv, "prices.csv", "text/csv")
