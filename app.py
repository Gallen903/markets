import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Markets Table", layout="wide")
st.title("Stock Prices Dashboard")

# --- Full stock list ---
default_stocks = [
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
    {"ticker": "TSCOL.XC", "name": "TSCOL.XC", "exchange": "CXE", "currency": "GBp"},
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
