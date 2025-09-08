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

# --- Timezone helper (ZoneInfo on Python 3.9+) ---
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # fallback to UTC if not available

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
    # Manual reference baselines (one per ticker+year)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reference_prices (
            ticker TEXT NOT NULL,
            year   INTEGER NOT NULL,
            price  REAL NOT NULL,
            date   TEXT,            -- ISO yyyy-mm-dd (optional reference session date)
            series TEXT,            -- 'close' or 'adjclose' (optional metadata)
            notes  TEXT,            -- free text (optional)
            PRIMARY KEY (ticker, year)
        )
    """)
    # Seed defaults WITHOUT overwriting user entries
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

# ----- reference_prices helpers -----
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
# Stocks CRUD
# -----------------------------
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
# Helpers for prices/returns
# -----------------------------
def currency_symbol(cur: str) -> str:
    return {"USD": "$", "EUR": "€", "GBp": "£"}.get(cur, "")

def _col(use_price_return: bool) -> str:
    return "Close" if use_price_return else "Adj Close"

def _session_dates_index(df: pd.DataFrame) -> np.ndarray:
    idx = pd.to_datetime(df.index)
    return np.array([d.date() for d in idx], dtype=object)

# Robust session lookup (+3 day grace; hard fallback)
def last_close_on_or_before_date(df: pd.DataFrame, target_date: date, use_price_return: bool, grace_days: int = 3):
    if df.empty:
        return None, None
    dates = _session_dates_index(df)
    cutoff = target_date + timedelta(days=grace_days)
    mask = dates <= cutoff
    if mask.any():
        pos = np.where(mask)[0][-1]
        return float(df.iloc[pos][_col(use_price_return)]), pos
    pos = len(df) - 1
    return float(df.iloc[pos][_col(use_price_return)]), pos

def close_n_trading_days_ago_by_pos(df: pd.DataFrame, pos: int, n: int, use_price_return: bool):
    if df.empty or pos is None:
        return None
    ref_pos = pos - n
    if ref_pos < 0:
        return None
    return float(df.iloc[ref_pos][_col(use_price_return)])

# -----------------------------
# Yahoo chart fetch (for YTD and as a final OHLC fallback)
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
    try:
        p1 = int((pd.to_datetime(start_dt) - timedelta(days=10)).timestamp())
        p2 = int((pd.to_datetime(end_dt) + timedelta(days=10)).timestamp())
    except Exception:
        return pd.DataFrame()

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
        n = min(len(stamps), len(closes))
        dates = [ (datetime.fromtimestamp(stamps[i], tz) if tz else datetime.utcfromtimestamp(stamps[i])) for i in range(n) ]
        close_vals = [ float(closes[i]) if closes[i] is not None else np.nan for i in range(n) ]
        adj_vals = [ float(adjc[i]) if i < len(adjc) and adjc[i] is not None else np.nan for i in range(n) ]
        df = pd.DataFrame({"Open": np.nan, "High": np.nan, "Low": np.nan,
                           "Close": close_vals, "Adj Close": adj_vals, "Volume": np.nan},
                          index=pd.to_datetime(dates))
        df = df.loc[(df.index >= pd.to_datetime(start_dt)) & (df.index <= pd.to_datetime(end_dt))]
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame()

def yahoo_ytd_via_chart(symbol: str, year: int, on_date: date, use_live_when_today: bool = True,
                        series: str = "close", anchor_policy: str = "standard") -> Optional[float]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "2y", "interval": "1d", "includePrePost": "false", "events": "div,splits"}
    data = _http_get_json(url, params)
    if not data:
        return None
    try:
        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        tzname = meta.get("exchangeTimezoneName", "UTC")
        tz = ZoneInfo(tzname) if ZoneInfo else None
        stamps = result.get("timestamp", []) or []
        q = result.get("indicators", {}).get("quote", [{}])[0]
        closes = q.get("close", []) or []
        adjc = (result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", []) or [])
        vec = adjc if (series == "adjclose" and len(adjc) == len(stamps)) else closes
        if not stamps or not vec: return None
        dcs = []
        for t, v in zip(stamps, vec):
            if v is None: continue
            dt = datetime.fromtimestamp(t, tz) if tz else datetime.utcfromtimestamp(t)
            dcs.append((dt.date(), float(v)))
        if not dcs: return None
        if anchor_policy == "preholiday":
            cutoff = date(year - 1, 12, 27)
            prev = [val for d, val in dcs if d <= cutoff]
            if not prev: return None
            base = prev[-1]
        else:
            jan1 = date(year, 1, 1)
            prev = [val for d, val in dcs if d < jan1]
            if not prev:
                in_year = [val for d, val in dcs if d >= jan1]
                if not in_year: return None
                base = in_year[0]
            else:
                base = prev[-1]
        last_vals = [val for d, val in dcs if d <= on_date]
        if not last_vals: return None
        last_val = last_vals[-1]
        if (series == "close") and use_live_when_today and (on_date == date.today()):
            try:
                fi = yf.Ticker(symbol).fast_info
                live = fi.get("last_price") or fi.get("regular_market_price")
                if live is not None: last_val = float(live)
            except Exception:
                pass
        if base == 0: return None
        return (last_val - base) / base * 100.0
    except Exception:
        return None

# -----------------------------
# Batch + resilient fetch
# -----------------------------
def _split_multi(data: pd.DataFrame, tickers: List[str]) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    if data is None or data.empty:
        return out
    cols = data.columns
    fields = ["Open","High","Low","Close","Adj Close","Volume"]
    if isinstance(cols, pd.MultiIndex):
        lvl0_vals = list(map(str, cols.get_level_values(0)))
        lvl1_vals = list(map(str, cols.get_level_values(1)))
        if set(fields).issubset(set(lvl0_vals)):
            # (field, ticker)
            for t in tickers:
                parts = []
                for f in fields:
                    key = (f, t)
                    if key in data.columns:
                        parts.append(data[key].rename(f))
                if parts:
                    out[t] = pd.concat(parts, axis=1).dropna(how="all")
        else:
            # (ticker, field)
            for t in tickers:
                if t in cols.get_level_values(0):
                    sub = data[t]
                    keep = [f for f in fields if f in sub.columns]
                    if keep:
                        out[t] = sub[keep].dropna(how="all")
    else:
        if len(tickers) == 1:
            out[tickers[0]] = data.dropna(how="all")
    return out

def fetch_hist_batch(tickers: List[str], start, end) -> Dict[str, pd.DataFrame]:
    start_dt = pd.to_datetime(start)
    end_dt   = pd.to_datetime(end)
    per: Dict[str, pd.DataFrame] = {t: pd.DataFrame() for t in tickers}
    # 1) Batch download
    try:
        batch = yf.download(
            tickers,
            start=start_dt,
            end=end_dt,
            progress=False,
            auto_adjust=False,
            group_by="column",
            threads=True,
        )
        per.update(_split_multi(batch, tickers))
    except Exception:
        pass
    # 2) Per-ticker fallbacks; 3) Chart fallback
    for t in tickers:
        if t in per and not per[t].empty:
            continue
        try:
            h = yf.Ticker(t).history(start=start_dt, end=end_dt, interval="1d", actions=False, auto_adjust=False)
            if h is not None and not h.empty:
                per[t] = h
                continue
        except Exception:
            pass
        try:
            h = yf.Ticker(t).history(period="2y", interval="1d", actions=False, auto_adjust=False)
            if h is not None and not h.empty:
                idx = pd.to_datetime(h.index)
                mask = (idx >= start_dt) & (idx <= end_dt)
                per[t] = h.loc[mask] if mask.any() else h
                continue
        except Exception:
            pass
        chart_df = chart_series_df(t, start_dt, end_dt)
        if not chart_df.empty:
            per[t] = chart_df
    return per

# --- Venue helpers for Yahoo parity (EU pre-holiday + adjusted series) ---
EU_SUFFIXES = (".IR", ".PA", ".MC", ".AS", ".BR", ".MI", ".NL", ".BE")
def _is_eu_like(ticker: str, region: str) -> bool:
    t = ticker.upper()
    return (region in ("Ireland", "Europe")) or any(t.endswith(suf) for suf in EU_SUFFIXES)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Stock Dashboard", layout="wide")
st.title("📊 Stock Dashboard")
st.caption("Last price, 5-day % change, and YTD % change. Use manual baselines for exact parity on Irish/EU tickers if needed.")

# Toggles
use_price_return = st.toggle(
    "Match Yahoo style for returns (use Close; live price if today)",
    value=True,
    help="ON = price return (Close). OFF = total return (Adj Close). Live price used for today's numerator."
)
use_manual_baselines = st.toggle(
    "Use manual YTD baselines when available",
    value=True,
    help="If a manual baseline exists for (ticker, year), it overrides auto baselines for YTD %."
)
exact_yahoo_mode = st.toggle(
    "Exact Yahoo YTD (chart feed) for others",
    value=True,
    help="If no manual baseline, compute YTD from Yahoo's chart endpoint. Irish/EU tickers use adjclose + pre-holiday baseline."
)

init_db_with_defaults()
stocks_df = db_all_stocks()

colA, colB = st.columns([1,1])
with colA:
    selected_date = st.date_input("Select date", value=date.today())
with colB:
    st.write(" ")
    run = st.button("Run")

# ---- Editor: add/remove stocks
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

# ---- NEW: Manual YTD baseline manager
with st.expander("🧭 Manual YTD baselines (set once at start of year)"):
    cur_year = st.number_input("Year", min_value=2000, max_value=2100, value=selected_date.year, step=1)
    st.caption("Each row defines the **baseline price** used for YTD % for that ticker in this year. Price should be in the trading currency (EUR/GBp/USD).")

    # Quick add form
    c1, c2, c3, c4 = st.columns([1.2, 0.8, 0.8, 1])
    with c1:
        b_ticker = st.text_input("Ticker (exact)", placeholder="A5G.IR")
    with c2:
        b_price = st.text_input("Baseline price", placeholder="e.g. 4.25")
    with c3:
        b_series = st.selectbox("Series", ["close","adjclose"])
    with c4:
        b_date = st.text_input("Baseline date (optional, yyyy-mm-dd)", placeholder="2024-12-27")

    b_notes = st.text_input("Notes (optional)", placeholder="e.g. Dec 27 adjclose from Yahoo")
    if st.button("Add / Update baseline"):
        try:
            price_val = float(b_price)
            db_set_reference(b_ticker, int(cur_year), price_val, b_date.strip() or None, b_series, b_notes.strip() or None)
            st.success(f"Baseline saved for {b_ticker} ({cur_year}): {price_val}")
        except Exception as e:
            st.error(f"Could not save baseline: {e}")

    # CSV import/export
    st.markdown("**Bulk import / export**")
    st.caption("CSV columns: ticker, year, price, date (optional), series (close|adjclose, optional), notes (optional)")
    up = st.file_uploader("Upload CSV to import/update baselines", type=["csv"])
    if up is not None:
        try:
            df_imp = pd.read_csv(up)
            req_cols = {"ticker","year","price"}
            if not req_cols.issubset({c.strip().lower() for c in df_imp.columns}):
                st.error("CSV must include at least columns: ticker, year, price")
            else:
                # Normalize columns
                df_norm = pd.DataFrame({
                    "ticker": df_imp["ticker"],
                    "year": df_imp["year"].astype(int),
                    "price": df_imp["price"].astype(float),
                    "date": df_imp["date"] if "date" in df_imp.columns else None,
                    "series": df_imp["series"] if "series" in df_imp.columns else None,
                    "notes": df_imp["notes"] if "notes" in df_imp.columns else None,
                })
                for _, r in df_norm.iterrows():
                    db_set_reference(str(r["ticker"]), int(r["year"]), float(r["price"]),
                                     (None if pd.isna(r["date"]) else str(r["date"])),
                                     (None if pd.isna(r["series"]) else str(r["series"])),
                                     (None if pd.isna(r["notes"]) else str(r["notes"])))
                st.success(f"Imported/updated {len(df_norm)} baseline(s).")
        except Exception as e:
            st.error(f"Import failed: {e}")

    # Show & export current year
    refs_df = db_all_references(cur_year).sort_values(["ticker","year"])
    st.dataframe(refs_df, use_container_width=True)
    if not refs_df.empty:
        out_csv = io.StringIO()
        refs_df.to_csv(out_csv, index=False)
        st.download_button("⬇️ Download current year's baselines CSV", data=out_csv.getvalue(), file_name=f"ytd_baselines_{cur_year}.csv", mime="text/csv")

    # Delete selected
    if not refs_df.empty:
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

    tickers = [s["ticker"] for s in selected_stocks]
    # Pull enough history once for all tickers (batch), then fill stragglers (includes chart fallback)
    hist_map = fetch_hist_batch(
        tickers,
        start=f"{selected_date.year-1}-12-15",
        end=selected_date + timedelta(days=10),
    )

    for s in selected_stocks:
        tkr = s["ticker"]
        try:
            hist = hist_map.get(tkr, pd.DataFrame())
            if hist is None or hist.empty:
                continue

            # Last session on/before selected date (grace up to +3 days, with hard fallback)
            price_eod, pos = last_close_on_or_before_date(hist, target_date, use_price_return, grace_days=3)
            if pos is None:
                continue

            # Live price option
            use_live = use_price_return and (target_date == today_date)
            live_price = None
            if use_live:
                try:
                    fi = yf.Ticker(tkr).fast_info
                    live_price = fi.get("last_price") or fi.get("regular_market_price")
                except Exception:
                    live_price = None
            price_num = float(live_price) if (live_price is not None) else float(price_eod)

            # 5D change
            c_5ago = close_n_trading_days_ago_by_pos(hist, pos, 5, use_price_return)
            chg_5d = None
            if c_5ago is not None and c_5ago != 0:
                chg_5d = (price_num - c_5ago) / c_5ago * 100.0

            # YTD %
            chg_ytd = None
            manual_ref = db_get_reference(tkr, selected_date.year) if use_manual_baselines else None
            if manual_ref is not None:
                base = manual_ref["price"]
                if base:
                    chg_ytd = (price_num - float(base)) / float(base) * 100.0
            elif exact_yahoo_mode:
                eu_like = _is_eu_like(tkr, s["Region"])
                series  = "adjclose" if eu_like else "close"
                policy  = "preholiday" if eu_like else "standard"
                chg_ytd = yahoo_ytd_via_chart(
                    tkr, selected_date.year, target_date,
                    use_live_when_today=use_price_return,
                    series=series,
                    anchor_policy=policy
                )
            else:
                # Basic fallback: prior-year last session baseline (≤ Dec 31)
                dates = _session_dates_index(hist)
                mask_prev = dates <= date(selected_date.year - 1, 12, 31)
                base = float(hist.iloc[np.where(mask_prev)[0][-1]][_col(use_price_return)]) if mask_prev.any() else None
                chg_ytd = ((price_num - base) / base * 100.0) if base else None

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

        # CSV export (unchanged format)
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
