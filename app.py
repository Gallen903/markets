import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, date
import sqlite3
import io
import csv
from pathlib import Path
from typing import Optional

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
    # Seed defaults without overwriting user entries (idempotent)
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
    cur.executemany(
        "INSERT OR IGNORE INTO stocks (ticker,name,region,currency) VALUES (?,?,?,?)",
        defaults
    )
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
# Finance helpers (session-date based; no tz math)
# -----------------------------
def _col(use_price_return: bool) -> str:
    # Yahoo site YTD == price return => use 'Close'; 'Adj Close' for total return
    return "Close" if use_price_return else "Adj Close"

def _session_dates_index(df: pd.DataFrame) -> np.ndarray:
    """Return an array of date() objects corresponding to each row (treat rows as local session dates)."""
    idx = pd.to_datetime(df.index)
    return np.array([d.date() for d in idx], dtype=object)

def last_close_on_or_before_date(df: pd.DataFrame, target_date: date, use_price_return: bool):
    """Get last session's price on/before target_date using the chosen column."""
    if df.empty:
        return None, None
    dates = _session_dates_index(df)
    mask = dates <= target_date
    if not mask.any():
        return None, None
    pos = np.where(mask)[0][-1]
    return float(df.iloc[pos][_col(use_price_return)]), pos

def close_n_trading_days_ago_by_pos(df: pd.DataFrame, pos: int, n: int, use_price_return: bool):
    """Get price n sessions before a given position."""
    if df.empty or pos is None:
        return None
    ref_pos = pos - n
    if ref_pos < 0:
        return None
    return float(df.iloc[ref_pos][_col(use_price_return)])

# --- Baseline (policy): Euronext pre-holiday vs last trading day ---
EURONEXT_TZS = {
    # used only as a venue hint; we don't actually convert tz now
    "Europe/Dublin", "Europe/Paris", "Europe/Amsterdam", "Europe/Brussels",
    "Europe/Lisbon", "Europe/Oslo", "Europe/Rome"
}

def _exchange_tz(ticker: str) -> str:
    """Best-effort exchange timezone; fallback 'UTC' (used only to decide Euronext policy)."""
    try:
        tz = yf.Ticker(ticker).fast_info.get("timezone")
        return tz or "UTC"
    except Exception:
        return "UTC"

def ytd_baseline_from_hist_policy(df: pd.DataFrame, year: int, use_price_return: bool, is_euronext_like: bool):
    """Pick the baseline row by session date only (no tz)."""
    if df.empty:
        return None
    dates = _session_dates_index(df)
    if is_euronext_like:
        cutoff = date(year - 1, 12, 27)   # mirror Yahoo EU behavior you observed
        mask = dates <= cutoff
    else:
        cutoff = date(year - 1, 12, 31)   # standard: last session of the year
        mask = dates <= cutoff
    if not mask.any():
        return None
    pos = np.where(mask)[0][-1]
    return float(df.iloc[pos][_col(use_price_return)])

def prior_year_last_close(ticker: str, target_year: int, use_price_return: bool):
    """Fallback only; not usually needed now."""
    start = f"{target_year-1}-12-01"
    end   = f"{target_year}-01-10"
    hist = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if hist.empty:
        return None
    # pick last session in prior year
    idx = pd.to_datetime(hist.index)
    mask = idx.year == (target_year - 1)
    if not mask.any():
        return float(hist.iloc[0][_col(use_price_return)])
    last_pos = np.where(mask)[0][-1]
    return float(hist.iloc[last_pos][_col(use_price_return)])

def _live_price(ticker: str) -> Optional[float]:
    """Yahoo-style 'regular market' price for today (if available)."""
    try:
        fi = yf.Ticker(ticker).fast_info
        p = fi.get("last_price") or fi.get("regular_market_price")
        return float(p) if p is not None else None
    except Exception:
        return None

def currency_symbol(cur: str) -> str:
    return {"USD": "$", "EUR": "€", "GBp": "£"}.get(cur, "")

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Stock Dashboard", layout="wide")
st.title("📊 Stock Dashboard")
st.caption("Last price, 5-day % change, YTD % change (YTD baseline policy varies by exchange).")

# Toggle: Yahoo-style (Close) vs total return (Adj Close)
use_price_return = st.toggle(
    "Match Yahoo Finance numbers (use Close → price return, live price if today)",
    value=True,
    help="ON = Yahoo-style price return (Close) and uses live price for today's YTD. "
         "OFF = total return using Adj Close (dividends & splits), end-of-day only."
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
    target_date = target_dt.date()
    today_date = date.today()

    for s in selected_stocks:
        tkr = s["ticker"]
        try:
            tz_hint = _exchange_tz(tkr)
            is_euronext_like = (tz_hint in EURONEXT_TZS) and (s["Region"] in ("Ireland", "Europe"))

            # Start mid-Dec prior year so the baseline row exists; extend +7 days after target
            hist = yf.download(
                tkr,
                start=f"{selected_date.year-1}-12-15",
                end=selected_date + timedelta(days=7),
                progress=False,
                auto_adjust=False,
            )
            if hist.empty:
                continue

            # Last session on/before selected date
            price_eod, pos = last_close_on_or_before_date(hist, target_date, use_price_return)
            if pos is None:
                continue

            # If matching Yahoo and the selected date is today, prefer LIVE price
            use_live = use_price_return and (target_date == today_date)
            live_price = _live_price(tkr) if use_live else None
            price = float(live_price) if (live_price is not None) else float(price_eod)

            # 5D change uses the ref point N sessions before the pos
            c_5ago = close_n_trading_days_ago_by_pos(hist, pos, 5, use_price_return)
            chg_5d = None
            if c_5ago is not None and c_5ago != 0:
                chg_5d = (price - c_5ago) / c_5ago * 100.0

            # YTD baseline using policy (Euronext ≤ Dec 27, others ≤ Dec 31)
            base = ytd_baseline_from_hist_policy(hist, selected_date.year, use_price_return, is_euronext_like)
            if base is None:
                # Fallbacks (rare)
                base = prior_year_last_close(tkr, selected_date.year, use_price_return)
                if base is None:
                    # fall back to first session in current year
                    dates = _session_dates_index(hist)
                    mask = dates >= date(selected_date.year, 1, 1)
                    if mask.any():
                        first_pos = np.where(mask)[0][0]
                        base = float(hist.iloc[first_pos][_col(use_price_return)])

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
        # build & sort the result table
        df = (
            pd.DataFrame(rows)
              .sort_values(by=["Region", "Company"])
              .reset_index(drop=True)
        )

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
