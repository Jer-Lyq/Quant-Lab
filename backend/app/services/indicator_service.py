def sma(values, window):
    output = []
    for i in range(len(values)):
        if i + 1 < window:
            output.append(None)
            continue
        chunk = values[i + 1 - window : i + 1]
        output.append(round(sum(chunk) / window, 4))
    return output


def ema(values, span):
    output = []
    multiplier = 2 / (span + 1)
    current = None
    for value in values:
        current = value if current is None else (value - current) * multiplier + current
        output.append(current)
    return output


def rsi(values, window=14):
    if not values:
        return []
    output = [None]
    gains = []
    losses = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
        if i < window:
            output.append(None)
            continue
        avg_gain = sum(gains[-window:]) / window
        avg_loss = sum(losses[-window:]) / window
        if avg_loss == 0:
            output.append(100)
        else:
            rs = avg_gain / avg_loss
            output.append(round(100 - (100 / (1 + rs)), 4))
    return output


def macd(values):
    ema12 = ema(values, 12)
    ema26 = ema(values, 26)
    dif = [a - b for a, b in zip(ema12, ema26)]
    dea = ema(dif, 9)
    bars = [(d - e) * 2 for d, e in zip(dif, dea)]
    return {
        "dif": [round(v, 4) for v in dif],
        "dea": [round(v, 4) for v in dea],
        "macd": [round(v, 4) for v in bars],
    }


def build_indicators(bars):
    closes = [float(row["close"]) for row in bars if row["close"] is not None]
    dates = [row["trade_date"] for row in bars if row["close"] is not None]
    if not closes:
        return {
            "dates": dates,
            "ma5": [],
            "ma10": [],
            "ma20": [],
            "rsi14": [],
            "macd": {"dif": [], "dea": [], "macd": []},
        }
    macd_values = macd(closes)
    return {
        "dates": dates,
        "ma5": sma(closes, 5),
        "ma10": sma(closes, 10),
        "ma20": sma(closes, 20),
        "rsi14": rsi(closes, 14),
        "macd": macd_values,
    }
