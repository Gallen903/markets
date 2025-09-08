import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, date
import sqlite3
import io
import csv
from typing import Optional, Dict, List

# --- HTTP (requests preferred; fallback to stdlib urllib) ---
try:
    import requests
    _HTTP_LIB = "requests"
except Exception:
    import urllib.request, urllib.parse
    _HTTP_LIB = "urllib"

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

DB_PATH = "stocks.db"

# -----------------------------
# SQLite helpers
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db_with_defaults():
    conn = get_conn()
    cur = conn.cursor()
    # Stocks table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            name   TEXT NOT NULL,
            region TEXT NOT NULL,   -- Ireland | UK | Europe | US
            currency TEXT NOT NULL  -- EUR | GBp | USD
        )
    """)
    # Manual YTD baselines
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reference_prices (
            ticker TEXT NOT NULL,
            year   INTEGER NOT NULL,
            price  REAL NOT NULL,
            date   TEXT,            -- optional yyyy-mm-dd
            series TEXT,            -- 'close'|'adjclose' (optional)
            notes  TEXT,            -- optional
            PRIMARY KEY (ticker, year)
        )
    """)

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

        # --- Europe ---
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
        ("PTSB.IR","PTSB Group Holdings plc","Ireland","EUR"),
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

# reference_prices helpers
def db_set_reference(ticker: str, year: int, price: float, date_iso: Optional[str], series: Optional[str], notes: Optional[str]):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reference_prices (ticker,year,price,date,series,notes)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(ticker,year) DO UPDATE SET price=excluded.price,date=excluded.date,series=excluded.series,notes=excluded.notes
    """, (ticker.strip(), int(year), float(price), (date_iso or None), (series or None), (notes or None)))
    conn.commit()
    conn.close()

def db_get_reference(ticker: str, year: int) -> Optional[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT price,date,series,notes FROM reference_prices WHERE ticker=? AND year=?", (ticker.strip(), int(year)))
    row = cur.fetchone()
    conn.close()
    if not row: return None
    return {"price": float(row[0]), "date": row[1], "series": row[2], "notes": row[3]}

def db_all_references(year: Optional[int] = None) -> pd.DataFrame:
    conn = get_conn()
    if year is None:
        df = pd.read_sql_query("SELECT ticker,year,price,date,series,notes FROM reference_prices", conn)
    else:
        df = pd.read_sql_query("SELECT ticker,year,price,date,series,notes FROM reference_prices WHERE year = ?", conn, params=(int(year),))
    conn.close()
    return df

def db_delete_references(keys: List[tuple]):
    if not keys: return
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany("DELETE FROM reference_prices WHERE ticker=? AND year=?", keys)
    conn.commit()
    conn.close()

# -----------------------------
# Helpers for prices/returns
# -----------------------------
def currency_symbol(cur: str) -> str:
    return {"USD": "$", "EUR": "€", "GBp": "£"}.get(cur, "")

def _col(use_price_return: bool) -> str:
    return "Close" if use_price_return else "Adj Close"

EU_SUFFIXES = (".IR", ".PA", ".MC", ".AS", ".BR", ".MI", ".NL", ".BE")
def _is_eu_like(ticker: str, region: str) -> bool:
    t = ticker.upper()
    return (region in ("Ireland", "Europe")) or any(t.endswith(suf) for suf in EU_SUFFIXES)

# -----------------------------
# Yahoo chart JSON helpers
# -----------------------------
def _http_get_json(url: str, params: dict, timeout: float = 10.0) -> Optional[dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        if _HTTP_LIB == "requests":
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        else:
            full = f"{url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(full, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                import json
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def chart_series_df(symbol: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> pd.DataFrame:
    """Daily Close/Adj Close, indexed by **session date** (date, not datetime). Tight window."""
    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)
    p1 = int((start_dt - timedelta(days=2)).timestamp())
    p2 = int((end_dt + timedelta(days=2)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"period1": p1, "period2": p2, "interval": "1d", "includePrePost": "false", "events": "div,splits"}
    data = _http_get_json(url, params)
    if not data:
        return pd.DataFrame()
    try:
        result = data["chart"]["result"][0]
        tzname = result.get("meta", {}).get("exchangeTimezoneName", "UTC")
        tz = ZoneInfo(tzname) if ZoneInfo else None
        stamps = result.get("timestamp", []) or []
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close", []) or []
        adjc = (result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", []) or [])
        rows = []
        for i, t in enumerate(stamps):
            c = closes[i] if i < len(closes) else None
            a = adjc[i] if i < len(adjc) else None
            if c is None and a is None:
                continue
            dt = datetime.fromtimestamp(t, tz) if tz else datetime.utcfromtimestamp(t)
            rows.append({"Session": dt.date(), "Close": c, "Adj Close": a})
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows).drop_duplicates(subset=["Session"], keep="last").set_index("Session")
        df.index = pd.to_datetime(df.index).date  # ensure index is date objects
        # Trim strictly to our window
        mask = (pd.Series(df.index) >= start_dt.date()) & (pd.Series(df.index) <= end_dt.date())
        return df.loc[mask.values]
    except Exception:
        return pd.DataFrame()

def get_series(symbol: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> pd.DataFrame:
    """
    Prefer yfinance (Close + Adj Close), trimmed, indexed by **session date**.
    If empty or missing fields, fall back to chart_series_df. Never returns future rows beyond end_dt.
    """
    # yfinance
    try:
        yf_df = yf.download(symbol, start=start_dt, end=end_dt + timedelta(days=1), progress=False, auto_adjust=False, threads=False)
    except Exception:
        yf_df = pd.DataFrame()

    def to_session_df(raw: pd.DataFrame) -> pd.DataFrame:
        if raw is None or raw.empty:
            return pd.DataFrame()
        # Normalize columns
        if isinstance(raw.columns, pd.MultiIndex):
            # Single ticker expected => flatten if possible
            try:
                raw = raw.swaplevel(axis=1).sort_index(axis=1)
                # take fields if present
                cols = {}
                for f in ["Close", "Adj Close"]:
                    for t in raw.columns.levels[0]:
                        if (t, f) in raw.columns:
                            cols[f] = raw[(t, f)]
                            break
                if not cols:
                    return pd.DataFrame()
                df = pd.concat(cols, axis=1)
            except Exception:
                return pd.DataFrame()
        else:
            keep = [c for c in ["Close", "Adj Close"] if c in raw.columns]
            if not keep:
                return pd.DataFrame()
            df = raw[keep]
        # Index to session date and trim
        idx_dates = pd.to_datetime(df.index).date
        df = df.copy()
        df.insert(0, "Session", idx_dates)
        df = df.drop_duplicates(subset=["Session"], keep="last").set_index("Session")
        # strict trim
        mask = (pd.Series(df.index) >= start_dt.date()) & (pd.Series(df.index) <= end_dt.date())
        return df.loc[mask.values]

    df_yf = to_session_df(yf_df)
    if df_yf is not None and not df_yf.empty:
        # Ensure both columns exist
        if "Adj Close" not in df_yf.columns:
            df_yf["Adj Close"] = np.nan
        if "Close" not in df_yf.columns:
            df_yf["Close"] = np.nan
        return df_yf

    # Fall back to chart
    return chart_series_df(symbol, start_dt, end_dt)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Stock Dashboard", layout="wide")
st.title("📊 Stock Dashboard")
st.caption("Last price, 5-day % change, and YTD % change. Manual baselines let you lock exact YTD for Irish/EU tickers.")

use_price_return = st.toggle(
    "Match Yahoo style for returns (use Close; live price if today)",
    value=True,
    help="ON = price return (Close). OFF = total return (Adj Close). Live price used ONLY if the selected date is today."
)
use_manual_baselines = st.toggle(
    "Use manual YTD baselines when available",
    value=True,
    help="If a manual baseline exists for (ticker, year), it overrides auto baselines for YTD %."
)

init_db_with_defaults()
stocks_df = pd.read_sql_query("SELECT ticker,name,region,currency FROM stocks", get_conn())

colA, colB = st.columns([1,1])
with colA:
    selected_date = st.date_input("Select date", value=date.today())
with colB:
    st.write(" ")
    run = st.button("Run")

# ---- Add/remove stocks
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
                db_add_conn = get_conn()
                db_add_conn.execute("INSERT OR REPLACE INTO stocks (ticker,name,region,currency) VALUES (?,?,?,?)",
                                    (a_ticker.strip(), a_name.strip(), a_region, a_curr))
                db_add_conn.commit(); db_add_conn.close()
                st.success(f"Saved {a_name} ({a_ticker})")
            else:
                st.warning("Please provide at least Ticker and Company name.")
    with c2:
        st.markdown("**Remove stocks**")
        rem_choices = [f"{r['name']} ({r['ticker']})" for _, r in stocks_df.sort_values("name").iterrows()]
        rem_sel = st.multiselect("Select to remove", rem_choices, [])
        if st.button("Remove selected"):
            tickers = [s[s.rfind("(")+1:-1] for s in rem_sel]
            conn_rm = get_conn()
            conn_rm.executemany("DELETE FROM stocks WHERE ticker = ?", [(t,) for t in tickers])
            conn_rm.commit(); conn_rm.close()
            st.success(f"Removed {len(tickers)} stock(s)")

# ---- Manual YTD baselines
with st.expander("🧭 Manual YTD baselines (set once at start of year)"):
    cur_year = st.number_input("Year", min_value=2000, max_value=2100, value=selected_date.year, step=1)
    st.caption("Define the **baseline price** used for YTD % for that ticker in this year (EUR/GBp/USD).")

    c1, c2, c3, c4 = st.columns([1.2, 0.8, 0.8, 1])
    with c1: b_ticker = st.text_input("Ticker (exact)", placeholder="A5G.IR")
    with c2: b_price  = st.text_input("Baseline price", placeholder="e.g. 4.25")
    with c3: b_series = st.selectbox("Series", ["close","adjclose"])
    with c4: b_date   = st.text_input("Baseline date (optional, yyyy-mm-dd)", placeholder="2024-12-27")
    b_notes = st.text_input("Notes (optional)", placeholder="e.g. Dec 27 adjclose from Yahoo")

    if st.button("Add / Update baseline"):
        try:
            db_set_reference(b_ticker, int(cur_year), float(b_price), b_date.strip() or None, b_series, b_notes.strip() or None)
            st.success(f"Baseline saved for {b_ticker} ({cur_year}): {b_price}")
        except Exception as e:
            st.error(f"Could not save baseline: {e}")

    st.markdown("**Bulk import / export** (CSV: ticker,year,price,date,series,notes)")
    up = st.file_uploader("Upload CSV", type=["csv"])
    if up is not None:
        try:
            imp = pd.read_csv(up)
            for _, r in imp.iterrows():
                db_set_reference(
                    str(r.get("ticker")), int(r.get("year")), float(r.get("price")),
                    None if pd.isna(r.get("date")) else str(r.get("date")),
                    None if pd.isna(r.get("series")) else str(r.get("series")),
                    None if pd.isna(r.get("notes")) else str(r.get("notes")),
                )
            st.success(f"Imported/updated {len(imp)} baseline(s).")
        except Exception as e:
            st.error(f"Import failed: {e}")

    refs_df = db_all_references(cur_year).sort_values(["ticker","year"])
    st.dataframe(refs_df, use_container_width=True)
    if not refs_df.empty:
        out_csv = io.StringIO(); refs_df.to_csv(out_csv, index=False)
        st.download_button("⬇️ Download current year's baselines CSV", data=out_csv.getvalue(),
                           file_name=f"ytd_baselines_{cur_year}.csv", mime="text/csv")

        del_opts = [f"{r['ticker']} ({r['year']})" for _, r in refs_df.iterrows()]
        del_sel = st.multiselect("Delete baselines", del_opts, [])
        if st.button("Delete selected baselines"):
            keys = []
            for s in del_sel:
                t = s[:s.rfind("(")].strip()
                y = int(s[s.rfind("(")+1:-1])
                keys.append((t,y))
            db_delete_references(keys)
            st.success(f"Deleted {len(keys)} baseline(s).")

# ----- Selection
stocks_df = pd.read_sql_query("SELECT ticker,name,region,currency FROM stocks", get_conn())
stock_options = {f"{r['name']} ({r['ticker']})": dict(r) for _, r in stocks_df.iterrows()}
sel_labels = st.multiselect("Stocks to include in this run:", list(stock_options.keys()), default=list(stock_options.keys()))
selected_stocks = [stock_options[label] for label in sel_labels]

# -----------------------------
# Run calculation
# -----------------------------
if run:
    rows = []
    target_date = pd.to_datetime(selected_date).date()
    today_date = date.today()
    grace_days = 2  # enough for Fri→Sat/Sun UTC stamp

    window_start = date(selected_date.year - 1, 12, 15)
    window_end   = target_date + timedelta(days=grace_days)

    for s in selected_stocks:
        tkr = s["ticker"]
        try:
            # Build a clean daily series (session-date index) for Close + Adj Close
            series_df = get_series(tkr, pd.to_datetime(window_start), pd.to_datetime(window_end))
            if series_df is None or series_df.empty:
                continue

            # Pick the session on/before selected date (with grace)
            sessions = pd.Index(series_df.index)
            mask = sessions <= pd.to_datetime(window_end).date()
            if not mask.any():
                continue
            pos = np.where(mask)[0][-1]

            # Determine displayed price (EOD for selected session; live ONLY if selected_date == today)
            price_eod_close = float(series_df.iloc[pos]["Close"]) if pd.notnull(series_df.iloc[pos]["Close"]) else None
            price_eod_adj   = float(series_df.iloc[pos]["Adj Close"]) if pd.notnull(series_df.iloc[pos]["Adj Close"]) else None

            price_eod = price_eod_close if use_price_return else (price_eod_adj if price_eod_adj is not None else price_eod_close)

            if price_eod is None:
                continue

            price_num = price_eod
            if use_price_return and (target_date == today_date):
                try:
                    fi = yf.Ticker(tkr).fast_info
                    live = fi.get("last_price") or fi.get("regular_market_price")
                    if live is not None:
                        price_num = float(live)
                except Exception:
                    pass

            # 5D change
            ref_pos = pos - 5
            chg_5d = None
            if ref_pos >= 0:
                ref_val_close = series_df.iloc[ref_pos]["Close"]
                ref_val_adj   = series_df.iloc[ref_pos]["Adj Close"]
                ref_val = ref_val_close if use_price_return else (ref_val_adj if pd.notnull(ref_val_adj) else ref_val_close)
                if pd.notnull(ref_val) and ref_val != 0:
                    chg_5d = (price_num - float(ref_val)) / float(ref_val) * 100.0

            # YTD change
            chg_ytd = None
            manual_ref = db_get_reference(tkr, selected_date.year) if use_manual_baselines else None
            if manual_ref is not None:
                base = manual_ref["price"]
                if base:
                    chg_ytd = (price_num - float(base)) / float(base) * 100.0
            else:
                # Auto baseline from the same series_df
                eu_like = _is_eu_like(tkr, s["Region"])
                if eu_like:
                    # Yahoo-like EU: use Adj Close and an anchor <= Dec 27
                    cutoff = date(selected_date.year - 1, 12, 27)
                    prev_idx = [i for i, d in enumerate(series_df.index) if d <= cutoff]
                    if prev_idx:
                        base_val = series_df.iloc[prev_idx[-1]]["Adj Close"]
                    else:
                        base_val = np.nan
                else:
                    # Standard: last session strictly before Jan 1, using Close
                    jan1 = date(selected_date.year, 1, 1)
                    prev_idx = [i for i, d in enumerate(series_df.index) if d < jan1]
                    if prev_idx:
                        base_val = series_df.iloc[prev_idx[-1]]["Close"]
                    else:
                        # if no prior, take first in-year
                        in_idx = [i for i, d in enumerate(series_df.index) if d >= jan1]
                        base_val = series_df.iloc[in_idx[0]]["Close"] if in_idx else np.nan

                if pd.notnull(base_val) and float(base_val) != 0.0:
                    chg_ytd = (price_num - float(base_val)) / float(base_val) * 100.0

            rows.append({
                "Company": s["name"],
                "Region": s["region"],
                "Currency": s["currency"],
                "Price": round(price_num, 1),
                "5D % Change": round(chg_5d, 1) if chg_5d is not None else None,
                "YTD % Change": round(chg_ytd, 1) if chg_ytd is not None else None,
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
