# --- Section 2: Download specific share price data ---
st.header("🔎 Look Up Specific Stock Price(s)")

stock_label = st.selectbox("Select stock:", list(stock_options.keys()))
selected_stock = stock_options[stock_label]

mode = st.radio("Choose mode:", ["Single Date", "Date Range"])

if mode == "Single Date":
    query_date = st.date_input("Select date", datetime.today())
    if st.button("Get Price"):
        data = yf.download(selected_stock["ticker"], 
                           start=query_date, 
                           end=query_date + timedelta(days=1), 
                           progress=False)
        if not data.empty:
            price = round(float(data["Close"].iloc[-1]), 2)
            st.write(f"**{selected_stock['name']}** closing price on {query_date}: {price} {selected_stock['currency']}")
            # CSV download
            csv = f"Date,Price\n{query_date},{price}".encode("utf-8")
            st.download_button("💾 Download Price CSV", csv, f"{selected_stock['ticker']}_price.csv", "text/csv")
        else:
            st.warning("No data available for that date.")

else:  # Date Range
    start_date = st.date_input("Start date", datetime.today() - timedelta(days=30))
    end_date = st.date_input("End date", datetime.today())
    if st.button("Get Prices"):
        data = yf.download(selected_stock["ticker"], 
                           start=start_date, 
                           end=end_date + timedelta(days=1), 
                           progress=False)
        if not data.empty:
            df = data[["Close"]].reset_index()
            df["Close"] = df["Close"].round(2)
            st.dataframe(df, use_container_width=True)
            # CSV download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("💾 Download Price History CSV", csv, f"{selected_stock['ticker']}_history.csv", "text/csv")
        else:
            st.warning("No data available for that period.")
