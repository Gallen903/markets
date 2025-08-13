# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ---- CONFIG ----

# Default tickers and custom company names
TICKERS = {
    "HEIA.AS": "Heineken N.V.",
    "FDP.AQ": "FD Technologies PLC",
    "FLTRL.XC": "Flutter Entertainment plc",
    "GNCL.XC": "Greencore Group plc",
    "GFTUL.XC": "Grafton Group plc",
    "TSCOL.XC": "Tesco PLC",
    "BSN.F": "Danone S.A.",
    "GVR.IR": "Glenveagh Properties PLC",
    "UPR.IR": "Uniphar plc",
    "RYA.IR": "Ryanair Holdings plc",
    "PTSB.IR": "Permanent TSB Group Holdings plc",
    "OIZ.IR": "Origin Enterprises plc",
    "MLC.IR": "Malin Corporation plc",
    "KRX.IR": "Kingspan Group plc",
    "KRZ.IR": "Kerry Group plc",
    "KMR.IR": "Kenmare Resources plc",
    "IRES.IR": "Irish Residential Properties REIT Plc",
    "IR5B.IR": "Irish Continental Group plc",
    "HSW.IR": "Hostelworld Group plc",
    "GRP.IR": "Greencoat Renewables",
    "GL9.IR": "Glanbia plc",
    "EG7.IR": "FBD Holdings plc",
    "DQ7A.IR": "Donegal Investment Group plc",
    "DHG.IR": "Dalata Hotel Group plc",
    "C5H.IR": "Cairn Homes plc",
    "A5G.IR": "AIB Group plc",
    "BIRG.IR": "Bank of Ireland Group plc",
    "VOD.L": "Vodafone Group",
    "DCC.L": "DCC plc",
    "HVO.L": "hVIVO plc",
    "POLB.L": "Poolbeg Pharma PLC",
    "ABRONXX": "HSBC USA Inc. Dual Directional Barrier Note",
    "ICON": "Icon Energy Corp.",
    "SBUX": "Starbucks Corporation",
    "PEP": "PepsiCo, Inc.",
    "META": "Meta Platforms, Inc.",
    "MSFT": "Microsoft Corporation",
    "INTC": "Intel Corporation",
    "EBAY": "eBay Inc.",
    "COKE": "Coca-Cola Consolidated, Inc.",
    "AAPL": "Apple Inc.",
    "AMGN": "Amgen Inc.",
    "ADI": "Analog Devices, Inc.",
    "GOOG": "Alphabet Inc.",
    "STT": "State Street Corporation",
    "PFE": "Pfizer Inc.",
    "ORCL": "Oracle Corporation",
    "NVS": "Novartis AG",
    "MRK": "Merck & Co., Inc.",
    "JNJ": "Johnson & Johnson",
    "HPQ": "HP Inc.",
    "GE": "GE Aerospace",
    "LLY": "Eli Lilly and Company",
    "BSX": "Boston Scientific Corporation",
    "ABBV": "AbbVie Inc.",
    "ABT": "Abbott Laboratories",
    "CRH": "CRH plc",
    "SW": "Smurfit Westrock Plc"
}

st.title("Stock Prices & 5-Day % Change")

# --- USER INPUT ---
input_date = st.date_input("Select Date", datetime.today())

# Convert date to string for yfinance
date_str = input_date.strftime("%Y-%m-%d")

# --- DATA FETCHING ---
df_list = []

for ticker, name in TICKERS.items():
    try:
        data = yf.download(ticker, start=(input_date - timedelta(days=7)).strftime("%Y-%m-%d"),
                           end=(input_date + timedelta(days=1)).strftime("%Y-%m-%d"))
        if data.empty:
            continue

        # Ensure the date exists in data
        if date_str not in data.index.strftime("%Y-%m-%d"):
            continue

        closing_price = data.loc[date_str]["Close"]
        five_days_ago = (input_date - timedelta(days=5)).strftime("%Y-%m-%d")
        # Find nearest previous available date for 5-day comparison
        past_prices = data[:date_str]
        if past_prices.empty:
            pct_change_5d = None
        else:
            closest_date = past_prices.index[-1]
            past_price = past_prices.loc[closest_date]["Close"]
            pct_change_5d = ((closing_price - past_price) / past_price) * 100

        # Get currency from yfinance info
        info = yf.Ticker(ticker).info
        exchange = info.get("exchange", "Unknown Exchange")
        currency = info.get("currency", "")

        df_list.append({
            "Exchange": exchange,
            "Currency": currency,
            "Company": name,
            "Closing Price": closing_price,
            "5-Day % Change": pct_change_5d
        })
    except Exception as e:
        st.warning(f"Failed to fetch {ticker}: {e}")

# --- DATAFRAME ---
if df_list:
    df = pd.DataFrame(df_list)
    # Group by exchange
    for ex, group in df.groupby("Exchange"):
        currency = group["Currency"].iloc[0]
        st.subheader(f"{ex} ({currency})")
        st.dataframe(group[["Company", "Closing Price", "5-Day % Change"]].sort_values("Company"))
else:
    st.info("No data available for the selected date.")
