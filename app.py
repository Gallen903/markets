import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
from io import StringIO

st.set_page_config(page_title="Market Prices", layout="wide")

# ----------------------------
# Full default stock list
# ----------------------------
STOCKS = [
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

st.title("📊 Market Prices (Clean)")

col1, col2 = st.columns([1, 3])
with col1:
    selected_date = st.date_input("Select date", value=date.today())
run = st.button("Run")

@st.cache_data(show_spinner=False)
def fetch_history(ticker: str, start_dt: date, end_dt: date) -> pd.DataFrame:
    """
    Download OHLC data for ticker in calendar date window [start_dt, end_dt).
    Returns a DataFrame with a naive DatetimeIndex and 'Close' column.
    """
    df = yf.download(
        ticker,
        start=start_dt.isoformat(),
        end=(end_dt + timedelta(days=1)).isoformat(),
        progress=False,
        auto_adjust=False,
        actions=False,
        interval="1d",
    )
    if df.empty:
        return df
    # Ensure naive datetime index for comparisons
    idx = pd.to_datetime(df.index)
    try:
        idx = idx.tz_localize(None)
    except Exception:
        pass
    df.index = idx
    # Keep only rows with numeric close
    df = df[pd.to_numeric(df.get("Close"), errors="coerce").notna()]
    return df

def compute_row(stock: dict, target: date):
    """
    For a given stock and target date:
      - Find the closest available trading day <= target.
      - Compute Close price for that day.
      - Compute 5-trading-day percentage change if available.
    Returns dict or None if no price found.
    """
    # Pull ~21 calendar days to cover at least 5 trading sessions
    start_window = target - timedelta(days=28)
    end_window = target
    hist = fetch_history(stock["ticker"], start_window, end_window)
    if hist.empty:
        return None

    # latest trading day <= target
    available = hist.index[hist.index <= pd.to_datetime(target)]
    if len(available) == 0:
        return None
    d0 = available[-1]
    price = float(hist.loc[d0, "Close"])

    # Compute 5-trading-day change (use row position)
    idx_pos = hist.index.get_loc(d0)
    if isinstance(idx_pos, slice):
        # if get_loc returned slice (duplicate index safety) -> take last position of slice
        idx_pos = range(idx_pos.start, idx_pos.stop)[-1]
    if idx_pos >= 5:
        old_price = float(hist.iloc[idx_pos - 5]["Close"])
        if old_price and old_price != 0:
            pct_5d = (price / old_price - 1.0) * 100.0
        else:
            pct_5d = None
    else:
        pct_5d = None

    return {
        "exchange": stock["exchange"],
        "currency": stock["currency"],
        "ticker": stock["ticker"],
        "name": stock["name"],
        "date": d0.date().isoformat(),
        "price": round(price, 2),
        "5d %": (None if pct_5d is None else round(pct_5d, 1)),
    }

if run:
    results = []
    for s in STOCKS:
        try:
            row = compute_row(s, selected_date)
            if row:  # hide tickers with no price
                results.append(row)
        except Exception:
            # Skip noisy tickers silently
            continue

    if not results:
        st.warning("No data found for the selected date across your list.")
    else:
        df = pd.DataFrame(results)

        # Sort within each exchange by company name
        df = df.sort_values(by=["exchange", "name"]).reset_index(drop=True)

        # Display grouped sections
        for (ex, cur), group in df.groupby(["exchange", "currency"], sort=False):
            st.subheader(f"{ex} ({cur})")
            show = group[["name", "price", "5d %", "date"]].rename(
                columns={"name": "Company", "price": "Close", "5d %": "5-day %", "date": "Price date"}
            )
            # Format 5-day % as one decimal with % sign for display
            show["5-day %"] = show["5-day %"].apply(lambda v: ("—" if pd.isna(v) else f"{v:.1f}%"))
            st.dataframe(show, use_container_width=True)

        # CSV download of the full underlying data (includes tickers)
        csv_df = df.copy()
        # Format 5d % to one decimal in CSV, keep numeric
        csv_df["5d %"] = csv_df["5d %"].round(1)
        csv = csv_df[["exchange", "currency", "ticker", "name", "date", "price", "5d %"]].rename(
            columns={
                "exchange": "Exchange",
                "currency": "Currency",
                "ticker": "Ticker",
                "name": "Company",
                "date": "Price Date",
                "price": "Close",
                "5d %": "5d_Pct"
            }
        ).to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"prices_{selected_date.isoformat()}.csv",
            mime="text/csv"
        )
else:
    st.info("Pick a date and click **Run** to fetch prices.")
