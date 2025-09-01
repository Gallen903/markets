import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import io
import csv

# --- Full Stock Master List ---
MASTER_STOCKS = [
    {"ticker": "STT", "name": "State Street Corporation", "region": "US", "currency": "USD"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "region": "US", "currency": "USD"},
    {"ticker": "SBUX", "name": "Starbucks Corporation", "region": "US", "currency": "USD"},
    {"ticker": "PEP", "name": "PepsiCo, Inc.", "region": "US", "currency": "USD"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "region": "US", "currency": "USD"},
    {"ticker": "NVS", "name": "Novartis AG", "region": "US", "currency": "USD"},
    {"ticker": "META", "name": "Meta Platforms, Inc.", "region": "US", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "region": "US", "currency": "USD"},
    {"ticker": "MRK", "name": "Merck & Co., Inc.", "region": "US", "currency": "USD"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "region": "US", "currency": "USD"},
    {"ticker": "INTC", "name": "Intel Corporation", "region": "US", "currency": "USD"},
    {"ticker": "ICON", "name": "Icon Energy Corp.", "region": "US", "currency": "USD"},
    {"ticker": "HPQ", "name": "HP Inc.", "region": "US", "currency": "USD"},
    {"ticker": "GE", "name": "GE Aerospace", "region": "US", "currency": "USD"},
    {"ticker": "LLY", "name": "Eli Lilly and Company", "region": "US", "currency": "USD"},
    {"ticker": "EBAY", "name": "eBay Inc.", "region": "US", "currency": "USD"},
    {"ticker": "COKE", "name": "Coca-Cola Consolidated, Inc.", "region": "US", "currency": "USD"},
    {"ticker": "BSX", "name": "Boston Scientific Corporation", "region": "US", "currency": "USD"},
    {"ticker": "AAPL", "name": "Apple Inc.", "region": "US", "currency": "USD"},
    {"ticker": "AMGN", "name": "Amgen Inc.", "region": "US", "currency": "USD"},
    {"ticker": "ADI", "name": "Analog Devices, Inc.", "region": "US", "currency": "USD"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "region": "US", "currency": "USD"},
    {"ticker": "GOOG", "name": "Alphabet Inc.", "region": "US", "currency": "USD"},
    {"ticker": "ABT", "name": "Abbott Laboratories", "region": "US", "currency": "USD"},
    {"ticker": "CRH", "name": "CRH plc", "region": "US", "currency": "USD"},
    {"ticker": "SW", "name": "Smurfit Westrock Plc", "region": "US", "currency": "USD"},
    {"ticker": "DEO", "name": "Diageo", "region": "US", "currency": "USD"},
    {"ticker": "AER", "name": "AerCap Holdings", "region": "US", "currency": "USD"},
    {"ticker": "FLUT", "name": "Flutter Entertainment plc", "region": "US", "currency": "USD"},  # NY listing

    {"ticker": "HEIA.AS", "name": "Heineken N.V.", "region": "Europe", "currency": "EUR"},
    {"ticker": "BSN.F", "name": "Danone S.A.", "region": "Europe", "currency": "EUR"},
    {"ticker": "VOD.L", "name": "Vodafone Group", "region": "UK", "currency": "GBp"},
    {"ticker": "DCC.L", "name": "DCC plc", "region": "UK", "currency": "GBp"},
    {"ticker": "GNCL.L", "name": "Greencore Group plc", "region": "UK", "currency": "GBp"},
    {"ticker": "GFTUL.XC", "name": "Grafton Group plc", "region": "UK", "currency": "GBp"},
    {"ticker": "HVO.L", "name": "hVIVO plc", "region": "UK", "currency": "GBp"},
    {"ticker": "POLB.L", "name": "Poolbeg Pharma PLC", "region": "UK", "currency": "GBp"},
    {"ticker": "TSCOL.XC", "name": "Tesco plc", "region": "UK", "currency": "GBp"},
    {"ticker": "BRBY.L", "name": "Burberry", "region": "UK", "currency": "GBp"},
    {"ticker": "SSPG.L", "name": "SSP Group", "region": "UK", "currency": "GBp"},
    {"ticker": "BKT.MC", "name": "Bankinter", "region": "Europe", "currency": "EUR"},
    {"ticker": "ABF.L", "name": "Associated British Foods", "region": "UK", "currency": "GBp"},
    {"ticker": "GWMO.L", "name": "Great Western Mining Corp", "region": "UK", "currency": "GBp"},

    {"ticker": "GVR.IR", "name": "Glenveagh Properties PLC", "region": "Ireland", "currency": "EUR"},
    {"ticker": "UPR.IR", "name": "Uniphar plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "RYA.IR", "name": "Ryanair Holdings plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "PTSB.IR", "name": "Permanent TSB Group Holdings plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "OIZ.IR", "name": "Origin Enterprises plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "MLC.IR", "name": "Malin Corporation plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "KRX.IR", "name": "Kingspan Group plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "KRZ.IR", "name": "Kerry Group plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "KMR.IR", "name": "Kenmare Resources plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "IRES.IR", "name": "Irish Residential Properties REIT Plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "IR5B.IR", "name": "Irish Continental Group plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "HSW.IR", "name": "Hostelworld Group plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "GRP.IR", "name": "Greencoat Renewables", "region": "Ireland", "currency": "EUR"},
    {"ticker": "GL9.IR", "name": "Glanbia plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "EG7.IR", "name": "FBD Holdings plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "DQ7A.IR", "name": "Donegal Investment Group plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "DHG.IR", "name": "Dalata Hotel Group plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "C5H.IR", "name": "Cairn Homes plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "A5G.IR", "name": "AIB Group plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "BIRG.IR", "name": "Bank of Ireland Group plc", "region": "Ireland", "currency": "EUR"},
    {"ticker": "YZA.IR", "name": "Arytza", "region": "Ireland", "currency": "EUR"},
]

# --- Streamlit UI ---
st.title("📊 Stock Dashboard")
st.write("View stock prices with 5-day % change and year-to-date % change.")

date_str = st.date_input("Select date")

# Allow user to edit stock list
stock_options = {f"{s['name']} ({s['ticker']})": s for s in MASTER_STOCKS}
selected_labels = st.multiselect(
    "Select stocks to include:", list(stock_options.keys()), default=list(stock_options.keys())
)
SELECTED_STOCKS = [stock_options[label] for label in selected_labels]

if st.button("Run"):
    rows = []
    for stock in SELECTED_STOCKS:
        ticker = stock["ticker"]
        try:
            data = yf.download(
                ticker, start=f"{date_str.year}-01-01", end=date_str + timedelta(days=1), progress=False
            )
            if data.empty:
                continue

            valid_dates = data.index[data.index <= pd.to_datetime(date_str)]
            if len(valid_dates) == 0:
                continue
            sel_date = valid_dates[-1]

            price = float(data.loc[sel_date, "Close"])

            # 5-day % change
            past_dates = data.index[data.index <= sel_date - timedelta(days=5)]
            change_5d = None
            if len(past_dates) > 0:
                past_price = float(data.loc[past_dates[-1], "Close"])
                change_5d = (price - past_price) / past_price * 100

            # YTD % change
            ytd_price = float(data.iloc[0]["Close"])
            change_ytd = (price - ytd_price) / ytd_price * 100

            rows.append({
                "Company": stock["name"],
                "Region": stock["region"],
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

        # Display in Streamlit
        for (region, currency), gdf in grouped:
            st.subheader(f"{region} ({currency})")
            st.dataframe(gdf.drop(columns=["Region", "Currency"]), use_container_width=True)

        # --- CSV Output ---
        REGION_LABELS = {
            "Ireland": "Ireland (€)",
            "UK": "UK (£)",
            "Europe": "Europe (€)",
            "US": "US ($)"
        }

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        for region in ["Ireland", "UK", "Europe", "US"]:
            for (r, currency), gdf in grouped:
                if r != region:
                    continue
                # Write region header
                writer.writerow([REGION_LABELS[r], "Last price", "5D %change", "YTD % change"])
                # Write stock rows
                for _, row in gdf.iterrows():
                    company = row['Company'].replace('"', '')  # remove any quotes
                    price = f"{row['Price']:.1f}" if pd.notnull(row['Price']) else ""
                    c5 = f"{row['5D % Change']:.1f}" if pd.notnull(row['5D % Change']) else ""
                    cy = f"{row['YTD % Change']:.1f}" if pd.notnull(row['YTD % Change']) else ""
                    writer.writerow([company, price, c5, cy])

        csv_bytes = '\ufeff' + output.getvalue()  # UTF-8 BOM for Excel
        st.download_button("💾 Download CSV", csv_bytes, "stock_data.csv", "text/csv")
    else:
        st.warning("No stock data available for that date.")
