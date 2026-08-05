from math import sqrt


def _number(value):
    return float(value) if value is not None else None


def _round(value, digits=4):
    return None if value is None else round(value, digits)


def _pct(value):
    return None if value is None else round(value * 100, 2)


def _last_present(values):
    for value in reversed(values):
        if value is not None:
            return value
    return None


def _percentile(values, current):
    clean = [value for value in values if value is not None]
    if current is None or not clean:
        return None
    below_or_equal = sum(1 for value in clean if value <= current)
    return round(below_or_equal / len(clean) * 100, 1)


def sma(values, window):
    output = []
    for index in range(len(values)):
        chunk = values[index + 1 - window : index + 1]
        if index + 1 < window or any(value is None for value in chunk):
            output.append(None)
            continue
        output.append(round(sum(chunk) / window, 4))
    return output


def ema(values, span):
    output = []
    multiplier = 2 / (span + 1)
    current = None
    for value in values:
        if value is None:
            output.append(None)
            continue
        current = value if current is None else (value - current) * multiplier + current
        output.append(round(current, 4))
    return output


def rsi(values, window=14):
    output = [None] if values else []
    gains = []
    losses = []
    for index in range(1, len(values)):
        if values[index] is None or values[index - 1] is None:
            gains.append(None)
            losses.append(None)
            output.append(None)
            continue
        diff = values[index] - values[index - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
        recent_gains = gains[-window:]
        recent_losses = losses[-window:]
        if index < window or any(value is None for value in recent_gains + recent_losses):
            output.append(None)
            continue
        avg_gain = sum(recent_gains) / window
        avg_loss = sum(recent_losses) / window
        if avg_loss == 0:
            output.append(100)
        else:
            rs = avg_gain / avg_loss
            output.append(round(100 - (100 / (1 + rs)), 4))
    return output


def macd(values):
    ema12 = ema(values, 12)
    ema26 = ema(values, 26)
    dif = [None if a is None or b is None else round(a - b, 4) for a, b in zip(ema12, ema26)]
    dea = ema(dif, 9)
    bars = [None if d is None or e is None else round((d - e) * 2, 4) for d, e in zip(dif, dea)]
    return {"dif": dif, "dea": dea, "macd": bars}


def bollinger(values, window=20, width=2):
    middle = sma(values, window)
    upper = []
    lower = []
    for index, mid in enumerate(middle):
        chunk = values[index + 1 - window : index + 1]
        if mid is None or any(value is None for value in chunk):
            upper.append(None)
            lower.append(None)
            continue
        variance = sum((value - mid) ** 2 for value in chunk) / window
        band = sqrt(variance) * width
        upper.append(round(mid + band, 4))
        lower.append(round(mid - band, 4))
    return {"upper": upper, "mid": middle, "lower": lower}


def atr(bars, window=14):
    true_ranges = []
    output = []
    previous_close = None
    for row in bars:
        high = _number(row.get("high"))
        low = _number(row.get("low"))
        close = _number(row.get("close"))
        if high is None or low is None:
            true_ranges.append(None)
            output.append(None)
            previous_close = close
            continue
        if previous_close is None:
            true_range = high - low
        else:
            true_range = max(high - low, abs(high - previous_close), abs(low - previous_close))
        true_ranges.append(true_range)
        chunk = true_ranges[-window:]
        output.append(None if len(chunk) < window or any(value is None for value in chunk) else round(sum(chunk) / window, 4))
        previous_close = close
    return output


def rolling_return(values, window):
    output = []
    for index, value in enumerate(values):
        if index < window or value is None or values[index - window] in (None, 0):
            output.append(None)
            continue
        output.append(round((value / values[index - window] - 1) * 100, 2))
    return output


def rolling_volatility(values, window, periods_per_year=252):
    output = []
    returns = [None]
    for index in range(1, len(values)):
        if values[index] is None or values[index - 1] in (None, 0):
            returns.append(None)
        else:
            returns.append(values[index] / values[index - 1] - 1)
    for index in range(len(values)):
        chunk = returns[index + 1 - window : index + 1]
        if index + 1 < window or any(value is None for value in chunk):
            output.append(None)
            continue
        mean = sum(chunk) / window
        variance = sum((value - mean) ** 2 for value in chunk) / window
        output.append(round(sqrt(variance) * sqrt(periods_per_year) * 100, 2))
    return output


def obv(closes, volumes):
    output = []
    current = 0
    for index, close in enumerate(closes):
        volume = volumes[index] or 0
        if index == 0 or close is None or closes[index - 1] is None:
            output.append(current)
        elif close > closes[index - 1]:
            current += volume
            output.append(round(current, 2))
        elif close < closes[index - 1]:
            current -= volume
            output.append(round(current, 2))
        else:
            output.append(round(current, 2))
    return output


def max_drawdown(values):
    peak = None
    worst = 0
    for value in values:
        if value is None:
            continue
        peak = value if peak is None else max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1)
    return round(worst * 100, 2)


def build_indicators(bars):
    closes = [_number(row.get("close")) for row in bars]
    volumes = [_number(row.get("volume")) for row in bars]
    dates = [row.get("trade_date") for row in bars]
    macd_values = macd(closes)
    return {
        "dates": dates,
        "ma5": sma(closes, 5),
        "ma10": sma(closes, 10),
        "ma20": sma(closes, 20),
        "ma60": sma(closes, 60),
        "ema12": ema(closes, 12),
        "ema26": ema(closes, 26),
        "rsi14": rsi(closes, 14),
        "macd": macd_values,
        "boll": bollinger(closes, 20),
        "atr14": atr(bars, 14),
        "volume_ma20": sma(volumes, 20),
        "obv": obv(closes, volumes),
    }


def build_overview(bars, indicators):
    closes = [_number(row.get("close")) for row in bars]
    volumes = [_number(row.get("volume")) for row in bars]
    amounts = [_number(row.get("amount")) for row in bars]
    latest_close = _last_present(closes)
    first_close = next((value for value in closes if value is not None), None)
    volume_ma20 = _last_present(indicators.get("volume_ma20", []))
    latest_volume = _last_present(volumes)
    latest_amount = _last_present(amounts)
    return {
        "latest_close": _round(latest_close, 3),
        "period_return_pct": _pct(latest_close / first_close - 1) if latest_close is not None and first_close not in (None, 0) else None,
        "return_20d_pct": _last_present(rolling_return(closes, 20)),
        "volatility_20d_pct": _last_present(rolling_volatility(closes, 20)),
        "volume_ratio_20d": _round(latest_volume / volume_ma20, 2) if latest_volume is not None and volume_ma20 not in (None, 0) else None,
        "latest_amount": _round(latest_amount, 2),
        "max_drawdown_pct": max_drawdown(closes),
    }


def _factor(key, label, group, value, unit="", percentile=None, direction="neutral"):
    return {
        "key": key,
        "label": label,
        "group": group,
        "value": value,
        "unit": unit,
        "percentile": percentile,
        "direction": direction,
    }


def build_factors(bars, indicators):
    closes = [_number(row.get("close")) for row in bars]
    volumes = [_number(row.get("volume")) for row in bars]
    return_20 = rolling_return(closes, 20)
    return_60 = rolling_return(closes, 60)
    return_120 = rolling_return(closes, 120)
    vol_20 = rolling_volatility(closes, 20)
    ma20 = indicators.get("ma20", [])
    ma60 = indicators.get("ma60", [])
    latest_close = _last_present(closes)
    latest_volume = _last_present(volumes)
    latest_volume_ma20 = _last_present(indicators.get("volume_ma20", []))
    trend_ma20 = []
    trend_ma60 = []
    for close, avg20, avg60 in zip(closes, ma20, ma60):
        trend_ma20.append(None if close is None or avg20 in (None, 0) else round((close / avg20 - 1) * 100, 2))
        trend_ma60.append(None if close is None or avg60 in (None, 0) else round((close / avg60 - 1) * 100, 2))
    volume_ratio = [
        None if volume is None or avg in (None, 0) else round(volume / avg, 2)
        for volume, avg in zip(volumes, indicators.get("volume_ma20", []))
    ]
    rsi_values = indicators.get("rsi14", [])
    atr_values = indicators.get("atr14", [])
    return [
        _factor("mom20", "20日动量", "动量", _last_present(return_20), "%", _percentile(return_20, _last_present(return_20)), "higher"),
        _factor("mom60", "60日动量", "动量", _last_present(return_60), "%", _percentile(return_60, _last_present(return_60)), "higher"),
        _factor("mom120", "120日动量", "动量", _last_present(return_120), "%", _percentile(return_120, _last_present(return_120)), "higher"),
        _factor("ma20_gap", "偏离MA20", "趋势", _last_present(trend_ma20), "%", _percentile(trend_ma20, _last_present(trend_ma20)), "neutral"),
        _factor("ma60_gap", "偏离MA60", "趋势", _last_present(trend_ma60), "%", _percentile(trend_ma60, _last_present(trend_ma60)), "neutral"),
        _factor("vol20", "20日波动率", "波动", _last_present(vol_20), "%", _percentile(vol_20, _last_present(vol_20)), "lower"),
        _factor("atr14", "ATR14", "波动", _last_present(atr_values), "", _percentile(atr_values, _last_present(atr_values)), "neutral"),
        _factor("volume_ratio", "量能倍率", "量价", _round(latest_volume / latest_volume_ma20, 2) if latest_volume is not None and latest_volume_ma20 not in (None, 0) else None, "x", _percentile(volume_ratio, _last_present(volume_ratio)), "neutral"),
        _factor("obv", "OBV", "量价", _last_present(indicators.get("obv", [])), "", None, "neutral"),
        _factor("rsi14", "RSI14", "反转", _last_present(rsi_values), "", _percentile(rsi_values, _last_present(rsi_values)), "neutral"),
        _factor("drawdown", "最大回撤", "风险", max_drawdown(closes), "%", None, "lower"),
    ]


def build_market_snapshot(bars):
    rows = [dict(row) for row in bars]
    indicators = build_indicators(rows)
    return {
        "indicators": indicators,
        "overview": build_overview(rows, indicators),
        "factors": build_factors(rows, indicators),
    }
