import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- Full Default Stock List (including your custom additions) ---
DEFAULT_STOCKS = [
    {"ticker": "NTRB", "name": "Nutriband", "exchange": "NCM", "currency": "USD"},
    {"ticker": "DEO", "name": "Diageo", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "AER", "name": "AerCap Holdings", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "BRBY.L", "name": "Burberry", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "YZA.IR", "name": "Arytza", "exchange": "ISE", "currency": "EUR"},
    {"ticker": "SSPG.L", "name": "SSP Group", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "BKT.MC", "name": "Bankinter", "exchange": "BME", "currency": "EUR"},
    {"ticker": "ABF.L", "name": "Associated British Foods", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "GWMO.L", "name": "Great Western Mining Corp", "exchange": "LSE", "currency": "GBp"},
    {"ticker": "FLUT", "name": "Flutter Entertainment", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "AAPL", "name": "Apple", "exchange": "NMS", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft", "exchange": "NMS", "currency": "USD"},
    {"ticker": "META", "name": "Meta Platforms", "exchange": "NMS", "currency": "USD"},
    {"ticker": "GOOG", "name": "Alphabet", "exchange": "NMS", "currency": "USD"},
    {"ticker": "PFE", "name": "Pfizer", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "MRK", "name": "Merck & Co.", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "ORCL", "name": "Oracle", "exchange": "NYQ", "currency": "USD"},
    {"ticker": "AMGN", "name": "Amgen", "exchange": "NMS", "currency": "USD"},
    {"ticker": "INTC", "name": "Intel", "exchange": "NMS", "currency": "USD"},
    {"ticker": "PEP", "name": "PepsiCo", "exchange": "NMS", "currency": "USD"},
    {"ticker": "SBUX", "name": "Starbucks", "exchange": "NMS", "currency": "USD"},
]

# --- Streamlit UI ---
st.title("📊 Stock Dashboard")
st.write("View stock prices with 5-day % change and year-to-date % change.")

date_str = st.date_input("Select date")

if st.button("Run"):
    rows = []
    for stock in DEFAULT_STOCKS:
        ticker = stock["ticker"]
        try:
            data = yf.download(ticker, start=f"{date_str.year}-01-01", end=date_str + timedelta(days=1))

            if data.empty:
                continue

            # Get the last available trading day on/before the chosen date
            valid_dates = data.index[data.index <= pd.to_datetime(date_str)]
            if len(valid_dates) == 0:
                continue
            sel_date = valid_dates[-1]
            price = float(data.loc[sel_date, "Close"].iloc[0] if isinstance(data.loc[sel_date, "Close"], pd.Series) else data.loc[sel_date, "Close"])

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
                "Exchange": stock["exchange"],
                "Currency": stock["currency"],
                "Price": round(price, 1),
                "5D % Change": round(change_5d, 1) if change_5d is not None else None,
                "YTD % Change": round(change_ytd, 1),
            })

        except Exception as e:
            continue

    if rows:
        df = pd.DataFrame(rows).sort_values(by=["Exchange", "Company"])
        grouped = df.groupby(["Exchange", "Currency"])

        for (exchange, currency), gdf in grouped:
            st.subheader(f"{exchange} ({currency})")
            st.dataframe(gdf.drop(columns=["Exchange", "Currency"]), use_container_width=True)

        # CSV download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Download CSV", csv, "stock_data.csv", "text/csv")
    else:
        st.warning("No stock data available for that date.")
