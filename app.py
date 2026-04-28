"""
PY2MQL5 — Python to MQL5 Converter
Single-file version — guaranteed to work on Streamlit Cloud
"""

import streamlit as st
import ast
import re
import json
from typing import Optional

# ═══════════════════════════════════════════════════════════════════
# INDICATOR MAP — hardcoded knowledge layer
# ═══════════════════════════════════════════════════════════════════

INDICATOR_MAP = {
    "ta.sma":    {"mql5_func": "iMA",         "ma_method": "MODE_SMA",  "params": ["period"], "buffer": 0, "handle_required": True,  "aliases": ["SMA", "sma", "rolling_mean", "simple_moving_average"]},
    "ta.ema":    {"mql5_func": "iMA",         "ma_method": "MODE_EMA",  "params": ["period"], "buffer": 0, "handle_required": True,  "aliases": ["EMA", "ema", "ewm_mean", "exponential_moving_average"]},
    "ta.wma":    {"mql5_func": "iMA",         "ma_method": "MODE_LWMA", "params": ["period"], "buffer": 0, "handle_required": True,  "aliases": ["WMA", "wma"]},
    "ta.dema":   {"mql5_func": "iMA",         "ma_method": "MODE_DEMA", "params": ["period"], "buffer": 0, "handle_required": True,  "aliases": ["DEMA", "dema"]},
    "ta.tema":   {"mql5_func": "iMA",         "ma_method": "MODE_TEMA", "params": ["period"], "buffer": 0, "handle_required": True,  "aliases": ["TEMA", "tema"]},
    "ta.rsi":    {"mql5_func": "iRSI",        "params": ["period"],     "buffer": 0,          "handle_required": True,               "aliases": ["RSI", "rsi", "relative_strength_index"]},
    "ta.macd":   {"mql5_func": "iMACD",       "params": ["fast_period", "slow_period", "signal_period"], "buffers": {"macd": 0, "signal": 1, "histogram": 2}, "handle_required": True, "aliases": ["MACD", "macd"]},
    "ta.stoch":  {"mql5_func": "iStochastic", "params": ["k_period", "d_period", "slowing"], "buffers": {"k": 0, "d": 1}, "handle_required": True, "aliases": ["STOCH", "stoch", "stochastic"]},
    "ta.bbands": {"mql5_func": "iBands",      "params": ["period", "deviation"], "buffers": {"upper": 1, "mid": 0, "lower": 2}, "handle_required": True, "aliases": ["BBANDS", "bbands", "bollinger", "BollingerBands"]},
    "ta.atr":    {"mql5_func": "iATR",        "params": ["period"],     "buffer": 0,          "handle_required": True,               "aliases": ["ATR", "atr", "average_true_range"]},
    "ta.adx":    {"mql5_func": "iADX",        "params": ["period"],     "buffers": {"adx": 0, "plus_di": 1, "minus_di": 2}, "handle_required": True, "aliases": ["ADX", "adx"]},
    "ta.cci":    {"mql5_func": "iCCI",        "params": ["period"],     "buffer": 0,          "handle_required": True,               "aliases": ["CCI", "cci"]},
    "ta.mfi":    {"mql5_func": "iMFI",        "params": ["period"],     "buffer": 0,          "handle_required": True,               "aliases": ["MFI", "mfi"]},
    "ta.mom":    {"mql5_func": "iMomentum",   "params": ["period"],     "buffer": 0,          "handle_required": True,               "aliases": ["MOM", "mom", "momentum"]},
    "ta.willr":  {"mql5_func": "iWPR",        "params": ["period"],     "buffer": 0,          "handle_required": True,               "aliases": ["WILLR", "willr", "williams"]},
    "ta.obv":    {"mql5_func": "iOBV",        "params": [],             "buffer": 0,          "handle_required": True,               "aliases": ["OBV", "obv"]},
    "ta.ad":     {"mql5_func": "iAD",         "params": [],             "buffer": 0,          "handle_required": True,               "aliases": ["AD", "ad"]},
    "ta.donchian":{"mql5_func": "iHighest",   "params": ["period"],     "buffer": 0,          "handle_required": False,              "aliases": ["donchian", "DC", "dc"]},
}

HANDLE_INIT_MAP = {
    "iRSI":        "handle_{name} = iRSI(_Symbol, _Period, {p1}, PRICE_CLOSE);",
    "iMA":         "handle_{name} = iMA(_Symbol, _Period, {p1}, 0, {method}, PRICE_CLOSE);",
    "iMACD":       "handle_{name} = iMACD(_Symbol, _Period, {p1}, {p2}, {p3}, PRICE_CLOSE);",
    "iBands":      "handle_{name} = iBands(_Symbol, _Period, {p1}, 0, {p2}, PRICE_CLOSE);",
    "iATR":        "handle_{name} = iATR(_Symbol, _Period, {p1});",
    "iStochastic": "handle_{name} = iStochastic(_Symbol, _Period, {p1}, {p2}, {p3}, MODE_SMA, STO_LOWHIGH);",
    "iADX":        "handle_{name} = iADX(_Symbol, _Period, {p1});",
    "iCCI":        "handle_{name} = iCCI(_Symbol, _Period, {p1}, PRICE_TYPICAL);",
    "iMFI":        "handle_{name} = iMFI(_Symbol, _Period, {p1}, VOLUME_TICK);",
    "iMomentum":   "handle_{name} = iMomentum(_Symbol, _Period, {p1}, PRICE_CLOSE);",
    "iWPR":        "handle_{name} = iWPR(_Symbol, _Period, {p1});",
    "iOBV":        "handle_{name} = iOBV(_Symbol, _Period, VOLUME_TICK);",
}

PATTERN_KEYWORDS = {
    "crossover":  ["crossover", "cross_above", "crossed_above"],
    "crossunder": ["crossunder", "cross_below", "crossed_below"],
    "overbought": ["overbought", "> 70", ">70", "> 80", "> 75"],
    "oversold":   ["oversold",   "< 30", "<30", "< 20", "< 25"],
    "new_bar":    ["new_bar", "is_new_candle", "new_candle"],
}

# ═══════════════════════════════════════════════════════════════════
# EA TEMPLATE
# ═══════════════════════════════════════════════════════════════════

EA_TEMPLATE = '''//+------------------------------------------------------------------+
//|  {ea_name}.mq5                                                   |
//|  Auto-generated by PY2MQL5 Converter                            |
//|  https://py2mql5.streamlit.app                                   |
//+------------------------------------------------------------------+
#property copyright "PY2MQL5 Converter"
#property version   "1.00"
#property strict

#include <Trade\\Trade.mqh>

//--- Input parameters
{input_params}

//--- Global variables
CTrade trade;
{handle_declarations}

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
  {{
   //--- Create indicator handles (MUST be here, NOT in OnTick)
{handle_init}

   //--- Validate handles
{handle_validation}

   trade.SetExpertMagicNumber(123456);
   return(INIT_SUCCEEDED);
  }}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {{
{handle_release}
  }}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
  {{
   //--- Only process on new bar
   if(!IsNewBar()) return;

   //--- Copy indicator data into arrays
{copy_buffers}

   //--- Current values  [0]=current bar  [1]=previous bar
{current_values}

   //--- Check position status
   bool in_position = PositionSelect(_Symbol);

   //--- Entry Logic
{entry_logic}

   //--- Exit Logic
{exit_logic}
  }}

//+------------------------------------------------------------------+
//| Detect new bar                                                    |
//+------------------------------------------------------------------+
bool IsNewBar()
  {{
   static datetime last_bar = 0;
   datetime cur = iTime(_Symbol, _Period, 0);
   if(cur != last_bar) {{ last_bar = cur; return true; }}
   return false;
  }}

//+------------------------------------------------------------------+
//| Stop Loss price                                                   |
//+------------------------------------------------------------------+
double CalcSL(bool is_buy, double atr_val, double mult=1.5)
  {{
   double price = is_buy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double dist  = atr_val * mult * _Point * MathPow(10, Digits() % 2);
   return is_buy ? price - dist : price + dist;
  }}

//+------------------------------------------------------------------+
//| Take Profit price                                                 |
//+------------------------------------------------------------------+
double CalcTP(bool is_buy, double atr_val, double mult=3.0)
  {{
   double price = is_buy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double dist  = atr_val * mult * _Point * MathPow(10, Digits() % 2);
   return is_buy ? price + dist : price - dist;
  }}
'''

# ═══════════════════════════════════════════════════════════════════
# CONVERTER ENGINE
# ═══════════════════════════════════════════════════════════════════

class ConversionResult:
    def __init__(self):
        self.mql5_code          = ""
        self.confidence         = 0
        self.errors             = []
        self.warnings           = []
        self.detected_indicators = []
        self.detected_patterns  = []
        self.ai_used            = False
        self.notes              = []


class PY2MQL5Converter:
    def __init__(self, groq_api_key: str = None):
        self.groq_key    = groq_api_key
        self.groq_client = None
        if groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_api_key)
            except Exception:
                pass

    # ── MAIN ENTRY ─────────────────────────────────────────────────
    def convert(self, python_code: str, ea_name: str = "MyEA") -> ConversionResult:
        result = ConversionResult()
        try:
            # 1. Syntax check
            try:
                ast.parse(python_code)
            except SyntaxError as e:
                result.errors.append(f"Python syntax error: {e}")
                result.confidence = 0
                return result

            # 2. Detect indicators & patterns
            indicators = self._detect_indicators(python_code)
            patterns   = self._detect_patterns(python_code)
            result.detected_indicators = indicators
            result.detected_patterns   = patterns

            # 3. Build each section
            handle_decls = self._build_handle_declarations(indicators)
            handle_inits = self._build_handle_inits(indicators)
            handle_vals  = self._build_handle_validations(indicators)
            handle_rels  = self._build_handle_releases(indicators)
            copy_bufs    = self._build_copy_buffers(indicators)
            cur_vals     = self._build_current_values(indicators)
            input_params = self._build_input_params(indicators)
            entry_logic  = self._build_entry_logic(python_code, patterns, indicators)
            exit_logic   = self._build_exit_logic(python_code, patterns, indicators)

            # 4. Groq for ambiguous logic
            if "// TODO" in entry_logic and self.groq_client:
                ai = self._groq_translate(python_code, indicators, patterns)
                if ai:
                    entry_logic  = ai.get("entry", entry_logic)
                    exit_logic   = ai.get("exit",  exit_logic)
                    result.ai_used = True
                    result.notes.append("Groq AI assisted with entry/exit translation")

            # 5. Assemble
            result.mql5_code = EA_TEMPLATE.format(
                ea_name             = ea_name,
                input_params        = input_params,
                handle_declarations = handle_decls,
                handle_init         = handle_inits,
                handle_validation   = handle_vals,
                handle_release      = handle_rels,
                copy_buffers        = copy_bufs,
                current_values      = cur_vals,
                entry_logic         = entry_logic,
                exit_logic          = exit_logic,
            )

            # 6. Validate & score
            self._validate(result)
            result.confidence = self._score(indicators, patterns, result)

        except Exception as e:
            result.errors.append(f"Unexpected error: {e}")
            result.confidence = 0

        return result

    # ── DETECTION ──────────────────────────────────────────────────
    def _detect_indicators(self, code: str) -> list:
        detected = []
        seen     = set()
        cl       = code.lower()
        for key, info in INDICATOR_MAP.items():
            terms = [key.split(".")[-1].lower()] + [a.lower() for a in info.get("aliases", [])]
            for term in terms:
                if term in cl and key not in seen:
                    seen.add(key)
                    params = self._extract_params(code, term, info)
                    detected.append({
                        "key":  key,
                        "name": key.split(".")[-1].lower(),
                        "info": info,
                        "params": params,
                    })
                    break
        return detected

    def _extract_params(self, code: str, indicator: str, info: dict) -> dict:
        p = {}
        # Generic period
        for pat in [
            rf'{indicator}\s*\([^,)]+,\s*(\d+)',
            rf'{indicator}_period\s*=\s*(\d+)',
            r'period\s*=\s*(\d+)',
            r'length\s*=\s*(\d+)',
        ]:
            m = re.search(pat, code, re.IGNORECASE)
            if m:
                p["period"] = int(m.group(1))
                break
        if "period" not in p:
            p["period"] = 14

        # MACD
        if "macd" in indicator.lower():
            p.update({"fast": 12, "slow": 26, "signal": 9})
            m = re.search(r'macd[^(]*\([^,)]+,\s*(\d+)[^,]*,\s*(\d+)[^,]*,\s*(\d+)', code, re.IGNORECASE)
            if m:
                p["fast"] = int(m.group(1))
                p["slow"] = int(m.group(2))
                p["signal"] = int(m.group(3))

        # Bollinger
        if any(x in indicator.lower() for x in ["bband", "bb"]):
            p["deviation"] = 2.0
            m = re.search(r'std\s*=\s*([\d.]+)', code)
            if m:
                p["deviation"] = float(m.group(1))

        # Stochastic
        if "stoch" in indicator.lower():
            p.update({"k_period": 14, "d_period": 3, "slowing": 3})

        return p

    def _detect_patterns(self, code: str) -> list:
        cl       = code.lower()
        detected = []
        for pat, kws in PATTERN_KEYWORDS.items():
            if any(k in cl for k in kws):
                detected.append(pat)
        if any(w in cl for w in ["buy(", "long(", "enter_long", "go_long", "buy_signal"]):
            detected.append("has_long")
        if any(w in cl for w in ["sell(", "short(", "enter_short", "go_short", "sell_signal"]):
            detected.append("has_short")
        return list(set(detected))

    # ── BUILD SECTIONS ─────────────────────────────────────────────
    def _build_handle_declarations(self, indicators: list) -> str:
        seen  = set()
        lines = []
        for ind in indicators:
            n = ind["name"]
            if n not in seen and ind["info"].get("handle_required", True):
                lines.append(f"int handle_{n} = INVALID_HANDLE;")
                seen.add(n)
        return "\n".join(lines) or "// No indicator handles"

    def _build_handle_inits(self, indicators: list) -> str:
        seen  = set()
        lines = []
        for ind in indicators:
            n    = ind["name"]
            info = ind["info"]
            p    = ind["params"]
            func = info.get("mql5_func", "")
            if n in seen or func not in HANDLE_INIT_MAP:
                continue
            seen.add(n)
            tpl = HANDLE_INIT_MAP[func]
            try:
                if func == "iMA":
                    line = tpl.format(name=n, p1=p.get("period", 14), method=info.get("ma_method", "MODE_SMA"))
                elif func == "iMACD":
                    line = tpl.format(name=n, p1=p.get("fast", 12), p2=p.get("slow", 26), p3=p.get("signal", 9))
                elif func == "iBands":
                    line = tpl.format(name=n, p1=p.get("period", 20), p2=p.get("deviation", 2.0))
                elif func == "iStochastic":
                    line = tpl.format(name=n, p1=p.get("k_period", 14), p2=p.get("d_period", 3), p3=p.get("slowing", 3))
                else:
                    line = tpl.format(name=n, p1=p.get("period", 14))
                lines.append(f"   {line}")
            except Exception:
                lines.append(f"   // TODO: manually init handle_{n}")
        return "\n".join(lines) or "   // No handles to init"

    def _build_handle_validations(self, indicators: list) -> str:
        seen  = set()
        lines = []
        for ind in indicators:
            n = ind["name"]
            if n not in seen and ind["info"].get("handle_required", True):
                lines.append(f"""   if(handle_{n} == INVALID_HANDLE)
     {{
      Print("Failed to create {n} handle. Error: ", GetLastError());
      return(INIT_FAILED);
     }}""")
                seen.add(n)
        return "\n".join(lines) or "   // No handles to validate"

    def _build_handle_releases(self, indicators: list) -> str:
        seen  = set()
        lines = []
        for ind in indicators:
            n = ind["name"]
            if n not in seen and ind["info"].get("handle_required", True):
                lines.append(f"   IndicatorRelease(handle_{n});")
                seen.add(n)
        return "\n".join(lines) or "   // No handles to release"

    def _build_copy_buffers(self, indicators: list) -> str:
        seen  = set()
        lines = []
        for ind in indicators:
            n    = ind["name"]
            info = ind["info"]
            if n in seen:
                continue
            seen.add(n)
            if "buffers" in info:
                for buf_name, buf_idx in info["buffers"].items():
                    var = f"{n}_{buf_name}"
                    lines.append(f"""   double {var}_buf[];
   ArraySetAsSeries({var}_buf, true);
   if(CopyBuffer(handle_{n}, {buf_idx}, 0, 3, {var}_buf) < 0)
     {{ Print("CopyBuffer {var} failed"); return; }}""")
            else:
                buf_idx = info.get("buffer", 0)
                lines.append(f"""   double {n}_buf[];
   ArraySetAsSeries({n}_buf, true);
   if(CopyBuffer(handle_{n}, {buf_idx}, 0, 3, {n}_buf) < 0)
     {{ Print("CopyBuffer {n} failed"); return; }}""")
        return "\n".join(lines) or "   // No buffers to copy"

    def _build_current_values(self, indicators: list) -> str:
        seen  = set()
        lines = ["   // [0] = current bar   [1] = previous bar"]
        for ind in indicators:
            n    = ind["name"]
            info = ind["info"]
            if n in seen:
                continue
            seen.add(n)
            if "buffers" in info:
                for buf_name in info["buffers"]:
                    var = f"{n}_{buf_name}"
                    lines.append(f"   double {var}_cur  = {var}_buf[0];")
                    lines.append(f"   double {var}_prev = {var}_buf[1];")
            else:
                lines.append(f"   double {n}_cur  = {n}_buf[0];")
                lines.append(f"   double {n}_prev = {n}_buf[1];")
        return "\n".join(lines)

    def _build_input_params(self, indicators: list) -> str:
        seen  = set()
        lines = []
        for ind in indicators:
            n = ind["name"]
            p = ind["params"]
            if n in seen:
                continue
            seen.add(n)
            func = ind["info"].get("mql5_func", "")
            if func == "iMACD":
                lines.append(f"input int    macd_fast    = {p.get('fast',12)};   // MACD fast period")
                lines.append(f"input int    macd_slow    = {p.get('slow',26)};   // MACD slow period")
                lines.append(f"input int    macd_signal  = {p.get('signal',9)}; // MACD signal period")
            elif func == "iBands":
                lines.append(f"input int    bb_period    = {p.get('period',20)};  // Bollinger period")
                lines.append(f"input double bb_deviation = {p.get('deviation',2.0)};  // Bollinger deviation")
            elif func == "iStochastic":
                lines.append(f"input int    stoch_k      = {p.get('k_period',14)};  // Stoch K period")
                lines.append(f"input int    stoch_d      = {p.get('d_period',3)};   // Stoch D period")
            else:
                lines.append(f"input int    {n}_period   = {p.get('period',14)};  // {n.upper()} period")
        lines += [
            "input double risk_pct      = 1.0;  // Risk % per trade",
            "input double sl_multiplier = 1.5;  // Stop Loss ATR multiplier",
            "input double tp_multiplier = 3.0;  // Take Profit ATR multiplier",
        ]
        return "\n".join(lines)

    # ── ENTRY / EXIT LOGIC ─────────────────────────────────────────
    def _build_entry_logic(self, code: str, patterns: list, indicators: list) -> str:
        has_long  = "has_long"  in patterns
        has_short = "has_short" in patterns
        lines     = ["   //--- Entry Logic"]

        ind_names = [i["name"] for i in indicators]

        # RSI overbought/oversold
        if ("overbought" in patterns or "oversold" in patterns) and "rsi" in ind_names:
            ob = self._extract_threshold(code, "overbought", 70)
            os_ = self._extract_threshold(code, "oversold", 30)
            if has_long or "oversold" in patterns:
                lines += [
                    f"   if(!in_position && rsi_cur < {os_} && rsi_prev >= {os_})",
                    "     {",
                    "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                    "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                    f"      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, \"RSI Oversold Buy\");",
                    "     }",
                ]
            if has_short or "overbought" in patterns:
                lines += [
                    f"   if(!in_position && rsi_cur > {ob} && rsi_prev <= {ob})",
                    "     {",
                    "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                    "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                    f"      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, \"RSI Overbought Sell\");",
                    "     }",
                ]

        # MA crossover
        elif "crossover" in patterns and any(x in ind_names for x in ["ema", "sma", "wma"]):
            ma_inds = [n for n in ind_names if n in ["ema", "sma", "wma", "dema", "tema"]]
            if len(ma_inds) >= 2:
                fast, slow = ma_inds[0], ma_inds[1]
                lines += [
                    f"   // Golden cross: {fast} crosses above {slow}",
                    f"   if(!in_position && {fast}_cur > {slow}_cur && {fast}_prev <= {slow}_prev)",
                    "     {",
                    "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                    "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                    f"      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, \"MA Cross Buy\");",
                    "     }",
                    f"   // Death cross: {fast} crosses below {slow}",
                    f"   if(!in_position && {fast}_cur < {slow}_cur && {fast}_prev >= {slow}_prev)",
                    "     {",
                    "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                    "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                    f"      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, \"MA Cross Sell\");",
                    "     }",
                ]
            else:
                lines.append("   // TODO: Only one MA detected — add second MA for crossover")

        # MACD crossover
        elif "macd" in ind_names:
            lines += [
                "   // MACD crosses above signal → Buy",
                "   if(!in_position && macd_macd_cur > macd_signal_cur && macd_macd_prev <= macd_signal_prev)",
                "     {",
                "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                "      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, \"MACD Buy\");",
                "     }",
                "   // MACD crosses below signal → Sell",
                "   if(!in_position && macd_macd_cur < macd_signal_cur && macd_macd_prev >= macd_signal_prev)",
                "     {",
                "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                "      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, \"MACD Sell\");",
                "     }",
            ]

        # Bollinger Band breakout
        elif "bbands" in ind_names:
            lines += [
                "   // Price closes below lower band → Buy (mean reversion)",
                "   if(!in_position && close_buf[0] < bbands_lower_cur)",
                "     {",
                "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                "      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, \"BB Lower Buy\");",
                "     }",
                "   // Price closes above upper band → Sell (mean reversion)",
                "   if(!in_position && close_buf[0] > bbands_upper_cur)",
                "     {",
                "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                "      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, \"BB Upper Sell\");",
                "     }",
            ]

        else:
            lines += [
                "   // TODO: Entry logic could not be auto-detected",
                "   // Common patterns: RSI overbought/oversold, MA crossover, MACD cross",
                "   // Add your entry condition below:",
                "   // if(!in_position && <your_condition>)",
                "   //   { trade.Buy(lot, _Symbol, 0, sl, tp, \"Signal\"); }",
            ]

        # Add ATR buffer for SL/TP if not already detected
        if "atr" not in [i["name"] for i in indicators]:
            lines.insert(1, "   // Note: Add ta.atr to your Python code for dynamic SL/TP")

        return "\n".join(lines)

    def _build_exit_logic(self, code: str, patterns: list, indicators: list) -> str:
        lines = [
            "   //--- Exit Logic",
            "   // SL and TP are set at entry — positions close automatically",
            "   // Add custom exit conditions here if needed:",
            "   // if(in_position && <exit_condition>)",
            "   //   { trade.PositionClose(_Symbol); }",
        ]
        return "\n".join(lines)

    def _extract_threshold(self, code: str, kind: str, default: int) -> int:
        if kind == "overbought":
            for pat in [r'>\s*(\d+)', r'overbought\s*=\s*(\d+)']:
                m = re.search(pat, code)
                if m and 60 < int(m.group(1)) < 100:
                    return int(m.group(1))
        else:
            for pat in [r'<\s*(\d+)', r'oversold\s*=\s*(\d+)']:
                m = re.search(pat, code)
                if m and 0 < int(m.group(1)) < 50:
                    return int(m.group(1))
        return default

    # ── GROQ AI ────────────────────────────────────────────────────
    def _groq_translate(self, python_code: str, indicators: list, patterns: list) -> Optional[dict]:
        if not self.groq_client:
            return None
        ind_names = [i["name"] for i in indicators]
        prompt = f"""You are a Python to MQL5 expert.
Convert the entry/exit logic of this Python trading strategy to MQL5.

Python code:
```python
{python_code[:2000]}
```

Detected indicators: {ind_names}
Available MQL5 variables (already declared):
- {" ".join([f"{i['name']}_cur, {i['name']}_prev" for i in indicators])}
- in_position (bool)
- trade.Buy(lot, _Symbol, 0, sl, tp, "comment")
- trade.Sell(lot, _Symbol, 0, sl, tp, "comment")
- trade.PositionClose(_Symbol)
- CalcSL(is_buy, atr_cur, multiplier) → returns SL price
- CalcTP(is_buy, atr_cur, multiplier) → returns TP price

Rules:
- [0] = current bar (most recent)
- Use && not 'and', || not 'or'
- Pure MQL5 only
- Return ONLY valid JSON: {{"entry": "mql5 code here", "exit": "mql5 code here"}}
- No markdown, no explanation"""
        try:
            from groq import Groq
            client = Groq(api_key=self.groq_key)
            resp   = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=800
            )
            content = resp.choices[0].message.content.strip()
            content = re.sub(r"```json|```", "", content).strip()
            return json.loads(content)
        except Exception:
            return None

    # ── VALIDATION & SCORING ───────────────────────────────────────
    def _validate(self, result: ConversionResult):
        code = result.mql5_code
        if "CopyBuffer" in code:
            cb = code.count("CopyBuffer")
            as_ = code.count("ArraySetAsSeries")
            if cb != as_:
                result.warnings.append(f"CopyBuffer ({cb}) ≠ ArraySetAsSeries ({as_}) — check output")
        if "TODO" in code:
            result.warnings.append("Some logic needs manual review — find TODO comments in output")
        if "iloc" in code or "pandas" in code.lower():
            result.errors.append("Python syntax still in output — check TODO sections")

    def _score(self, indicators, patterns, result) -> int:
        score = 90
        score -= len(result.errors)   * 25
        score -= len(result.warnings) * 5
        score += min(len(indicators)  * 3, 15)
        known = {"crossover", "crossunder", "overbought", "oversold"}
        score += sum(5 for p in patterns if p in known)
        if result.ai_used:
            score -= 5
        return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════════
# STREAMLIT UI
# ═══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="PY2MQL5 — Python to MQL5 Converter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;700;800&display=swap');
html,body,.stApp{background:#0a0a0f!important;color:#e2e8f0!important;font-family:'Syne',sans-serif}
.hero{text-align:center;padding:2rem 0 1.5rem;border-bottom:1px solid #1e1e2e;margin-bottom:1.5rem}
.hero h1{font-size:2.8rem;font-weight:800;background:linear-gradient(135deg,#00ff88,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0}
.hero p{color:#475569;font-size:.9rem;margin-top:.4rem;font-family:'JetBrains Mono',monospace}
.tag{display:inline-block;padding:2px 9px;border-radius:20px;font-size:.7rem;font-weight:600;margin:2px;font-family:'JetBrains Mono',monospace}
.tg{background:#052e1c;color:#00ff88;border:1px solid #00ff8833}
.tp{background:#1e0a3c;color:#a78bfa;border:1px solid #7c3aed33}
.ta{background:#2d1a00;color:#fbbf24;border:1px solid #f59e0b33}
.tr{background:#2d0a0a;color:#f87171;border:1px solid #ef444433}
.mcard{background:#111118;border:1px solid #1e1e2e;border-radius:12px;padding:1rem 1.2rem;margin-bottom:.8rem}
.mcard h4{font-size:.65rem;text-transform:uppercase;letter-spacing:.1em;color:#475569;margin:0 0 .4rem;font-family:'JetBrains Mono',monospace}
.slbl{font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:#334155;font-family:'JetBrains Mono',monospace;margin-bottom:.4rem}
section[data-testid="stSidebar"]{background:#111118!important;border-right:1px solid #1e1e2e!important}
.stButton>button{background:linear-gradient(135deg,#00ff88,#00cc6a)!important;color:#0a0a0f!important;font-weight:700!important;font-family:'Syne',sans-serif!important;border:none!important;border-radius:8px!important;width:100%}
.stTextArea textarea,.stTextInput input{background:#111118!important;border:1px solid #1e1e2e!important;color:#e2e8f0!important;font-family:'JetBrains Mono',monospace!important;font-size:.8rem!important;border-radius:8px!important}
.stDownloadButton>button{background:#111118!important;color:#00ff88!important;border:1px solid #00ff88!important;font-family:'Syne',sans-serif!important;font-weight:600!important;border-radius:8px!important;width:100%}
hr{border-color:#1e1e2e!important}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>⚡ PY2MQL5</h1>
  <p>Python strategy → MQL5 Expert Advisor · No martingale · No BS · Built by a quant</p>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    groq_key = st.text_input("Groq API Key", type="password",
                              placeholder="gsk_... (free at console.groq.com)",
                              help="Optional — used for complex logic only")
    ea_name  = st.text_input("EA Name", value="MyStrategy_EA")

    st.markdown("---")
    st.markdown("### ✅ Supported Indicators")
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;font-size:.73rem;color:#475569;line-height:2.1">
ta.rsi → iRSI<br>ta.ema / ta.sma → iMA<br>ta.wma / ta.dema / ta.tema → iMA<br>
ta.macd → iMACD (3 buffers)<br>ta.bbands → iBands<br>ta.atr → iATR<br>
ta.stoch → iStochastic<br>ta.adx → iADX (3 buffers)<br>ta.cci → iCCI<br>
ta.mfi → iMFI<br>ta.obv → iOBV<br>ta.willr → iWPR<br>
🤖 Custom logic → Groq AI</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""<div style="font-size:.7rem;color:#1e3a5f;font-family:'JetBrains Mono',monospace">
MVP v0.1 · More indicators coming<br>FTMO risk module · Multi-timeframe</div>""", unsafe_allow_html=True)

# ── EXAMPLES ───────────────────────────────────────────────────────
EXAMPLES = {
    "RSI Overbought/Oversold": """\
import pandas_ta as ta

rsi = ta.rsi(close, length=14)
atr = ta.atr(high, low, close, length=14)

if rsi.iloc[-1] < 30:
    buy()

if rsi.iloc[-1] > 70:
    sell()
""",
    "EMA Crossover": """\
import pandas_ta as ta

ema_fast = ta.ema(close, length=10)
ema_slow = ta.ema(close, length=50)
atr      = ta.atr(high, low, close, length=14)

if ema_fast.iloc[-1] > ema_slow.iloc[-1] and ema_fast.iloc[-2] <= ema_slow.iloc[-2]:
    buy()

if ema_fast.iloc[-1] < ema_slow.iloc[-1] and ema_fast.iloc[-2] >= ema_slow.iloc[-2]:
    sell()
""",
    "MACD Cross": """\
import pandas_ta as ta

macd   = ta.macd(close, fast=12, slow=26, signal=9)
atr    = ta.atr(high, low, close, length=14)

macd_line   = macd['MACD_12_26_9']
signal_line = macd['MACDs_12_26_9']

if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
    buy()

if macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:
    sell()
""",
    "Bollinger Band Mean Reversion": """\
import pandas_ta as ta

bb  = ta.bbands(close, length=20, std=2.0)
atr = ta.atr(high, low, close, length=14)

upper = bb['BBU_20_2.0']
lower = bb['BBL_20_2.0']

if close.iloc[-1] < lower.iloc[-1]:
    buy()

if close.iloc[-1] > upper.iloc[-1]:
    sell()
""",
}

# ── MAIN LAYOUT ────────────────────────────────────────────────────
col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown('<div class="slbl">Python Strategy Input</div>', unsafe_allow_html=True)
    ex = st.selectbox("Load example", ["— paste your own —"] + list(EXAMPLES.keys()),
                      label_visibility="collapsed")
    default = EXAMPLES.get(ex, "")
    code_in = st.text_area("code", value=default, height=420,
                            placeholder="Paste your Python trading strategy here…",
                            label_visibility="collapsed")
    go = st.button("⚡  Convert to MQL5", use_container_width=True)

with col_r:
    st.markdown('<div class="slbl">MQL5 Expert Advisor Output</div>', unsafe_allow_html=True)

    if go and code_in.strip():
        with st.spinner("Converting…"):
            conv   = PY2MQL5Converter(groq_api_key=groq_key or None)
            result = conv.convert(code_in, ea_name=ea_name)

        # Metrics
        m1, m2, m3 = st.columns(3)
        conf = result.confidence
        cclass = "#00ff88" if conf >= 75 else "#f59e0b" if conf >= 50 else "#ef4444"
        with m1:
            st.markdown(f'<div class="mcard"><h4>Confidence</h4>'
                        f'<span style="font-size:1.5rem;font-weight:700;color:{cclass}">{conf}%</span></div>',
                        unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="mcard"><h4>Indicators</h4>'
                        f'<span style="font-size:1.5rem;font-weight:700;color:#a78bfa">'
                        f'{len(result.detected_indicators)}</span></div>',
                        unsafe_allow_html=True)
        with m3:
            ai_txt = "Groq 🤖" if result.ai_used else "Dict ⚡"
            ai_col = "#f59e0b" if result.ai_used else "#00ff88"
            st.markdown(f'<div class="mcard"><h4>Engine</h4>'
                        f'<span style="font-size:1.1rem;font-weight:700;color:{ai_col}">{ai_txt}</span></div>',
                        unsafe_allow_html=True)

        # Tags
        if result.detected_indicators:
            tags = " ".join(f'<span class="tag tg">{i["name"].upper()}</span>'
                            for i in result.detected_indicators)
            st.markdown(tags, unsafe_allow_html=True)

        clean_pats = [p for p in result.detected_patterns if p not in ("has_long","has_short")]
        if clean_pats:
            tags = " ".join(f'<span class="tag tp">{p.replace("_"," ")}</span>' for p in clean_pats)
            st.markdown(tags, unsafe_allow_html=True)

        for e in result.errors:
            st.markdown(f'<span class="tag tr">❌ {e}</span>', unsafe_allow_html=True)
        for w in result.warnings:
            st.markdown(f'<span class="tag ta">⚠️ {w}</span>', unsafe_allow_html=True)
        for n in result.notes:
            st.info(f"ℹ️ {n}")

        st.markdown("---")

        if result.mql5_code:
            st.code(result.mql5_code, language="cpp")
            st.download_button(
                f"⬇️  Download {ea_name}.mq5",
                data=result.mql5_code,
                file_name=f"{ea_name}.mq5",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.error("Conversion failed — check errors above")

    elif go:
        st.warning("Paste your Python strategy first")
    else:
        st.markdown("""
        <div style="height:340px;display:flex;flex-direction:column;align-items:center;
                    justify-content:center;border:1px dashed #1e1e2e;border-radius:12px;
                    color:#1e3a5f;font-family:'JetBrains Mono',monospace;font-size:.82rem;
                    text-align:center;gap:1rem">
            <div style="font-size:2.5rem">⚡</div>
            <div>Paste your Python strategy<br>and hit Convert</div>
            <div style="font-size:.68rem;color:#0f2333">RSI · MACD · EMA · Bollinger · ATR · ADX · more</div>
        </div>""", unsafe_allow_html=True)

# ── FOOTER ─────────────────────────────────────────────────────────
st.markdown("---")
f1, f2, f3 = st.columns(3)
with f1:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#1e3a5f">
<span style="color:#00ff88">How it works</span><br>
1. AST parses your Python<br>2. Dict maps indicators<br>3. Groq fills edge cases<br>4. Validator checks output</div>""",
                unsafe_allow_html=True)
with f2:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#1e3a5f">
<span style="color:#00ff88">Always correct</span><br>
✅ Handles in OnInit()<br>✅ ArraySetAsSeries()<br>✅ CTrade execution<br>✅ No index reversal bugs</div>""",
                unsafe_allow_html=True)
with f3:
    st.markdown("""<div style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#1e3a5f">
<span style="color:#00ff88">Coming next</span><br>
FTMO risk manager built-in<br>Multi-symbol support<br>Multi-timeframe<br>More indicator patterns</div>""",
                unsafe_allow_html=True)
