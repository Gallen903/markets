import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- Exchange to Region Mapping ---
EXCHANGE_REGION = {
    "NYQ": "US",
    "NMS": "US",
    "NYS": "US",
    "NCM": "US",
    "CXE": "UK",
    "LSE": "UK",
    "AQS": "UK",
    "ISE": "Ireland",
    "AMS": "Europe",
    "FRA": "Europe",
    "BME": "Europe",
}

# --- Full Stock Master List ---
MASTER_STOCKS = [
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
    {"ticker": "ABBV", "name": "AbbVie Inc.", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "GVR.IR", "name": "Glenveagh Properties PLC", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "GOOG", "name": "Alphabet Inc.", "exchange": "NMS", "currency": "USD"},
    {"ticker": "ABT", "name": "Abbott Laboratories", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "CRH", "name": "CRH plc", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "VOD.L", "name": "Vodafone Group", "exchange": "LSE", "currency": "GBp"},
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
    {"ticker": "FLUT", "name": "Flutter Entertainment plc", "exchange": "NYQ", "currency": "USD"},  # updated to NY
    {"ticker": "GNCL.XC", "name": "Greencore Group plc", "exchange": "CXE", "currency": "GBp"},
    {"ticker": "GFTUL.XC", "name": "Grafton Group plc", "exchange": "CXE", "currency": "GBp"},
    {"ticker": "HVO.L", "name": "hVIVO plc", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "POLB.L", "name": "Poolbeg Pharma PLC", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "SW", "name": "Smurfit Westrock Plc", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "TSCOL.XC", "name": "Tesco plc", "exchange": "CXE", "currency": "GBp"},
    {"ticker": "NTRB", "name": "Nutriband", "exchange": "NCM", "currency": "USD"},
    {"ticker": "DEO", "name": "Diageo", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "AER", "name": "AerCap Holdings", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "BRBY.L", "name": "Burberry", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "YZA.IR", "name": "Arytza", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "SSPG.L", "name": "SSP Group", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "BKT.MC", "name": "Bankinter", "exchange": "BME", "currency": "EUR"},
    {"ticker": "ABF.L", "name": "Associated British Foods", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "GWMO.L", "name": "Great Western Mining Corp", "exchange": "LSE", "currency": "GBp"},
]

# --- Streamlit UI ---
st.title("📊 Stock Dashboard")
st.write("View stock prices with 5-day % change and year-to-date % change.")

date_str = st.date_input("Select date")

# Allow user to edit stock list
stock_options = {f"{s['name']} ({s['ticker']})": s for s in MASTER_STOCKS}
selected_labels = st.multiselect("Select stocks to include:", list(stock_options.keys()), default=list(stock_options.keys()))
SELECTED_STOCKS = [stock_options[label] for label in selected_labels]

if st.button("Run"):
    rows = []
    for stock in SELECTED_STOCKS:
        ticker = stock["ticker"]
        try:
            data = yf.download(ticker, start=f"{date_str.year}-01-01", end=date_str + timedelta(days=1), progress=False)

            if data.empty:
                continue

            valid_dates = data.index[data.index <= pd.to_datetime(date_str)]
            if len(valid_dates) == 0:
                continue
            sel_date = valid_dates[-1]

            price = float(data.loc[sel_date, "Close"])
            past_dates = data.index[data.index <= sel_date - timedelta(days=5)]
            change_5d = None
            if len(past_dates) > 0:
                past_price = float(data.loc[past_dates[-1], "Close"])
                change_5d = (price - past_price) / past_price * 100

            ytd_price = float(data.iloc[0]["Close"])
            change_ytd = (price - ytd_price) / ytd_price * 100

            rows.append({
                "Company": stock["name"],
                "Region": EXCHANGE_REGION.get(stock["exchange"], "Other"),
                "Exchange": stock["exchange"],
                "Currency": stock["currency"],
                "Price": round(price, 1),
                "5D % Change": round(change_5d, 1) if change_5d is not None else None,
                "YTD % Change": round(change_ytd, 1),
            })
        except Exception:
            continue

    if rows:
        df = pd.DataFrame(rows).sort_values(by=["Region", "Company"])
        grouped = df.groupby(["Region", "Currency"])

        for (region, currency), gdf in grouped:
            st.subheader(f"{region} ({currency})")
            st.dataframe(gdf.drop(columns=["Region", "Currency"]), use_container_width=True)

        # --- CSV Output by Region ---
        output_lines = []
        for (region, currency), gdf in grouped:
            output_lines.append(f"{region} ({currency})")
            output_lines.append("Company,Price,5D % Change,YTD % Change")
            for _, row in gdf.drop(columns=["Region", "Currency"]).iterrows():
                p = f"{row['Price']:.1f}" if pd.notnull(row['Price']) else ""
                c5 = f"{row['5D % Change']:.1f}" if pd.notnull(row['5D % Change']) else ""
                cy = f"{row['YTD % Change']:.1f}" if pd.notnull(row['YTD % Change']) else ""
                output_lines.append(f"{row['Company']},{p},{c5},{cy}")
            output_lines.append("")

        csv = "\n".join(output_lines).encode("utf-8")
        st.download_button("💾 Download CSV", csv, "stock_data.csv", "text/csv")
    else:
        st.warning("No stock data available for that date.")
