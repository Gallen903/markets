import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- Full Default Stock List ---
DEFAULT_STOCKS = [
    {"ticker": "A5G.IR", "name": "AIB Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "BIRG.IR", "name": "Bank of Ireland Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "C5H.IR", "name": "Cairn Homes plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "DHG.IR", "name": "Dalata Hotel Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "DQ7A.IR", "name": "Donegal Investment Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "EG7.IR", "name": "FBD Holdings plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "GL9.IR", "name": "Glanbia plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "GRP.IR", "name": "Greencoat Renewables plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "HSW.IR", "name": "Hostelworld Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "IR5B.IR", "name": "Irish Continental Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "IRES.IR", "name": "Irish Residential Properties REIT Plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "KMR.IR", "name": "Kenmare Resources plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "KRZ.IR", "name": "Kerry Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "KRX.IR", "name": "Kingspan Group plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "MLC.IR", "name": "Malin Corporation plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "OIZ.IR", "name": "Origin Enterprises plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "PTSB.IR", "name": "Permanent TSB Group Holdings plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "RYA.IR", "name": "Ryanair Holdings plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "UPR.IR", "name": "Uniphar plc", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "CRH", "name": "CRH plc", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "FLUT", "name": "Flutter Entertainment plc", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "SW", "name": "Smurfit Westrock Plc", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "DCC.L", "name": "DCC plc", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "GNCL.L", "name": "Greencore Group plc", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "GFTU.L", "name": "Grafton Group plc", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "HVO.L", "name": "hVIVO plc", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "POLB.L", "name": "Poolbeg Pharma PLC", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "TSCO.L", "name": "Tesco PLC", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "VOD.L", "name": "Vodafone Group plc", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "HEIA.AS", "name": "Heineken N.V.", "exchange": "AMS", "currency": "EUR"},
    {"ticker": "BSN.F", "name": "Danone S.A.", "exchange": "FRA", "currency": "EUR"},
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "GOOG", "name": "Alphabet Inc.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "META", "name": "Meta Platforms, Inc.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "AMGN", "name": "Amgen Inc.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "INTC", "name": "Intel Corporation", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "EBAY", "name": "eBay Inc.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "SBUX", "name": "Starbucks Corporation", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "PEP", "name": "PepsiCo, Inc.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "ADI", "name": "Analog Devices, Inc.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "COKE", "name": "Coca-Cola Consolidated, Inc.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "MRK", "name": "Merck & Co., Inc.", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "HPQ", "name": "HP Inc.", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "LLY", "name": "Eli Lilly and Company", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "NVS", "name": "Novartis AG", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "BSX", "name": "Boston Scientific Corporation", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "GE", "name": "GE Aerospace", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "ABT", "name": "Abbott Laboratories", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "STT", "name": "State Street Corporation", "exchange": "NYSE", "currency": "USD"},
    {"ticker": "ICON", "name": "Icon Energy Corp.", "exchange": "NASDAQ", "currency": "USD"},
    {"ticker": "FDP.AQ", "name": "FD Technologies PLC", "exchange": "AQSE", "currency": "GBp"},
]

# --- Streamlit UI ---
st.title("📊 Stock Prices Dashboard")
st.write("View stock prices with 5-day % change and year-to-date % change.")

date_str = st.date_input("Select date", value=datetime.today().date())

# Run button
if st.button("Run"):
    rows = []
    for stock in DEFAULT_STOCKS:
        ticker = stock["ticker"]
        try:
            data = yf.download(ticker, start=f"{date_str.year}-01-01", end=date_str + timedelta(days=1), progress=False)

            if data.empty:
                continue

            # Find last available trading day on or before selected date
            valid_dates = data.index[data.index <= pd.to_datetime(date_str)]
            if len(valid_dates) == 0:
                continue
            sel_date = valid_dates[-1]

            # Always extract as scalar
            price = float(data.loc[sel_date, "Close"])

            # 5-day % change
            past_dates = data.index[data.index <= sel_date - timedelta(days=5)]
            if len(past_dates) > 0:
                past_price = float(data.loc[past_dates[-1], "Close"])
                change_5d = (price - past_price) / past_price * 100
            else:
                change_5d = None

            # YTD % change
            ytd_price = float(data.iloc[0]["Close"])
            change_ytd = (price - ytd_price) / ytd_price * 100

            rows.append({
                "Company": stock["name"],
                "Exchange": f"{stock['exchange']} ({stock['currency']})",
                "Price": round(price, 1),
                "5D % Change": round(change_5d, 1) if change_5d is not None else None,
                "YTD % Change": round(change_ytd, 1),
            })

        except Exception as e:
            continue

    if rows:
        df = pd.DataFrame(rows).sort_values(by=["Exchange", "Company"])
        st.dataframe(df, use_container_width=True)

        # CSV Download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="💾 Download CSV",
            data=csv,
            file_name="stock_prices.csv",
            mime="text/csv",
        )
    else:
        st.warning("No stock data available for that date.")
