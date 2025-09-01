import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import io
import csv

# --- Full Stock Master List ---
MASTER_STOCKS = {
    "Ireland": [
        ("AIB Group plc", "A5G.IR"),
        ("Bank of Ireland Group plc", "BIRG.IR"),
        ("Cairn Homes plc", "CRN.IR"),
        ("Dalata Hotel Group plc", "DHG.IR"),
        ("Donegal Investment Group plc", "DQ7A.IR"),
        ("FBD Holdings plc", "EG7.IR"),
        ("Glanbia plc", "GL9.IR"),
        ("Glenveagh Properties PLC", "GVV.IR"),
        ("Greencoat Renewables", "GRP.IR"),
        ("Hostelworld Group plc", "HSW.IR"),
        ("Irish Continental Group plc", "IR5B.IR"),
        ("Irish Residential Properties REIT Plc", "IRES.IR"),
        ("Kenmare Resources plc", "KMR.IR"),
        ("Kerry Group plc", "KRZ.IR"),
        ("Kingspan Group plc", "KRX.IR"),
        ("Malin Corporation plc", "MLC.IR"),
        ("Origin Enterprises plc", "OIZ.IR"),
        ("Permanent TSB Group Holdings plc", "IL0A.IR"),
        ("Ryanair Holdings plc", "RYA.IR"),
        ("Uniphar plc", "UPR.IR"),
    ],

    "UK": [
        ("Associated British Foods", "ABF.L"),
        ("Burberry", "BRBY.L"),
        ("DCC plc", "DCC.L"),
        ("Grafton Group plc", "GFTU.L"),
        ("Great Western Mining Corp", "GWMO.L"),
        ("Greencore Group plc", "GNC.L"),
        ("Poolbeg Pharma PLC", "POLB.L"),
        ("SSP Group", "SSPG.L"),
        ("Tesco plc", "TSCO.L"),
        ("Vodafone Group", "VOD.L"),
        ("hVIVO plc", "HVO.L"),
        # Smurfit WestRock – London listing
        ("Smurfit WestRock Plc", "SWR.L"),
        # Diageo – London ticker (DGE.L) instead of US ADR (DEO)
        ("Diageo", "DGE.L"),
        # CRH – London ticker (CRH.L) instead of US (CRH)
        ("CRH plc", "CRH.L"),
        # Flutter – NY ticker is FLUT, London is FLTR.L → keeping London here
        ("Flutter Entertainment plc", "FLTR.L"),
    ],

    "Europe": [
        ("Bankinter", "BKT.MC"),
        ("Danone S.A.", "BN.PA"),
        ("Heineken N.V.", "HEIA.AS"),
    ],

    "US": [
        ("AbbVie Inc.", "ABBV"),
        ("Abbott Laboratories", "ABT"),
        ("AerCap Holdings", "AER"),
        ("Alphabet Inc.", "GOOG"),
        ("Amgen Inc.", "AMGN"),
        ("Analog Devices, Inc.", "ADI"),
        ("Apple Inc.", "AAPL"),
        ("Boston Scientific Corporation", "BSX"),
        ("Coca-Cola Consolidated, Inc.", "COKE"),
        ("Eli Lilly and Company", "LLY"),
        ("GE Aerospace", "GE"),
        ("HP Inc.", "HPQ"),
        ("Icon Energy Corp.", "ICNR"),  # ⚠️ Please confirm if this is correct
        ("Intel Corporation", "INTC"),
        ("Johnson & Johnson", "JNJ"),
        ("Merck & Co., Inc.", "MRK"),
        ("Meta Platforms, Inc.", "META"),
        ("Microsoft Corporation", "MSFT"),
        ("Novartis AG", "NVS"),
        ("Oracle Corporation", "ORCL"),
        ("PepsiCo, Inc.", "PEP"),
        ("Pfizer Inc.", "PFE"),
        ("Starbucks Corporation", "SBUX"),
        ("State Street Corporation", "STT"),
        ("eBay Inc.", "EBAY"),
    ]
}


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
