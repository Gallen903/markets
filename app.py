import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from yahooquery import Ticker
from datetime import datetime, timedelta
import csv
import os

DB_FILE = "stocks.db"

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stocks
                 (ticker TEXT PRIMARY KEY, name TEXT, region TEXT, currency TEXT)''')
    conn.commit()
    conn.close()

def load_stocks():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT ticker, name, region, currency FROM stocks")
    rows = c.fetchall()
    conn.close()
    return [{"ticker": r[0], "name": r[1], "region": r[2], "currency": r[3]} for r in rows]

def save_stock(ticker, name, region, currency):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO stocks VALUES (?, ?, ?, ?)", (ticker, name, region, currency))
    conn.commit()
    conn.close()

def remove_stock(ticker):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM stocks WHERE ticker=?", (ticker,))
    conn.commit()
    conn.close()

# --- Finance data fetching ---
def fetch_stock_data(ticker, name, region, currency, start_date, end_date):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            return None

        last_price = hist["Close"].iloc[-1]

        # --- 5D change (adjusted close) ---
        five_days_ago = hist.index[-1] - timedelta(days=7)
        hist_5d = hist[hist.index >= five_days_ago]
        if len(hist_5d) > 1:
            five_day_change = ((hist_5d["Close"].iloc[-1] / hist_5d["Close"].iloc[0]) - 1) * 100
        else:
            five_day_change = None

        # --- YTD change (via yahooquery, matches Yahoo site exactly) ---
        yq = Ticker(ticker)
        summary = yq.summary_detail
        try:
            ytd_return = summary[ticker].get("ytdReturn", None)
            if ytd_return is not None:
                ytd_change = ytd_return * 100
            else:
                ytd_change = None
        except Exception:
            ytd_change = None

        return {
            "Region": region,
            "Name": name,
            "Last price": f"{last_price:.1f}",
            "5D %change": f"{five_day_change:.1f}" if five_day_change is not None else "N/A",
            "YTD % change": f"{ytd_change:.1f}" if ytd_change is not None else "N/A",
            "Currency": currency
        }
    except Exception:
        return None

# --- CSV export ---
def export_to_csv(data, filename="stock_data.csv"):
    regions = ["Ireland", "UK", "Europe", "US"]
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter="\t")

        for region in regions:
            region_data = [row for row in data if row["Region"] == region]
            if region_data:
                writer.writerow([f"{region} ({region_data[0]['Currency']})", "Last price", "5D %change", "YTD % change"])
                for row in region_data:
                    writer.writerow([
                        row["Name"],
                        row["Last price"],
                        row["5D %change"],
                        row["YTD % change"]
                    ])

# --- Streamlit UI ---
def main():
    st.title("Stock Performance Dashboard")

    init_db()
    stocks = load_stocks()

    start_date = st.sidebar.date_input("Start Date", datetime(datetime.today().year, 1, 1))
    end_date = st.sidebar.date_input("End Date", datetime.today())

    # Add stock
    st.sidebar.header("Add Stock")
    ticker = st.sidebar.text_input("Ticker")
    name = st.sidebar.text_input("Name")
    region = st.sidebar.selectbox("Region", ["Ireland", "UK", "Europe", "US"])
    currency = st.sidebar.selectbox("Currency", ["€", "£", "$"])
    if st.sidebar.button("Add/Update Stock"):
        if ticker and name:
            save_stock(ticker, name, region, currency)
            st.sidebar.success(f"Added/Updated {name} ({ticker})")

    # Remove stock
    st.sidebar.header("Remove Stock")
    all_tickers = [s["ticker"] for s in stocks]
    ticker_to_remove = st.sidebar.selectbox("Select ticker to remove", [""] + all_tickers)
    if st.sidebar.button("Remove Stock") and ticker_to_remove:
        remove_stock(ticker_to_remove)
        st.sidebar.success(f"Removed {ticker_to_remove}")

    # Fetch data
    if st.button("Fetch Data"):
        data = []
        for stock in stocks:
            stock_data = fetch_stock_data(stock["ticker"], stock["name"], stock["region"], stock["currency"], start_date, end_date)
            if stock_data:
                data.append(stock_data)

        if data:
            df = pd.DataFrame(data)
            st.dataframe(df)

            export_to_csv(data)
            st.success("Data exported to stock_data.csv")
        else:
            st.warning("No data found for the selected stocks.")

if __name__ == "__main__":
    main()
