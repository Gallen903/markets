import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Stock Price Lookup", page_icon="📈", layout="wide")

st.title("📊 Stock Price Lookup with 5-Day Change")

# User inputs
tickers_input = st.text_input(
    "Enter stock tickers (comma separated)", 
    "AAPL,MSFT,GOOG"
)

date_input = st.date_input(
    "Select date", 
    datetime.today() - timedelta(days=1)
)

if st.button("Get Prices"):
    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]
    if not tickers:
        st.error("Please enter at least one ticker.")
    else:
        try:
            # Download 6 days of data (to ensure we capture 5 trading days)
            start_date = date_input - timedelta(days=7)
            end_date = date_input + timedelta(days=1)
            data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=False)

            results = []
            for ticker in tickers:
                try:
                    df = data[ticker] if len(tickers) > 1 else data
                    df = df.reset_index()
                    df["Date"] = pd.to_datetime(df["Date"]).dt.date
                    
                    # Closing price on selected date
                    close_row = df[df["Date"] == date_input]
                    if close_row.empty:
                        st.warning(f"No data found for {ticker} on {date_input}. Skipping...")
                        continue
                    close_price = close_row["Close"].values[0]

                    # Closing price 5 trading days earlier
                    prev_df = df[df["Date"] < date_input]
                    if len(prev_df) >= 5:
                        prev_close = prev_df.iloc[-5]["Close"]
                        pct_change = ((close_price - prev_close) / prev_close) * 100
                    else:
                        pct_change = None

                    # Company name from yfinance
                    info = yf.Ticker(ticker).info
                    company_name = info.get("shortName", ticker)

                    results.append({
                        "Company": company_name,
                        "Ticker": ticker,
                        "Close Price": round(close_price, 2),
                        "5-Day % Change": round(pct_change, 2) if pct_change is not None else None
                    })
                except Exception as e:
                    st.error(f"Error processing {ticker}: {e}")

            if results:
                df_results = pd.DataFrame(results)
                st.dataframe(df_results)
                csv = df_results.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"stock_prices_{date_input}.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Error fetching data: {e}")
