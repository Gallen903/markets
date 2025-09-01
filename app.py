import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
import io

# -----------------------
# Master stock dictionary
# -----------------------
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
        ("Smurfit WestRock Plc", "SWR.L"),
        ("Diageo", "DGE.L"),
        ("CRH plc", "CRH.L"),
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

REGION_ORDER = ["Ireland", "UK", "Europe", "US"]

# -----------------------
# Data fetcher
# -----------------------
def fetch_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="ytd")

        if hist.empty:
            return None, None, None

        last_price = hist["Close"].iloc[-1]

        # Weekly change
        if len(hist) > 5:
            week_ago = hist["Close"].iloc[-6]
        else:
            week_ago = hist["Close"].iloc[0]
        week_change = ((last_price - week_ago) / week_ago) * 100

        # YTD change
        start_price = hist["Close"].iloc[0]
        ytd_change = ((last_price - start_price) / start_price) * 100

        return round(last_price, 1), round(week_change, 1), round(ytd_change, 1)
    except:
        return None, None, None

# -----------------------
# App layout
# -----------------------
st.title("Stock Dashboard")

if "selected_stocks" not in st.session_state:
    st.session_state.selected_stocks = MASTER_STOCKS

if st.sidebar.button("Edit stock list"):
    st.session_state.selected_stocks = {}

    for region, stocks in MASTER_STOCKS.items():
        selected = st.sidebar.multiselect(f"Select {region} stocks", [s[0] for s in stocks], [s[0] for s in stocks])
        st.session_state.selected_stocks[region] = [(name, ticker) for name, ticker in stocks if name in selected]

# -----------------------
# Build DataFrame
# -----------------------
rows = []
for region in REGION_ORDER:
    for name, ticker in st.session_state.selected_stocks.get(region, []):
        price, week_change, ytd_change = fetch_stock_data(ticker)
        if price is not None:
            rows.append((region, name, price, week_change, ytd_change))

df = pd.DataFrame(rows, columns=["Region", "Name", "Last price", "5D %change", "YTD % change"])

# -----------------------
# Display by region
# -----------------------
for region in REGION_ORDER:
    region_df = df[df["Region"] == region].drop(columns=["Region"])
    if not region_df.empty:
        st.subheader(region)
        st.dataframe(region_df.set_index("Name"))

# -----------------------
# CSV export
# -----------------------
def format_csv(df):
    output = io.StringIO()

    for region in REGION_ORDER:
        region_df = df[df["Region"] == region].drop(columns=["Region"])
        if not region_df.empty:
            if region == "Ireland":
                header = "Ireland (EUR)\tLast price\t5D %change\tYTD % change\n"
            elif region == "UK":
                header = "UK (£)\tLast price\t5D %change\tYTD % change\n"
            elif region == "Europe":
                header = "Europe (€)\tLast price\t5D %change\tYTD % change\n"
            elif region == "US":
                header = "US ($)\tLast price\t5D %change\tYTD % change\n"
            output.write(header)
            region_df.to_csv(output, sep="\t", index=False, header=False)
    return output.getvalue()

csv_data = format_csv(df)
st.download_button("Download CSV", csv_data, "stocks.csv", "text/csv")
