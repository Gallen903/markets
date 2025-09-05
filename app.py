import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, date
import sqlite3
import io
import csv

DB_PATH = "stocks.db"

# -----------------------------
# SQLite helpers
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db_with_defaults():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            name   TEXT NOT NULL,
            region TEXT NOT NULL,
            currency TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def db_all_stocks():
    conn = get_conn()
    df = pd.read_sql_query("SELECT ticker,name,region,currency FROM stocks", conn)
    conn.close()
    return df

def db_add_stock(ticker, name, region, currency):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO stocks (ticker,name,region,currency) VALUES (?,?,?,?)",
                (ticker.strip(), name.strip(), region, currency))
    conn.commit()
    conn.close()

def db_remove_stocks(tickers):
    if not tickers:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany("DELETE FROM stocks WHERE ticker = ?", [(t,) for t in tickers])
    conn.commit()
    conn.close()

# -----------------------------
# Finance helpers
# -----------------------------
def last_trading_close_on_or_before(tkr_hist: pd.DataFrame, target_dt: pd.Timestamp):
    if tkr_hist.empty:
        return None, None
    idx = tkr_hist.index[tkr_hist.index <= target_dt]
    if len(idx) == 0:
        return None, None
    dt = idx[-1]
    return float(tkr_hist.loc[dt, "Close"]), dt

def close_n_trading_days_ago(tkr_hist: pd.DataFrame, ref_dt: pd.Timestamp, n: int):
    if tkr_hist.empty:
        return None
    idx = tkr_hist.index[tkr_hist.index <= ref_dt]
    if len(idx) <= n:
        return None
    past_dt = idx[-(n+1)]
    return float(tkr_hist.loc[past_dt, "Close"])

def prior_year_last_close(ticker: str, target_year: int):
    start = f"{target_year-1}-12-01"
    end   = f"{target_year}-01-02"
    hist = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if hist.empty:
        return None
    cutoff = pd.Timestamp(f"{target_year}-01-01")
    idx = hist.index[hist.index < cutoff]
    if len(idx) == 0:
        return float(hist.iloc[0]["Close"])
    return float(hist.loc[idx[-1], "Close"])

def currency_symbol(cur: str) -> str:
    return {"USD": "$", "EUR": "€", "GBp": "£"}.get(cur, "")

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Stock Dashboard", layout="wide")
st.title("📊 Stock Dashboard")
st.caption("Last price, 5-day % change, YTD % change (Yahoo YTD if available).")

init_db_with_defaults()
stocks_df = db_all_stocks()

colA, colB = st.columns([1,1])
with colA:
    selected_date = st.date_input("Select date", value=date.today())
with colB:
    st.write(" ")
    run = st.button("Run")

# Editor: add/remove stocks
with st.expander("➕ Add or ➖ remove stocks (saved to SQLite)"):
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("**Add a stock**")
        a_ticker = st.text_input("Ticker (e.g., AAPL, HEIA.AS)")
        a_name   = st.text_input("Company name")
        a_region = st.selectbox("Region", ["Ireland", "UK", "Europe", "US"])
        a_curr   = st.selectbox("Currency", ["EUR", "GBp", "USD"])
        if st.button("Add / Update"):
            if a_ticker and a_name:
                db_add_stock(a_ticker, a_name, a_region, a_curr)
                st.success(f"Saved {a_name} ({a_ticker})")
            else:
                st.warning("Please provide at least Ticker and Company name.")
    with c2:
        st.markdown("**Remove stocks**")
        rem_choices = [f"{r['name']} ({r['ticker']})" for _, r in stocks_df.sort_values("name").iterrows()]
        rem_sel = st.multiselect("Select to remove", rem_choices, [])
        if st.button("Remove selected"):
            tickers = [s[s.rfind("(")+1:-1] for s in rem_sel]
            db_remove_stocks(tickers)
            st.success(f"Removed {len(tickers)} stock(s)")

# Stock selection for this run
stocks_df = db_all_stocks()
stock_options = {f"{r['name']} ({r['ticker']})": dict(r) for _, r in stocks_df.iterrows()}
sel_labels = st.multiselect(
    "Stocks to include in this run:",
    list(stock_options.keys()),
    default=list(stock_options.keys())
)
selected_stocks = [stock_options[label] for label in sel_labels]

# -----------------------------
# Run calculation
# -----------------------------
if run:
    rows = []
    target_dt = pd.to_datetime(selected_date)

    for s in selected_stocks:
        tkr = s["ticker"]
        try:
            hist = yf.download(
                tkr,
                start=f"{selected_date.year}-01-01",
                end=selected_date + timedelta(days=1),
                progress=False,
                auto_adjust=False,
            )
            if hist.empty:
                continue

            price, p_dt = last_trading_close_on_or_before(hist, target_dt)
            if price is None:
                continue

            c_5ago = close_n_trading_days_ago(hist, p_dt, 5)
            chg_5d = None
            if c_5ago is not None and c_5ago != 0:
                chg_5d = (price - c_5ago) / c_5ago * 100.0

            # --- Yahoo YTD Return ---
            ytd_return = None
            try:
                info = yf.Ticker(tkr).info
                if "ytdReturn" in info and info["ytdReturn"] is not None:
                    ytd_return = info["ytdReturn"] * 100.0
            except Exception:
                pass

            # fallback if Yahoo YTD missing
            if ytd_return is None:
                base = prior_year_last_close(tkr, selected_date.year)
                if base is None:
                    base = float(hist.iloc[0]["Close"])
                ytd_return = (price - base) / base * 100.0 if base else None

            rows.append({
                "Company": s["name"],
                "Region": s["region"],
                "Currency": s["currency"],
                "Price": round(price, 1),
                "5D % Change": round(chg_5d, 1) if chg_5d is not None else None,
                "YTD % Change": round(ytd_return, 1) if ytd_return is not None else None,
            })
        except Exception:
            continue

    if not rows:
        st.warning("No stock data available for that date.")
    else:
        df = pd.DataFrame(rows).sort_values(by=["Region", "Company"]).reset_index(drop=True)

        region_order = ["Ireland", "UK", "Europe", "US"]
        df["Region"] = pd.Categorical(df["Region"], categories=region_order, ordered=True)
        df = df.sort_values(["Region", "Company"])

        for region in region_order:
            g = df[df["Region"] == region]
            if g.empty:
                continue
            currs = g["Currency"].unique().tolist()
            curr_label = " / ".join(currency_symbol(c) for c in currs if currency_symbol(c))
            header = f"{region} ({curr_label})" if curr_label else region
            st.subheader(header)
            st.dataframe(g.drop(columns=["Region", "Currency"]), use_container_width=True)

        # CSV export
        REGION_LABELS = {
            "Ireland": f"Ireland ({currency_symbol('EUR')})",
            "UK":      f"UK ({currency_symbol('GBp')})",
            "Europe":  f"Europe ({currency_symbol('EUR')})",
            "US":      f"US ({currency_symbol('USD')})",
        }

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        for region in region_order:
            g = df[df["Region"] == region]
            if g.empty:
                continue
            writer.writerow([REGION_LABELS[region], "Last price", "5D %change", "YTD % change"])
            for _, row in g.iterrows():
                company = (row["Company"] or "").replace(",", "")
                price = f"{row['Price']:.1f}" if pd.notnull(row["Price"]) else ""
                c5 = f"{row['5D % Change']:.1f}" if pd.notnull(row["5D % Change"]) else ""
                cy = f"{row['YTD % Change']:.1f}" if pd.notnull(row["YTD % Change"]) else ""
                writer.writerow([company, price, c5, cy])

        csv_bytes = "\ufeff" + output.getvalue()
        st.download_button("💾 Download CSV", csv_bytes, "stock_data.csv", "text/csv")
