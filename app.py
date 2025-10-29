# app.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, date
import sqlite3
import io
import csv
import os
import base64
import json
from typing import Optional

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

# --- Exchange calendars (optional) ---
try:
    import exchange_calendars as xcals
    _HAS_XCALS = True
except Exception:
    xcals = None
    _HAS_XCALS = False

DB_PATH = "stocks.db"

# =============================
# GitHub-backed storage (CSV in repo)
# =============================
GH_STOCKS_PATH = "data/stocks.csv"
GH_BASELINES_PATH = "data/reference_prices.csv"

# --- Auth headers (supports classic 'token' and fine-grained 'Bearer') ---
def _gh_headers_auth(scheme: str = "token"):
    tok = st.secrets.get("GITHUB_TOKEN")
    if not tok:
        return None
    auth = f"{'Bearer' if scheme.lower()=='bearer' else 'token'} {tok}"
    return {
        "Authorization": auth,
        "Accept": "application/vnd.github+json",
        "User-Agent": "streamlit-app",
        "Content-Type": "application/json",
    }

def _gh_headers():  # keep old name for callers
    return _gh_headers_auth("token")

def _gh_repo():
    repo = st.secrets.get("GITHUB_REPO")
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    return repo, branch

def gh_get_file(path: str):
    repo, branch = _gh_repo()
    if not repo:
        return None
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    for scheme in ("token", "bearer"):
        headers = _gh_headers_auth(scheme)
        if not headers:
            return None
        try:
            if _HTTP_LIB == "requests":
                r = requests.get(url, params={"ref": branch}, headers=headers, timeout=20)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 401:
                    continue  # try next scheme
                return None
            else:
                full = f"{url}?{urllib.parse.urlencode({'ref': branch})}"
                req = urllib.request.Request(full, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if scheme == "bearer":
                return None
            continue
    return None

def gh_put_file(path: str, content_bytes: bytes, message: str, sha: Optional[str]):
    repo, branch = _gh_repo()
    if not repo:
        return False, "GitHub not configured"
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    body = json.dumps(payload).encode("utf-8")

    for scheme in ("token", "bearer"):
        headers = _gh_headers_auth(scheme)
        try:
            if _HTTP_LIB == "requests":
                r = requests.put(url, headers=headers, json=payload, timeout=30)
                if r.status_code in (200, 201):
                    return True, "Committed"
                if r.status_code == 401:
                    continue  # try alternate scheme
                return False, f"{r.status_code}: {r.text[:200]}"
            else:
                req = urllib.request.Request(url, data=body, headers=headers, method="PUT")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    code = resp.getcode()
                    if code in (200, 201):
                        return True, "Committed"
                    return False, f"{code}: {resp.read(200)}"
        except Exception as e:
            if scheme == "bearer":
                return False, f"Commit failed: {e}"
            continue
    return False, "401: Bad credentials (check token scope/SSO/repo access)"

def seed_db_from_github():
    """Fetch CSVs from repo and upsert into local SQLite tables."""
    # stocks.csv
    meta = gh_get_file(GH_STOCKS_PATH)
    if meta and "content" in meta:
        try:
            csv_bytes = base64.b64decode(meta["content"])
            df = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8-sig", keep_default_na=False)
            for _, r in df.iterrows():
                t = str(r.get("ticker","")).strip()
                n = str(r.get("name","")).strip()
                rg = str(r.get("region","")).strip()
                cu = str(r.get("currency","")).strip()
                if t and n and rg and cu:
                    db_add_stock(t, n, rg, cu)
        except Exception:
            pass

    # reference_prices.csv
    meta = gh_get_file(GH_BASELINES_PATH)
    if meta and "content" in meta:
        try:
            csv_bytes = base64.b64decode(meta["content"])
            df = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8-sig", keep_default_na=False)
            cols = {c.strip().lower(): c for c in df.columns}
            req = {"ticker","year","price"}
            if req.issubset(set(cols.keys())):
                for _, r in df.iterrows():
                    try:
                        db_set_reference(
                            str(r[cols["ticker"]]).strip(),
                            int(pd.to_numeric(r[cols["year"]], errors="coerce")),
                            float(pd.to_numeric(r[cols["price"]], errors="coerce")),
                            None if "date" not in cols else (None if pd.isna(r[cols["date"]]) else str(r[cols["date"]])),
                            None if "series" not in cols else (None if pd.isna(r[cols["series"]]) else str(r[cols["series"]])),
                            None if "notes" not in cols else (None if pd.isna(r[cols["notes"]]) else str(r[cols["notes"]]))
                        )
                    except Exception:
                        continue
        except Exception:
            pass

def sync_db_to_github(note: str = ""):
    """Dump both tables to CSV and commit to repo."""
    if not _gh_repo()[0] or not _gh_headers():
        return False, "GitHub not configured"

    # Stocks
    try:
        stocks_now = db_all_stocks().sort_values("name")
        s_buf = io.StringIO()
        stocks_now.to_csv(s_buf, index=False)
        s_bytes = s_buf.getvalue().encode("utf-8")
        meta_s = gh_get_file(GH_STOCKS_PATH)
        sha_s = meta_s.get("sha") if meta_s else None
        ok1, msg1 = gh_put_file(GH_STOCKS_PATH, s_bytes, f"stocks: {note or 'sync'}", sha_s)
    except Exception as e:
        ok1, msg1 = False, f"stocks export failed: {e}"

    # Baselines
    try:
        refs_all = db_all_references(None)
        r_buf = io.StringIO()
        refs_all.to_csv(r_buf, index=False)
        r_bytes = r_buf.getvalue().encode("utf-8")
        meta_r = gh_get_file(GH_BASELINES_PATH)
        sha_r = meta_r.get("sha") if meta_r else None
        ok2, msg2 = gh_put_file(GH_BASELINES_PATH, r_bytes, f"baselines: {note or 'sync'}", sha_r)
    except Exception as e:
        ok2, msg2 = False, f"baselines export failed: {e}"

    return (ok1 and ok2), f"stocks={msg1}; baselines={msg2}"

# =============================
# SQLite helpers (local runtime DB)
# =============================
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
            currency TEXT NOT NULL  -- EUR | GBp | USD | DKK | CHF
        )
    """)
    # Manual YTD baselines (one per ticker+year)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reference_prices (
            ticker TEXT NOT NULL,
            year   INTEGER NOT NULL,
            price  REAL NOT NULL,
            date   TEXT,
            series TEXT,
            notes  TEXT,
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
        ("IBE.MC","Iberdrola S.A.","Europe","EUR"),    # Madrid (primary)
        ("ORSTED.CO","Orsted A/S","Europe","DKK"),     # Copenhagen (primary)
        ("ROG.SW","Roche Holding AG","Europe","CHF"),  # SIX Swiss (primary)
        ("SAN.PA","Sanofi","Europe","EUR"),            # Paris (primary)
        # --- UK ---
        ("VOD.L","Vodafone Group","UK","GBp"),
        ("DCC.L","DCC plc","UK","GBp"),
        ("GNC.L","Greencore Group plc","UK","GBp"),
        ("GFTU.L","Grafton Group plc","UK","GBp"),
        ("HVO.L","hVIVO plc","UK","GBp"),
        ("POLB.L","Poolbeg Pharma PLC","UK","GBp"),
        ("TSCO.L","Tesco plc","UK","GBp"),
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

# ---- reference_prices helpers ----
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
    if not row:
        return None
    return {"price": float(row[0]), "date": row[1], "series": row[2], "notes": row[3]}

def db_all_references(year: Optional[int] = None) -> pd.DataFrame:
    conn = get_conn()
    if year is None:
        df = pd.read_sql_query("SELECT ticker,year,price,date,series,notes FROM reference_prices", conn)
    else:
        df = pd.read_sql_query("SELECT ticker,year,price,date,series,notes FROM reference_prices WHERE year = ?", conn, params=(int(year),))
    conn.close()
    return df

def db_delete_references(keys):
    if not keys:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany("DELETE FROM reference_prices WHERE ticker=? AND year=?", keys)
    conn.commit()
    conn.close()

# -----------------------------
# Helpers for prices/returns
# -----------------------------
def currency_symbol(cur: str) -> str:
    return {
        "USD": "$",
        "EUR": "€",
        "GBp": "£",
        "DKK": "kr",
        "CHF": "Fr",
    }.get(cur, "")

def _col(use_price_return: bool) -> str:
    # Yahoo UI uses price return => 'Close'; total return => 'Adj Close'
    return "Close" if use_price_return else "Adj Close"

def _session_dates_index(df: pd.DataFrame) -> np.ndarray:
    idx = pd.to_datetime(df.index)
    return np.array([d.date() for d in idx], dtype=object)

def last_close_on_or_before_date(df: pd.DataFrame, target_date: date, use_price_return: bool):
    if df.empty:
        return None, None
    dates = _session_dates_index(df)
    mask = dates <= target_date
    if not mask.any():
        return None, None
    pos = np.where(mask)[0][-1]
    return float(df.iloc[pos][_col(use_price_return)]), pos

def close_n_trading_days_ago_by_pos(df: pd.DataFrame, pos: int, n: int, use_price_return: bool):
    if df.empty or pos is None:
        return None
    ref_pos = pos - n
    if ref_pos < 0:
        return None
    return float(df.iloc[ref_pos][_col(use_price_return)])

# -----------------------------
# Yahoo chart endpoint for exact YTD
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
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def yahoo_ytd_via_chart(symbol: str, year: int, on_date: date, use_live_when_today: bool = True) -> Optional[float]:
    """
    Compute YTD % using Yahoo's own chart data (daily 'close' series).
    Baseline: last close BEFORE Jan 1 of `year` (local to exchange).
    Numerator: last close ON/BEFORE `on_date` (or live price if today & requested).
    """
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
        closes = (result.get("indicators", {}).get("quote", [{}])[0].get("close", []) or [])
        if not stamps or not closes:
            return None

        dcs = []
        for t, c in zip(stamps, closes):
            if c is None:
                continue
            dt = datetime.fromtimestamp(t, tz) if tz else datetime.utcfromtimestamp(t)
            dcs.append((dt.date(), float(c)))
        if not dcs:
            return None

        jan1 = date(year, 1, 1)
        prior = [c for d, c in dcs if d < jan1]
        if not prior:
            in_year = [c for d, c in dcs if d >= jan1]
            if not in_year:
                return None
            base = in_year[0]
        else:
            base = prior[-1]

        last_vals = [c for d, c in dcs if d <= on_date]
        if not last_vals:
            return None
        last_close = last_vals[-1]

        if use_live_when_today and on_date == date.today():
            try:
                fi = yf.Ticker(symbol).fast_info
                live = fi.get("last_price") or fi.get("regular_market_price")
                if live is not None:
                    last_close = float(live)
            except Exception:
                pass

        if base == 0:
            return None
        return (last_close - base) / base * 100.0
    except Exception:
        return None

# -----------------------------
# OFFICIAL EXCHANGE CALENDAR helpers (Option B)
# -----------------------------
CAL_BY_SUFFIX = {
    "IR": "XDUB",  # Dublin
    "PA": "XPAR",  # Paris
    "AS": "XAMS",  # Amsterdam
    "BR": "XBRU",  # Brussels
    "LS": "XLIS",  # Lisbon
    "L":  "XLON",  # London
    "MC": "XMAD",  # Madrid
    "CO": "XCSE",  # Copenhagen
    "SW": "XSWX",  # SIX Swiss
    "DE": "XETR",  # Xetra
    "F":  "XFRA",  # Frankfurt floor
    "MI": "XMIL",  # Milan
}
def _suffix(sym: str) -> str:
    return sym.split(".")[-1].upper() if "." in sym else ""
def ticker_calendar_c
