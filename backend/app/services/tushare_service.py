import math
from datetime import datetime

import pandas as pd
import requests
import tushare as ts
import tushare.pro.client as tushare_client

from .settings_service import get_tushare_http_url, get_tushare_token

SUPPORTED_ASSET_TYPES = frozenset({"stock", "etf", "index", "fund"})

_PROXY_FREE_SESSION = requests.Session()
_PROXY_FREE_SESSION.trust_env = False
_QUERY_PATCHED = False


def _token():
    token = get_tushare_token()
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is not configured.")
    return token


def pro_api():
    _patch_tushare_query()
    token = _token()
    http_url = get_tushare_http_url()
    pro = ts.pro_api(token)
    pro._DataApi__token = token
    pro._DataApi__http_url = http_url
    return pro


def _patch_tushare_query():
    global _QUERY_PATCHED
    if _QUERY_PATCHED:
        return

    def query_without_env_proxy(self, api_name, fields="", **kwargs):
        req_params = {
            "api_name": api_name,
            "token": self._DataApi__token,
            "params": kwargs,
            "fields": fields,
        }
        response = _PROXY_FREE_SESSION.post(
            f"{self._DataApi__http_url}/{api_name}",
            json=req_params,
            timeout=self._DataApi__timeout,
        )
        if response:
            result = tushare_client.json.loads(response.text)
            if result["code"] != 0:
                raise Exception(result["msg"])
            data = result["data"]
            return tushare_client.pd.DataFrame(data["items"], columns=data["fields"])
        return tushare_client.pd.DataFrame()

    tushare_client.DataApi.query = query_without_env_proxy
    _QUERY_PATCHED = True


def normalize_date(value):
    if not value:
        return None
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def infer_asset_type(ts_code):
    text = (ts_code or "").upper().strip()
    parts = text.split(".")
    code = parts[0]
    exchange = parts[1] if len(parts) > 1 else ""
    if not (len(code) == 6 and code.isdigit()):
        return None
    if exchange == "BJ":
        return "stock"
    if exchange == "SH":
        if code.startswith(("600", "601", "603", "605", "688", "689")):
            return "stock"
        if code.startswith(("510", "511", "512", "513", "515", "516", "517", "518", "520", "560", "561", "562", "563", "588", "589")):
            return "etf"
        if code.startswith(("000", "880", "881", "882", "883", "884", "885", "886", "887", "888")):
            return "index"
    if exchange == "SZ":
        if code.startswith(("000", "001", "002", "003", "300", "301")):
            return "stock"
        if code.startswith(("150", "159", "160", "161", "162", "163", "164", "165", "166", "167", "168", "169", "184")):
            return "etf"
        if code.startswith(("399", "980", "981", "982", "983", "984", "985", "986", "987", "988")):
            return "index"
    return "stock"


def fetch_basic_info(ts_code, asset_type):
    fetcher = _BASIC_INFO_FETCHERS.get(asset_type)
    if fetcher is None:
        raise ValueError(f"Unsupported asset type: {asset_type}")
    return fetcher(pro_api(), ts_code)


def fetch_bars(ts_code, asset_type, freq, start_date=None, end_date=None):
    if freq not in {"daily", "weekly"}:
        raise ValueError(f"Unsupported frequency: {freq}")
    fetcher = _BAR_FRAME_FETCHERS.get(asset_type)
    if fetcher is None:
        raise ValueError(f"Unsupported asset type: {asset_type}")

    start = (start_date or "20180101").replace("-", "")
    end = (end_date or datetime.now().strftime("%Y%m%d")).replace("-", "")
    frame = fetcher(pro_api(), ts_code, freq, start, end)
    return _frame_to_rows(frame)


def _fetch_stock_basic(pro, ts_code):
    frame = pro.stock_basic(
        ts_code=ts_code,
        fields="ts_code,name,area,industry,market,list_date",
    )
    row = _matching_row(frame, ts_code)
    if row is None:
        return _fallback_basic(ts_code)
    row["list_date"] = normalize_date(row.get("list_date"))
    return row


def _fetch_etf_basic(pro, ts_code):
    frame = pro.etf_basic(
        ts_code=ts_code,
        fields=(
            "ts_code,csname,extname,cname,index_code,index_name,list_date,"
            "exchange,mgr_name,etf_type"
        ),
    )
    row = _matching_row(frame, ts_code)
    if row is None:
        return _fallback_basic(ts_code, market="E")
    return {
        "ts_code": row.get("ts_code", ts_code),
        "name": row.get("extname") or row.get("csname") or row.get("cname") or ts_code,
        "market": row.get("exchange") or "E",
        "industry": row.get("etf_type") or row.get("index_name"),
        "area": None,
        "list_date": normalize_date(row.get("list_date")),
    }


def _fetch_index_basic(pro, ts_code):
    frame = pro.index_basic(
        ts_code=ts_code,
        fields="ts_code,name,market,publisher,category,base_date,base_point,list_date",
    )
    row = _matching_row(frame, ts_code)
    if row is None:
        return _fallback_basic(ts_code)
    return {
        "ts_code": row.get("ts_code", ts_code),
        "name": row.get("name") or ts_code,
        "market": row.get("market"),
        "industry": row.get("category"),
        "area": row.get("publisher"),
        "list_date": normalize_date(row.get("list_date") or row.get("base_date")),
    }


def _fetch_fund_basic(pro, ts_code):
    frame = pro.fund_basic(
        market="E",
        fields="ts_code,name,management,custodian,fund_type,found_date,due_date",
    )
    row = _matching_row(frame, ts_code)
    if row is None:
        return _fallback_basic(ts_code, market="E")
    return {
        "ts_code": row.get("ts_code", ts_code),
        "name": row.get("name") or ts_code,
        "market": "E",
        "industry": row.get("fund_type"),
        "area": None,
        "list_date": normalize_date(row.get("found_date")),
    }


def _fetch_stock_bars(pro, ts_code, freq, start, end):
    api = pro.daily if freq == "daily" else pro.weekly
    frame = api(ts_code=ts_code, start_date=start, end_date=end)
    if freq != "daily" or frame is None or frame.empty:
        return frame
    try:
        factors = pro.adj_factor(ts_code=ts_code, start_date=start, end_date=end)
    except Exception:
        return frame
    if factors is None or factors.empty or "adj_factor" not in factors.columns:
        return frame
    return frame.merge(factors[["trade_date", "adj_factor"]], on="trade_date", how="left")


def _fetch_etf_bars(pro, ts_code, freq, start, end):
    daily = pro.fund_daily(ts_code=ts_code, start_date=start, end_date=end)
    return daily if freq == "daily" else _aggregate_weekly_frame(daily)


def _fetch_index_bars(pro, ts_code, freq, start, end):
    api = pro.index_daily if freq == "daily" else pro.index_weekly
    return api(ts_code=ts_code, start_date=start, end_date=end)


def _fetch_fund_bars(pro, ts_code, freq, start, end):
    daily = pro.fund_daily(ts_code=ts_code, start_date=start, end_date=end)
    return daily if freq == "daily" else _aggregate_weekly_frame(daily)


def _aggregate_weekly_frame(frame):
    if frame is None or frame.empty:
        return frame

    working = frame.copy()
    for column in ("trade_date", "open", "high", "low", "close", "vol", "amount"):
        if column not in working.columns:
            working[column] = None
    working["trade_date"] = working["trade_date"].astype(str)
    working["_trade_date"] = pd.to_datetime(working["trade_date"], format="%Y%m%d", errors="coerce")
    working = working.dropna(subset=["_trade_date"]).sort_values("_trade_date")
    if working.empty:
        return working

    working["_week"] = working["_trade_date"].dt.to_period("W-FRI")
    return (
        working.groupby("_week", sort=True)
        .agg(
            trade_date=("trade_date", "last"),
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            vol=("vol", "sum"),
            amount=("amount", "sum"),
        )
        .reset_index(drop=True)
    )


def _frame_to_rows(frame):
    if frame is None or frame.empty:
        return []

    rows = []
    for _, row in frame.sort_values("trade_date").iterrows():
        rows.append(
            {
                "trade_date": normalize_date(row.get("trade_date")),
                "open": _number(row.get("open")),
                "high": _number(row.get("high")),
                "low": _number(row.get("low")),
                "close": _number(row.get("close")),
                "volume": _number(row.get("vol")),
                "amount": _number(row.get("amount")),
                "adj_factor": _number(row.get("adj_factor")),
            }
        )
    return rows


def _matching_row(frame, ts_code):
    if frame is None or frame.empty or "ts_code" not in frame.columns:
        return None
    match = frame[frame["ts_code"] == ts_code]
    return None if match.empty else match.iloc[0].to_dict()


def _fallback_basic(ts_code, market=None):
    return {
        "ts_code": ts_code,
        "name": ts_code,
        "market": market,
        "industry": None,
        "area": None,
        "list_date": None,
    }


def _number(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return float(value)


_BASIC_INFO_FETCHERS = {
    "stock": _fetch_stock_basic,
    "etf": _fetch_etf_basic,
    "index": _fetch_index_basic,
    "fund": _fetch_fund_basic,
}

_BAR_FRAME_FETCHERS = {
    "stock": _fetch_stock_bars,
    "etf": _fetch_etf_bars,
    "index": _fetch_index_bars,
    "fund": _fetch_fund_bars,
}
