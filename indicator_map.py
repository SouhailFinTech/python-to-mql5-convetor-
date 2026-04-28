"""
Hardcoded Python → MQL5 indicator translation dictionary.
This is the core knowledge layer — deterministic, no AI involved.
"""

INDICATOR_MAP = {
    # ─── MOVING AVERAGES ───────────────────────────────────────────
    "ta.sma": {
        "mql5_func": "iMA", "ma_method": "MODE_SMA",
        "params": ["period"], "buffer": 0, "handle_required": True,
        "aliases": ["SMA", "sma", "rolling_mean"]
    },
    "ta.ema": {
        "mql5_func": "iMA", "ma_method": "MODE_EMA",
        "params": ["period"], "buffer": 0, "handle_required": True,
        "aliases": ["EMA", "ema", "ewm_mean"]
    },
    "ta.wma": {
        "mql5_func": "iMA", "ma_method": "MODE_LWMA",
        "params": ["period"], "buffer": 0, "handle_required": True,
    },
    "ta.dema": {
        "mql5_func": "iMA", "ma_method": "MODE_DEMA",
        "params": ["period"], "buffer": 0, "handle_required": True,
    },
    "ta.tema": {
        "mql5_func": "iMA", "ma_method": "MODE_TEMA",
        "params": ["period"], "buffer": 0, "handle_required": True,
    },

    # ─── OSCILLATORS ───────────────────────────────────────────────
    "ta.rsi": {
        "mql5_func": "iRSI",
        "params": ["period"], "buffer": 0, "handle_required": True,
        "aliases": ["RSI", "rsi"]
    },
    "ta.macd": {
        "mql5_func": "iMACD",
        "params": ["fast_period", "slow_period", "signal_period"],
        "buffers": {"macd": 0, "signal": 1, "histogram": 2},
        "handle_required": True, "aliases": ["MACD", "macd"]
    },
    "ta.stoch": {
        "mql5_func": "iStochastic",
        "params": ["k_period", "d_period", "slowing"],
        "buffers": {"k": 0, "d": 1},
        "handle_required": True, "aliases": ["STOCH", "stoch"]
    },
    "ta.cci": {
        "mql5_func": "iCCI",
        "params": ["period"], "buffer": 0, "handle_required": True,
        "aliases": ["CCI", "cci"]
    },
    "ta.adx": {
        "mql5_func": "iADX",
        "params": ["period"],
        "buffers": {"adx": 0, "plus_di": 1, "minus_di": 2},
        "handle_required": True, "aliases": ["ADX", "adx"]
    },
    "ta.mfi": {
        "mql5_func": "iMFI",
        "params": ["period"], "buffer": 0, "handle_required": True,
    },
    "ta.mom": {
        "mql5_func": "iMomentum",
        "params": ["period"], "buffer": 0, "handle_required": True,
    },
    "ta.willr": {
        "mql5_func": "iWPR",
        "params": ["period"], "buffer": 0, "handle_required": True,
    },

    # ─── VOLATILITY ────────────────────────────────────────────────
    "ta.bbands": {
        "mql5_func": "iBands",
        "params": ["period", "deviation"],
        "buffers": {"upper": 1, "mid": 0, "lower": 2},
        "handle_required": True, "aliases": ["BBANDS", "bbands", "BollingerBands"]
    },
    "ta.atr": {
        "mql5_func": "iATR",
        "params": ["period"], "buffer": 0, "handle_required": True,
        "aliases": ["ATR", "atr"]
    },
    "ta.donchian": {
        "mql5_func": "iHighest_iLowest",  # custom — uses iHighest + iLowest
        "params": ["period"], "handle_required": False,
        "aliases": ["donchian", "DC"]
    },

    # ─── VOLUME ────────────────────────────────────────────────────
    "ta.obv": {
        "mql5_func": "iOBV",
        "params": [], "buffer": 0, "handle_required": True,
    },
    "ta.ad": {
        "mql5_func": "iAD",
        "params": [], "buffer": 0, "handle_required": True,
    },
}

# ─── CRITICAL ARRAY INDEX TRANSLATION ─────────────────────────────
# Python iloc[-1] = latest bar = MQL5 array[0] (after ArraySetAsSeries=true)
ARRAY_INDEX_MAP = {
    "iloc[-1]": "[0]",   # current bar
    "iloc[-2]": "[1]",   # previous bar
    "iloc[-3]": "[2]",
    ".iloc[0]": "[0]",
    "[-1]":     "[0]",
    "[-2]":     "[1]",
    "[-3]":     "[2]",
}

# ─── PYTHON OPERATOR → MQL5 ────────────────────────────────────────
OPERATOR_MAP = {
    "and": "&&",
    "or":  "||",
    "not": "!",
    "True": "true",
    "False": "false",
    "None": "NULL",
    "**": "MathPow",
    "abs(": "MathAbs(",
    "math.sqrt(": "MathSqrt(",
    "math.log(": "MathLog(",
    "math.floor(": "MathFloor(",
    "math.ceil(": "MathCeil(",
    "round(": "MathRound(",
    "max(": "MathMax(",
    "min(": "MathMin(",
    "len(": "ArraySize(",
    "print(": "Print(",
}

# ─── OHLCV ACCESS PATTERNS ─────────────────────────────────────────
OHLCV_MAP = {
    "df['close']":  "close",
    "df['open']":   "open_price",
    "df['high']":   "high",
    "df['low']":    "low",
    "df['volume']": "tick_volume",
    "close_prices": "close",
    "data['close']": "close",
    "data['high']":  "high",
    "data['low']":   "low",
}

# ─── ORDER LOGIC PATTERNS ──────────────────────────────────────────
ORDER_PATTERNS = {
    "buy":  "trade.Buy(lot_size, _Symbol, 0, sl_price, tp_price, \"Buy Signal\");",
    "sell": "trade.Sell(lot_size, _Symbol, 0, sl_price, tp_price, \"Sell Signal\");",
    "close_buy":  "trade.PositionClose(_Symbol);",
    "close_sell": "trade.PositionClose(_Symbol);",
    "close_all":  "trade.PositionClose(_Symbol);",
}

# ─── COMMON PATTERN DETECTION ──────────────────────────────────────
PATTERN_KEYWORDS = {
    "crossover":   ["crossover", "cross_above", "crossed_above", "> prev"],
    "crossunder":  ["crossunder", "cross_below", "crossed_below", "< prev"],
    "overbought":  ["overbought", "> 70", "> 80", "> 75"],
    "oversold":    ["oversold", "< 30", "< 20", "< 25"],
    "new_bar":     ["new_bar", "bar_count", "is_new_candle", "new_candle"],
}
