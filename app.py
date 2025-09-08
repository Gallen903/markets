import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, date
import sqlite3
import io
import csv
from pathlib import Path

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
            region TEXT NOT NULL,   -- Ireland | UK | Europe | US
            currency TEXT NOT NULL  -- EUR | GBp | USD
        )
    """)
    # Only seed if empty
    cur.execute("SELECT COUNT(*) FROM stocks")
    if cur.fetchone()[0] == 0:
        defaults = [
            # --- US ---
            ("STT","State Street Corporation","US","USD"),
            ("PFE","Pfizer Inc.","US","USD"),
            ("SBUX","Starbucks Corporation","US","USD"),
            ("PEP","PepsiCo, Inc.","US","USD"),
            ("ORCL","Oracle Corporation","US","USD"),
            ("NVS","Novartis AG","US","USD"),
            ("META","Meta Platforms, Inc.","US","USD"),
            ("MSFT","Microsoft Corporation","US","USD"),
            ("MRK","Merck & Co., Inc.","US","USD"),
            ("JNJ","Johnson & Johnson","US","USD"),
            ("INTC","Intel Corporation","US","USD"),
            ("ICON","Icon Energy Corp.","US","USD"),
            ("HPQ","HP Inc.","US","USD"),
            ("GE","GE Aerospace","US","USD"),
            ("LLY","Eli Lilly and Company","US","USD"),
            ("EBAY","eBay Inc.","US","USD"),
            ("COKE","Coca-Cola Consolidated, Inc.","US","USD"),
            ("BSX","Boston Scientific Corporation","US","USD"),
            ("AAPL","Apple Inc.","US","USD"),
            ("AMGN","Amgen Inc.","US","USD"),
            ("ADI","Analog Devices, Inc.","US","USD"),
            ("ABBV","AbbVie Inc.","US","USD"),
            ("GOOG","Alphabet Inc.","US","USD"),
            ("ABT","Abbott Laboratories","US","USD"),
            ("CRH","CRH plc","US","USD"),
            ("SW","Smurfit Westrock Plc","US","USD"),
            ("DEO","Diageo","US","USD"),
            ("AER","AerCap Holdings","US","USD"),
            ("FLUT","Flutter Entertainment plc","US","USD"),

            # --- Europe (non-UK, non-Ireland) ---
            ("HEIA.AS","Heineken N.V.","Europe","EUR"),
            ("BSN.F","Danone S.A.","Europe","EUR"),
            ("BKT.MC","Bankinter","Europe","EUR"),

            # --- UK ---
            ("VOD.L","Vodafone Group","UK","GBp"),
            ("DCC.L","DCC plc","UK","GBp"),
            ("GNCL.XC","Greencore Group plc","UK","GBp"),
            ("GFTUL.XC","Grafton Group plc","UK","GBp"),
            ("HVO.L","hVIVO plc","UK","GBp"),
            ("POLB.L","Poolbeg Pharma PLC","UK","GBp"),
            ("TSCOL.XC","Tesco plc","UK","GBp"),
            ("BRBY.L","Burberry","UK","GBp"),
            ("SSPG.L","SSP Group","UK","GBp"),
            ("ABF.L","Associated British Foods","UK","GBp"),
            ("GWMO.L","Great Western Mining Corp","UK","GBp"),

            # --- Ireland ---
            ("GVR.IR","Glenveagh Properties PLC","Ireland","EUR"),
            ("UPR.IR","Uniphar plc","Ireland","EUR"),
            ("RYA.IR","Ryanair Holdings plc","Ireland","EUR"),
            ("PTSB.IR","Permanent TSB Group Holdings plc","Ireland","EUR"),
            ("OIZ.IR","Origin Enterprises plc","Ireland","EUR"),
            ("MLC.IR","Malin Corporation plc","Ireland","EUR"),
            ("KRX.IR","Kingspan Group plc","Ireland","EUR"),
            ("KRZ.IR","Kerry Group plc","Ireland","EUR"),
            ("KMR.IR","Kenmare Resources plc","Ireland","EUR"),
            ("IRES.IR","Irish Residential Properties REIT Plc","Ireland","EUR"),
            ("IR5B.IR","Irish Continental Group plc","Ireland","EUR"),
            ("HSW.IR","Hostelworld Group plc","Ireland","EUR"),
            ("GRP.IR","Greencoat Renewables","Ireland","EUR"),
            ("GL9.IR","Glanbia plc","Ireland","EUR"),
            ("EG7.IR","FBD Holdings plc","Ireland","EUR"),
            ("DQ7A.IR","Donegal Investment Group plc","Ireland","EUR"),
            ("DHG.IR","Dalata Hotel Group plc","Ireland","EUR"),
            ("C5H.IR","Cairn Homes plc","Ireland","EUR"),
            ("A5G.IR","AIB Group plc","Ireland","EUR"),
            ("BIRG.IR","Bank of Ireland Group plc","Ireland","EUR"),
            ("YZA.IR","Arytza","Ireland","EUR"),
        ]
        cur.executemany("INSERT INTO stocks (ticker,name,region,currency) VALUES (?,?,?,?)", defaults)
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
# Finance helpers (timezone-aware)
# -----------------------------
# Column selector: Yahoo (price return) uses 'Close'; total return uses 'Adj Close'
def _col(use_price_return: bool) -> str:
    return "Close" if use_price_return else "Adj Close"

def _exchange_tz(ticker: str) -> str:
    """Best-effort exchange timezone; fallback UTC."""
    try:
        tz = yf.Ticker(ticker).fast_info.get("timezone")
        return tz or "UTC"
    except Exception:
        return "UTC"

def _to_local_tz(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    """Ensure index is tz-aware and converted to the exchange's local tz."""
    if df.empty:
        return df
    # Daily data from yfinance is often tz-naive; assume UTC then convert.
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    return df.tz_convert(tz)

def last_trading_close_on_or_before(tkr_hist: pd.DataFrame, target_dt: pd.Timestamp, use_price_return: bool, tz: str):
    if tkr_hist.empty:
        return None, None
    hist_local = _to_local_tz(tkr_hist, tz)
    target_local_eod = pd.Timestamp(target_dt).tz_localize(tz) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    idx = hist_local.index[hist_local.index <= target_local_eod]
    if len(idx) == 0:
        return None, None
    dt_local = idx[-1]
    return float(hist_local.loc[dt_local, _col(use_price_return)]), dt_local

def close_n_trading_days_ago(tkr_hist: pd.DataFrame, ref_dt_local: pd.Timestamp, n: int, use_price_return: bool, tz: str):
    if tkr_hist.empty:
        return None
    hist_local = _to_local_tz(tkr_hist, tz)
    idx = hist_local.index[hist_local.index <= ref_dt_local]
    if len(idx) <= n:
        return None
    past_dt_local = idx[-(n+1)]
    return float(hist_local.loc[past_dt_local, _col(use_price_return)])

def ytd_baseline_from_hist(tkr_hist: pd.DataFrame, year: int, use_price_return: bool, tz: str):
    """Pick last trading close strictly before Jan 1 (LOCAL exchange time)."""
    if tkr_hist.empty:
        return None
    hist_local = _to_local_tz(tkr_hist, tz)
    cutoff_local = pd.Timestamp(f"{year}-01-01").tz_localize(tz)
    idx = hist_local.index[hist_local.index < cutoff_local]
    if len(idx) == 0:
        return None
    last_prev_year_local = idx[-1]
    return float(hist_local.loc[last_prev_year_local, _col(use_price_return)])

def prior_year_last_close(ticker: str, target_year: int, use_price_return: bool):
    """Fallback only (UTC-based window)."""
    start = f"{target_year-1}-12-01"
    end   = f"{target_year}-01-10"
    hist = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if hist.empty:
        return None
    idx = hist.index[hist.index.year == (target_year - 1)]
    if len(idx) == 0:
        return float(hist.iloc[0][_col(use_price_return)])
    return float(hist.loc[idx[-1], _col(use_price_return)])

def currency_symbol(cur: str) -> str:
    return {"USD": "$", "EUR": "€", "GBp": "£"}.get(cur, "")

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Stock Dashboard", layout="wide")
st.title("📊 Stock Dashboard")
st.caption("Last price, 5-day % change, YTD % change (YTD uses prior-year last trading close).")

# Toggle: Yahoo-style (Close) vs total return (Adj Close)
use_price_return = st.toggle(
    "Match Yahoo Finance numbers (use Close → price return)",
    value=True,
    help="ON = Yahoo-style price return (Close). OFF = total return using Adj Close (dividends & splits)."
)

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
            tz = _exchange_tz(tkr)

            # Start mid-Dec prior year so the baseline candle exists in LOCAL time; extend +7 days after target
            hist = yf.download(
                tkr,
                start=f"{selected_date.year-1}-12-15",
                end=selected_date + timedelta(days=7),
                progress=False,
                auto_adjust=False,
            )
            if hist.empty:
                continue

            price, p_dt_local = last_trading_close_on_or_before(hist, target_dt, use_price_return, tz)
            if price is None:
                continue

            c_5ago = close_n_trading_days_ago(hist, p_dt_local, 5, use_price_return, tz)
            chg_5d = None
            if c_5ago is not None and c_5ago != 0:
                chg_5d = (price - c_5ago) / c_5ago * 100.0

            # YTD baseline from SAME frame using LOCAL cutoff (fixes IE/EU drift)
            base = ytd_baseline_from_hist(hist, selected_date.year, use_price_return, tz)
            if base is None:
                # Fallbacks (rare)
                base = prior_year_last_close(tkr, selected_date.year, use_price_return)
                if base is None and not hist.empty:
                    jan1_local = pd.Timestamp(f"{selected_date.year}-01-01").tz_localize(tz)
                    hist_local = _to_local_tz(hist, tz)
                    later_idx = hist_local.index[hist_local.index >= jan1_local]
                    if len(later_idx) > 0:
                        base = float(hist_local.loc[later_idx[0], _col(use_price_return)])

            chg_ytd = (price - base) / base * 100.0 if base else None

            rows.append({
                "Company": s["name"],
                "Region": s["region"],
                "Currency": s["currency"],
                "Price": round(price, 1),
                "5D % Change": round(chg_5d, 1) if chg_5d is not None else None,
                "YTD % Change": round(chg_ytd, 1) if chg_ytd is not None else None,
            })
        except Exception:
            continue

    if not rows:
        st.warning("No stock data available for that date.")
    else:
        df = pd.DataFrame(rows).sort_values(by=["Region", "Company"]).reset_index(drop_by=True if hasattr(pd.DataFrame, "reset_index") else False)
        if "index" in df.columns:
            df = df.drop(columns=["index"])  # compatibility for older pandas

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
