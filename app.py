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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            name   TEXT NOT NULL,
            region TEXT NOT NULL,   -- Ireland | UK | Europe | US
            currency TEXT NOT NULL  -- EUR | GBp | USD
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
    # Yahoo UI uses price return => 'Close'; total return => 'Adj Close'
    return "Close" if use_price_return else "Adj Close"

def _session_dates_index(df: pd.DataFrame) -> np.ndarray:
    """Return array of date() for each row; treat rows as local session dates."""
    idx = pd.to_datetime(df.index)
    return np.array([d.date() for d in idx], dtype=object)

# --- Robust session lookup with wider grace (+3 days) and hard fallback ---
def last_close_on_or_before_date(df: pd.DataFrame, target_date: date, use_price_return: bool, grace_days: int = 3):
    """
    Find the last session on/before target_date, allowing a forward grace window
    (to catch Friday bars stamped on Sat/Sun UTC). If still nothing, fall back to
    the last available row in df.
    """
    if df.empty:
        return None, None
    dates = _session_dates_index(df)
    cutoff = target_date + timedelta(days=grace_days)
    mask = dates <= cutoff
    if mask.any():
        pos = np.where(mask)[0][-1]
        return float(df.iloc[pos][_col(use_price_return)]), pos
    # HARD FALLBACK: use last available row
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
# Batch + resilient fetch
# -----------------------------
def _split_multi(data: pd.DataFrame, tickers: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Split yf.download's multi-ticker frame into per-ticker frames with standard OHLCV columns.
    Works with both wide (single ticker) and MultiIndex columns.
    """
    out: Dict[str, pd.DataFrame] = {}
    if data is None or data.empty:
        return out
    cols = data.columns
    if isinstance(cols, pd.MultiIndex):
        # Expected shape: top level = field, second level = ticker
        fields = ["Open","High","Low","Close","Adj Close","Volume"]
        for t in tickers:
            sub = pd.concat({f: data[(f, t)] for f in fields if (f, t) in data.columns}, axis=1)
            sub.columns = fields[:sub.shape[1]]
            out[t] = sub.dropna(how="all")
    else:
        # Single ticker; we don't know which one, so map to the only ticker if there is exactly one
        if len(tickers) == 1:
            out[tickers[0]] = data.dropna(how="all")
    return out

def fetch_hist_batch(tickers: List[str], start, end) -> Dict[str, pd.DataFrame]:
    """
    Try to download all tickers in one call; if some missing, fill them via per-ticker fallbacks.
    """
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
            group_by="ticker",
            threads=True,
        )
        per.update(_split_multi(batch, tickers))
    except Exception:
        pass

    # 2) Fill any empties with per-ticker fallbacks (history start/end, then period="2y")
    for t in tickers:
        if t in per and not per[t].empty:
            continue
        # try per-ticker start/end
        try:
            h = yf.Ticker(t).history(start=start_dt, end=end_dt, interval="1d", actions=False, auto_adjust=False)
            if h is not None and not h.empty:
                per[t] = h
                continue
        except Exception:
            pass
        # try broader period and trim
        try:
            h = yf.Ticker(t).history(period="2y", interval="1d", actions=False, auto_adjust=False)
            if h is not None and not h.empty:
                idx = pd.to_datetime(h.index)
                mask = (idx >= start_dt) & (idx <= end_dt)
                per[t] = h.loc[mask] if mask.any() else h
        except Exception:
            pass

    return per

# --- Venue helpers for Yahoo parity (EU pre-holiday + adjusted series) ---
EU_SUFFIXES = (".IR", ".PA", ".MC", ".AS", ".BR", ".MI", ".NL", ".BE")

def _is_eu_like(ticker: str, region: str) -> bool:
    t = ticker.upper()
    return (region in ("Ireland", "Europe")) or any(t.endswith(suf) for suf in EU_SUFFIXES)

# -----------------------------
# OPTION A: Yahoo chart endpoint for exact YTD
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

def yahoo_ytd_via_chart(
    symbol: str,
    year: int,
    on_date: date,
    use_live_when_today: bool = True,
    series: str = "close",                 # "close" or "adjclose"
    anchor_policy: str = "standard"        # "standard" => last < Jan 1; "preholiday" => last <= Dec 27
) -> Optional[float]:
    """
    Compute YTD % using Yahoo's own chart data (daily series).
    Baseline:
      - standard: last value strictly before Jan 1 of `year`
      - preholiday: last value on/ before Dec 27 of prior year
    Numerator: last value on/ before `on_date` (or live price if today & series=='close' & enabled)
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
        q = result.get("indicators", {}).get("quote", [{}])[0]
        closes = q.get("close", []) or []
        adjc = (result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", []) or [])

        vec = adjc if (series == "adjclose" and len(adjc) == len(stamps)) else closes
        if not stamps or not vec:
            return None

        dcs = []
        for t, v in zip(stamps, vec):
            if v is None:
                continue
            dt = datetime.fromtimestamp(t, tz) if tz else datetime.utcfromtimestamp(t)
            dcs.append((dt.date(), float(v)))
        if not dcs:
            return None

        # Baseline
        if anchor_policy == "preholiday":
            cutoff = date(year - 1, 12, 27)
            prev = [val for d, val in dcs if d <= cutoff]
            if not prev:
                return None
            base = prev[-1]
        else:
            jan1 = date(year, 1, 1)
            prev = [val for d, val in dcs if d < jan1]
            if not prev:
                in_year = [val for d, val in dcs if d >= jan1]
                if not in_year:
                    return None
                base = in_year[0]
            else:
                base = prev[-1]

        # Value for on_date (latest <= on_date)
        last_vals = [val for d, val in dcs if d <= on_date]
        if not last_vals:
            return None
        last_val = last_vals[-1]

        # Optional: live for today if using CLOSE (price return)
        if (series == "close") and use_live_when_today and (on_date == date.today()):
            try:
                fi = yf.Ticker(symbol).fast_info
                live = fi.get("last_price") or fi.get("regular_market_price")
                if live is not None:
                    last_val = float(live)
            except Exception:
                pass

        if base == 0:
            return None
        return (last_val - base) / base * 100.0
    except Exception:
        return None

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Stock Dashboard", layout="wide")
st.title("📊 Stock Dashboard")
st.caption("Last price, 5-day % change, and YTD % change. YTD can be computed from Yahoo's chart feed for exact parity.")

# Toggles
use_price_return = st.toggle(
    "Match Yahoo style for returns (use Close; live price if today)",
    value=True,
    help="ON = price return (Close). OFF = total return (Adj Close). Live price used for today's numerator."
)
exact_yahoo_mode = st.toggle(
    "Exact Yahoo YTD (chart feed)",
    value=True,
    help="ON = compute YTD from Yahoo's chart endpoint to match their baseline/calendar. "
         "For Irish/EU tickers uses adjclose + pre-holiday baseline."
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
        rem_choices = [f"{r['name']} ({r['ticker']})"] + []
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

    tickers = [s["ticker"] for s in selected_stocks]
    # Pull enough history once for all tickers (batch), then fill stragglers
    hist_map = fetch_hist_batch(
        tickers,
        start=f"{selected_date.year-1}-12-15",
        end=selected_date + timedelta(days=10),   # slightly wider to be safe
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

            # If matching Yahoo style and selected date is today, prefer LIVE price for display/5D numerators
            use_live = use_price_return and (target_date == today_date)
            live_price = None
            if use_live:
                try:
                    fi = yf.Ticker(tkr).fast_info
                    live_price = fi.get("last_price") or fi.get("regular_market_price")
                except Exception:
                    live_price = None

            # Numerator price (today's live if available; else EOD close)
            price_num = float(live_price) if (live_price is not None) else float(price_eod)

            # 5D change uses n sessions back from the EOD position
            c_5ago = close_n_trading_days_ago_by_pos(hist, pos, 5, use_price_return)
            chg_5d = None
            if c_5ago is not None and c_5ago != 0:
                chg_5d = (price_num - c_5ago) / c_5ago * 100.0

            # YTD %
            if exact_yahoo_mode:
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
                # Internal fallback: prior-year last session baseline (≤ Dec 31)
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
