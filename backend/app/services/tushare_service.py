from datetime import datetime
import math

import tushare as ts

from .settings_service import get_tushare_http_url, get_tushare_token


def _token():
    token = get_tushare_token()
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is not configured.")
    return token


def pro_api():
    token = _token()
    http_url = get_tushare_http_url()
    pro = ts.pro_api(token)
    pro._DataApi__token = token
    pro._DataApi__http_url = http_url
    return pro


def normalize_date(value):
    if not value:
        return None
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def fetch_basic_info(ts_code, asset_type):
    pro = pro_api()
    if asset_type == "stock":
        frame = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,name,area,industry,market,list_date",
        )
        match = frame[frame["ts_code"] == ts_code]
        if match.empty:
            return {"ts_code": ts_code, "name": ts_code, "market": None}
        row = match.iloc[0].to_dict()
        row["list_date"] = normalize_date(row.get("list_date"))
        return row

    frame = pro.fund_basic(
        market="E",
        fields="ts_code,name,management,custodian,fund_type,found_date,due_date",
    )
    match = frame[frame["ts_code"] == ts_code]
    if match.empty:
        return {"ts_code": ts_code, "name": ts_code, "market": "E"}
    row = match.iloc[0].to_dict()
    return {
        "ts_code": row.get("ts_code", ts_code),
        "name": row.get("name", ts_code),
        "market": "E",
        "industry": row.get("fund_type"),
        "area": None,
        "list_date": normalize_date(row.get("found_date")),
    }


def fetch_bars(ts_code, asset_type, freq, start_date=None, end_date=None):
    pro = pro_api()
    start = (start_date or "20180101").replace("-", "")
    end = (end_date or datetime.now().strftime("%Y%m%d")).replace("-", "")

    if asset_type == "stock":
        frame = pro.daily(ts_code=ts_code, start_date=start, end_date=end) if freq == "daily" else pro.weekly(ts_code=ts_code, start_date=start, end_date=end)
    else:
        api = pro.fund_daily if freq == "daily" else pro.fund_weekly
        frame = api(ts_code=ts_code, start_date=start, end_date=end)

    if frame is None or frame.empty:
        return []

    frame = frame.sort_values("trade_date")
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "trade_date": normalize_date(row.get("trade_date")),
                "open": _number(row.get("open")),
                "high": _number(row.get("high")),
                "low": _number(row.get("low")),
                "close": _number(row.get("close")),
                "volume": _number(row.get("vol")),
                "amount": _number(row.get("amount")),
            }
        )
    return rows


def _number(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return float(value)
