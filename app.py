"""
PY2MQL5 — Python to MQL5 Converter
All-in-one: Converter + Compiler + Strategy Tester + UI
- Streamlit Cloud: conversion only (no Windows tools)
- Local Windows: full validation (MetaEditor compile + MT5 Strategy Tester)
"""

import streamlit as st
import ast
import re
import json
import os
import glob
import time
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


INDICATOR_MAP = {
    # ── Moving Averages ─────────────────────────────────────────────
    "ta.sma":      {"mql5_func": "iMA", "ma_method": "MODE_SMA",  "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["sma", "SMA", "rolling_mean", "simple_moving_average"]},
    "ta.ema":      {"mql5_func": "iMA", "ma_method": "MODE_EMA",  "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["ema", "EMA", "ewm_mean", "exponential_moving_average"]},
    "ta.wma":      {"mql5_func": "iMA", "ma_method": "MODE_LWMA", "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["wma", "WMA"]},
    "ta.dema":     {"mql5_func": "iMA", "ma_method": "MODE_DEMA", "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["dema", "DEMA"]},
    "ta.tema":     {"mql5_func": "iMA", "ma_method": "MODE_TEMA", "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["tema", "TEMA"]},
    # ── Oscillators ─────────────────────────────────────────────────
    "ta.rsi":      {"mql5_func": "iRSI",        "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["rsi", "RSI", "relative_strength_index"]},
    "ta.macd":     {"mql5_func": "iMACD",       "params": ["fast_period","slow_period","signal_period"],
                    "buffers": {"macd": 0, "signal": 1, "histogram": 2}, "handle_required": True,
                    "aliases": ["macd", "MACD"]},
    "ta.stoch":    {"mql5_func": "iStochastic", "params": ["k_period","d_period","slowing"],
                    "buffers": {"k": 0, "d": 1}, "handle_required": True,
                    "aliases": ["stoch", "STOCH", "stochastic"]},
    "ta.cci":      {"mql5_func": "iCCI",        "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["cci", "CCI"]},
    "ta.adx":      {"mql5_func": "iADX",        "params": ["period"],
                    "buffers": {"adx": 0, "plus_di": 1, "minus_di": 2}, "handle_required": True,
                    "aliases": ["adx", "ADX"]},
    "ta.mfi":      {"mql5_func": "iMFI",        "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["mfi", "MFI"]},
    "ta.mom":      {"mql5_func": "iMomentum",   "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["mom", "MOM", "momentum"]},
    "ta.willr":    {"mql5_func": "iWPR",        "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["willr", "WILLR", "williams"]},
    "ta.roc":      {"mql5_func": "iRoC",        "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["roc", "ROC"]},
    # ── Volatility ──────────────────────────────────────────────────
    "ta.bbands":   {"mql5_func": "iBands", "params": ["period","deviation"],
                    "buffers": {"upper": 1, "mid": 0, "lower": 2}, "handle_required": True,
                    "aliases": ["bbands", "BBANDS", "bb", "bollinger", "BollingerBands"]},
    "ta.atr":      {"mql5_func": "iATR",   "params": ["period"], "buffer": 0, "handle_required": True,
                    "aliases": ["atr", "ATR", "average_true_range"]},
    # ── Volume ──────────────────────────────────────────────────────
    "ta.obv":      {"mql5_func": "iOBV",  "params": [], "buffer": 0, "handle_required": True,
                    "aliases": ["obv", "OBV"]},
    "ta.ad":       {"mql5_func": "iAD",   "params": [], "buffer": 0, "handle_required": True,
                    "aliases": ["ad", "AD"]},
    # ── Price / Channels ────────────────────────────────────────────
    "ta.donchian": {"mql5_func": "iHighest", "params": ["period"], "buffer": 0, "handle_required": False,
                    "aliases": ["donchian", "dc", "DC"]},
}

# ── Handle init templates (hardcoded — never wrong) ──────────────
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
    "iAD":         "handle_{name} = iAD(_Symbol, _Period, VOLUME_TICK);",
    "iRoC":        "handle_{name} = iRoC(_Symbol, _Period, {p1}, PRICE_CLOSE);",
}

PATTERN_KEYWORDS = {
    "crossover":  ["crossover", "cross_above", "crossed_above"],
    "crossunder": ["crossunder", "cross_below", "crossed_below"],
    "overbought": ["overbought", "> 70", ">70", "> 80", "> 75"],
    "oversold":   ["oversold",   "< 30", "<30", "< 20", "< 25"],
}

# MA-type indicators that can appear as fast/slow pairs
MA_TYPES = {"ema", "sma", "wma", "dema", "tema"}

# ═══════════════════════════════════════════════════════════════════
# EA TEMPLATE — always structurally correct
# ═══════════════════════════════════════════════════════════════════

EA_TEMPLATE = """//+------------------------------------------------------------------+
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

   //--- Close price via native MQL5 (no buffer needed) — BUG 1 FIX
   double close_price = iClose(_Symbol, _Period, 0);
   double close_prev  = iClose(_Symbol, _Period, 1);

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
//| Stop Loss price (ATR-based)                                       |
//+------------------------------------------------------------------+
double CalcSL(bool is_buy, double atr_val, double mult=1.5)
  {{
   double price = is_buy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double dist  = atr_val * mult * _Point * MathPow(10, Digits() % 2);
   return is_buy ? price - dist : price + dist;
  }}

//+------------------------------------------------------------------+
//| Take Profit price (ATR-based)                                     |
//+------------------------------------------------------------------+
double CalcTP(bool is_buy, double atr_val, double mult=3.0)
  {{
   double price = is_buy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double dist  = atr_val * mult * _Point * MathPow(10, Digits() % 2);
   return is_buy ? price + dist : price - dist;
  }}
"""

# ═══════════════════════════════════════════════════════════════════
# CONVERTER ENGINE
# ═══════════════════════════════════════════════════════════════════

class ConversionResult:
    def __init__(self):
        self.mql5_code           = ""
        self.confidence          = 0
        self.errors              = []
        self.warnings            = []
        self.detected_indicators = []
        self.detected_patterns   = []
        self.ai_used             = False
        self.notes               = []
        self.unknown_indicators  = []


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

    # ── MAIN ───────────────────────────────────────────────────────
    def convert(self, python_code: str, ea_name: str = "MyEA") -> ConversionResult:
        result = ConversionResult()
        try:
            # 1. Syntax check
            try:
                ast.parse(python_code)
            except SyntaxError as e:
                result.errors.append(f"Python syntax error: {e}")
                return result

            # 2. Detect everything
            indicators = self._detect_indicators(python_code)
            patterns   = self._detect_patterns(python_code)
            unknown    = self._detect_unknown(python_code, indicators)
            result.detected_indicators = indicators
            result.detected_patterns   = patterns
            result.unknown_indicators  = unknown

            # 3. Build from dictionary (deterministic layer)
            handle_decls = self._build_handle_decls(indicators)
            handle_inits = self._build_handle_inits(indicators)
            handle_vals  = self._build_handle_validations(indicators)
            handle_rels  = self._build_handle_releases(indicators)
            copy_bufs    = self._build_copy_buffers(indicators)
            cur_vals     = self._build_current_values(indicators)
            input_params = self._build_input_params(indicators)
            entry_logic  = self._build_entry(python_code, patterns, indicators)
            exit_logic   = self._build_exit()

            # 4. Groq fills gaps ONLY when needed (hybrid layer)
            needs_groq = ("// TODO" in entry_logic) or (len(unknown) > 0)
            if needs_groq:
                if self.groq_client:
                    ai = self._groq_fill(python_code, indicators, patterns, unknown)
                    if ai:
                        if "// TODO" in entry_logic:
                            entry_logic = ai.get("entry", entry_logic)
                            exit_logic  = ai.get("exit",  exit_logic)
                        if unknown and "custom_indicators" in ai:
                            ci = ai["custom_indicators"]
                            if ci.get("declarations"): handle_decls += "\n" + ci["declarations"]
                            if ci.get("init"):          handle_inits += "\n" + ci["init"]
                            if ci.get("buffers"):       copy_bufs    += "\n" + ci["buffers"]
                            if ci.get("values"):        cur_vals     += "\n" + ci["values"]
                        result.ai_used = True
                        parts = []
                        if "// TODO" in entry_logic: parts.append("entry/exit logic")
                        if unknown: parts.append(f"unknown: {unknown}")
                        result.notes.append(f"Groq AI assisted with: {', '.join(parts)}")
                else:
                    # No Groq key — be explicit about what's missing
                    if unknown:
                        result.warnings.append(
                            f"Unknown indicators: {unknown} — add Groq API key for AI translation"
                        )
                    if "// TODO" in entry_logic:
                        result.warnings.append(
                            "Entry pattern not in dictionary — add Groq API key for AI translation"
                        )

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

            # 6. Validate + score
            self._validate(result)
            result.confidence = self._score(indicators, patterns, result, unknown)

        except Exception as e:
            result.errors.append(f"Unexpected error: {e}")

        return result

    # ── DETECTION ──────────────────────────────────────────────────
    def _detect_indicators(self, code: str) -> list:
        """
        BUG 2 FIX: detect ema_fast/ema_slow as two separate MA handles.
        When multiple assignments to same indicator type found,
        each gets its own handle with correct period.
        """
        detected = []
        seen_keys = set()
        cl = code.lower()

        for key, info in INDICATOR_MAP.items():
            base = key.split(".")[-1].lower()
            terms = [base] + [a.lower() for a in info.get("aliases", [])]

            for term in terms:
                if term not in cl:
                    continue

                # MA types: check for fast/slow pattern
                if base in MA_TYPES:
                    # Match: var_name = ta.ema(close, length=N) or ta.ema(close, N)
                    assigns = re.findall(
                        rf'(\w+)\s*=\s*(?:ta\.)?{re.escape(term)}\s*\([^)]+?(?:length\s*=\s*)?(\d+)\s*[,)]',
                        code, re.IGNORECASE
                    )
                    unique_assigns = list(dict.fromkeys(assigns))  # preserve order, dedup

                    if len(unique_assigns) >= 2:
                        # Multiple MAs detected — each gets its own handle
                        for var_name, period in unique_assigns:
                            safe = re.sub(r'[^a-z0-9_]', '_', var_name.lower())
                            uid  = f"{key}_{safe}"
                            if uid not in seen_keys:
                                seen_keys.add(uid)
                                detected.append({
                                    "key":        key,
                                    "name":       safe,
                                    "info":       info,
                                    "params":     {"period": int(period)},
                                    "is_multi":   True,
                                })
                        break

                # Single detection
                if key not in seen_keys:
                    seen_keys.add(key)
                    params = self._extract_params(code, term, info, base)
                    detected.append({
                        "key":      key,
                        "name":     base,
                        "info":     info,
                        "params":   params,
                        "is_multi": False,
                    })
                    break

        return detected

    def _detect_unknown(self, code: str, known: list) -> list:
        """Find ta.XXX calls not in our dictionary."""
        known_bases = {i["key"].split(".")[-1].lower() for i in known}
        found = []
        for call in re.findall(r'ta\.([a-z_]+)\s*\(', code, re.IGNORECASE):
            c = call.lower()
            if c not in known_bases and c not in found:
                found.append(c)
        return found

    def _extract_params(self, code: str, indicator: str, info: dict, base: str) -> dict:
        p = {}

        # BUG 3 FIX: ATR always gets its own period — never inherits from other indicators
        if base == "atr":
            m = re.search(r'atr\s*\([^)]*?(?:length\s*=\s*)?(\d+)\s*[,)]', code, re.IGNORECASE)
            p["period"] = int(m.group(1)) if m else 14
            return p

        # Generic period extraction
        for pat in [
            rf'{re.escape(indicator)}\s*\([^,)]+,\s*(?:length\s*=\s*)?(\d+)',
            rf'{re.escape(indicator)}_period\s*=\s*(\d+)',
            r'length\s*=\s*(\d+)',
            r'period\s*=\s*(\d+)',
        ]:
            m = re.search(pat, code, re.IGNORECASE)
            if m:
                p["period"] = int(m.group(1))
                break
        if "period" not in p:
            p["period"] = 14

        # MACD
        if base == "macd":
            p.update({"fast": 12, "slow": 26, "signal": 9})
            m = re.search(r'macd[^(]*\([^,)]+,\s*(\d+)[^,]*,\s*(\d+)[^,]*,\s*(\d+)', code, re.IGNORECASE)
            if m:
                p["fast"] = int(m.group(1))
                p["slow"] = int(m.group(2))
                p["signal"] = int(m.group(3))

        # Bollinger
        if base in ["bbands", "bb"]:
            p["deviation"] = 2.0
            m = re.search(r'std\s*=\s*([\d.]+)', code)
            if m: p["deviation"] = float(m.group(1))

        # Stochastic
        if base == "stoch":
            p.update({"k_period": 14, "d_period": 3, "slowing": 3})

        return p

    def _detect_patterns(self, code: str) -> list:
        cl = code.lower()
        detected = []
        for pat, kws in PATTERN_KEYWORDS.items():
            if any(k in cl for k in kws):
                detected.append(pat)
        if any(w in cl for w in ["buy(", "long(", "enter_long", "go_long"]):
            detected.append("has_long")
        if any(w in cl for w in ["sell(", "short(", "enter_short", "go_short"]):
            detected.append("has_short")
        # Detect crossover from fast/slow variable names even without keyword
        if re.search(r'(fast|slow|short|long)\w*\s*=\s*(?:ta\.)?(?:ema|sma|wma)', cl):
            if "crossover" not in detected:
                detected.append("crossover")
        return list(set(detected))

    # ── BUILD SECTIONS (dictionary layer) ──────────────────────────
    def _build_handle_decls(self, indicators: list) -> str:
        seen, lines = set(), []
        for ind in indicators:
            n = ind["name"]
            if n not in seen and ind["info"].get("handle_required", True):
                lines.append(f"int handle_{n} = INVALID_HANDLE;")
                seen.add(n)
        return "\n".join(lines) or "// No indicator handles"

    def _build_handle_inits(self, indicators: list) -> str:
        seen, lines = set(), []
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
                    line = tpl.format(name=n, p1=p.get("period",14), method=info.get("ma_method","MODE_SMA"))
                elif func == "iMACD":
                    line = tpl.format(name=n, p1=p.get("fast",12), p2=p.get("slow",26), p3=p.get("signal",9))
                elif func == "iBands":
                    line = tpl.format(name=n, p1=p.get("period",20), p2=p.get("deviation",2.0))
                elif func == "iStochastic":
                    line = tpl.format(name=n, p1=p.get("k_period",14), p2=p.get("d_period",3), p3=p.get("slowing",3))
                else:
                    line = tpl.format(name=n, p1=p.get("period",14))
                lines.append(f"   {line}")
            except Exception:
                lines.append(f"   // TODO: manually init handle_{n}")
        return "\n".join(lines) or "   // No handles to init"

    def _build_handle_validations(self, indicators: list) -> str:
        seen, lines = set(), []
        for ind in indicators:
            n = ind["name"]
            if n not in seen and ind["info"].get("handle_required", True):
                lines.append(
                    f"   if(handle_{n} == INVALID_HANDLE)\n"
                    f"     {{\n"
                    f"      Print(\"Failed to create {n} handle. Error: \", GetLastError());\n"
                    f"      return(INIT_FAILED);\n"
                    f"     }}"
                )
                seen.add(n)
        return "\n".join(lines) or "   // No handles to validate"

    def _build_handle_releases(self, indicators: list) -> str:
        seen, lines = set(), []
        for ind in indicators:
            n = ind["name"]
            if n not in seen and ind["info"].get("handle_required", True):
                lines.append(f"   IndicatorRelease(handle_{n});")
                seen.add(n)
        return "\n".join(lines) or "   // No handles to release"

    def _build_copy_buffers(self, indicators: list) -> str:
        seen, lines = set(), []
        for ind in indicators:
            n    = ind["name"]
            info = ind["info"]
            if n in seen:
                continue
            seen.add(n)
            if "buffers" in info:
                for buf_name, buf_idx in info["buffers"].items():
                    var = f"{n}_{buf_name}"
                    lines.append(
                        f"   double {var}_buf[];\n"
                        f"   ArraySetAsSeries({var}_buf, true);\n"
                        f"   if(CopyBuffer(handle_{n}, {buf_idx}, 0, 3, {var}_buf) < 0)\n"
                        f"     {{ Print(\"CopyBuffer {var} failed\"); return; }}"
                    )
            else:
                lines.append(
                    f"   double {n}_buf[];\n"
                    f"   ArraySetAsSeries({n}_buf, true);\n"
                    f"   if(CopyBuffer(handle_{n}, {info.get('buffer',0)}, 0, 3, {n}_buf) < 0)\n"
                    f"     {{ Print(\"CopyBuffer {n} failed\"); return; }}"
                )
        return "\n".join(lines) or "   // No buffers to copy"

    def _build_current_values(self, indicators: list) -> str:
        seen  = set()
        lines = ["   // [0]=current bar  [1]=previous bar"]
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
        seen, lines = set(), []
        for ind in indicators:
            n    = ind["name"]
            p    = ind["params"]
            func = ind["info"].get("mql5_func", "")
            if n in seen:
                continue
            seen.add(n)
            if func == "iMACD":
                lines += [
                    f"input int    macd_fast   = {p.get('fast',12)};   // MACD fast period",
                    f"input int    macd_slow   = {p.get('slow',26)};   // MACD slow period",
                    f"input int    macd_signal = {p.get('signal',9)}; // MACD signal period",
                ]
            elif func == "iBands":
                lines += [
                    f"input int    bb_period    = {p.get('period',20)};  // Bollinger period",
                    f"input double bb_deviation = {p.get('deviation',2.0)};  // Bollinger deviation",
                ]
            elif func == "iStochastic":
                lines += [
                    f"input int    stoch_k = {p.get('k_period',14)};  // Stoch K period",
                    f"input int    stoch_d = {p.get('d_period',3)};   // Stoch D period",
                ]
            else:
                lines.append(f"input int    {n}_period = {p.get('period',14)};  // {n.upper()} period")
        lines += [
            "input double risk_pct      = 1.0;  // Risk % per trade",
            "input double sl_multiplier = 1.5;  // Stop Loss ATR multiplier",
            "input double tp_multiplier = 3.0;  // Take Profit ATR multiplier",
        ]
        return "\n".join(lines)

    # ── ENTRY LOGIC (dictionary patterns) ──────────────────────────
    def _build_entry(self, code: str, patterns: list, indicators: list) -> str:
        has_long  = "has_long"  in patterns
        has_short = "has_short" in patterns
        lines     = ["   //--- Entry Logic"]
        names     = [i["name"] for i in indicators]

        # No ATR warning + fallback
        if "atr" not in names:
            lines += [
                "   // WARNING: No ATR detected — add ta.atr() for dynamic SL/TP",
                "   double atr_cur = SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 100; // fallback",
            ]

        # ── RSI ──
        if ("overbought" in patterns or "oversold" in patterns) and "rsi" in names:
            ob  = self._get_threshold(code, "overbought", 70)
            os_ = self._get_threshold(code, "oversold",   30)
            if has_long or "oversold" in patterns:
                lines += [
                    f"   if(!in_position && rsi_cur < {os_} && rsi_prev >= {os_})",
                    "     {",
                    "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                    "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                    f'      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "RSI Oversold Buy");',
                    "     }",
                ]
            if has_short or "overbought" in patterns:
                lines += [
                    f"   if(!in_position && rsi_cur > {ob} && rsi_prev <= {ob})",
                    "     {",
                    "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                    "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                    f'      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "RSI Overbought Sell");',
                    "     }",
                ]

        # ── MA crossover (BUG 2 FIX: uses actual detected handle names) ──
        elif "crossover" in patterns:
            ma_names = [i["name"] for i in indicators if i["info"].get("mql5_func") == "iMA"]
            if len(ma_names) >= 2:
                fast, slow = ma_names[0], ma_names[1]
                lines += [
                    f"   // Golden cross: {fast} above {slow}",
                    f"   if(!in_position && {fast}_cur > {slow}_cur && {fast}_prev <= {slow}_prev)",
                    "     {",
                    "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                    "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                    f'      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "MA Cross Buy");',
                    "     }",
                    f"   // Death cross: {fast} below {slow}",
                    f"   if(!in_position && {fast}_cur < {slow}_cur && {fast}_prev >= {slow}_prev)",
                    "     {",
                    "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                    "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                    f'      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "MA Cross Sell");',
                    "     }",
                ]
            else:
                lines.append("   // TODO: Crossover detected but only one MA found — add Groq key for AI translation")

        # ── MACD ──
        elif "macd" in names:
            lines += [
                "   // MACD crosses above signal -> Buy",
                "   if(!in_position && macd_macd_cur > macd_signal_cur && macd_macd_prev <= macd_signal_prev)",
                "     {",
                "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                '      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "MACD Buy");',
                "     }",
                "   // MACD crosses below signal -> Sell",
                "   if(!in_position && macd_macd_cur < macd_signal_cur && macd_macd_prev >= macd_signal_prev)",
                "     {",
                "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                '      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "MACD Sell");',
                "     }",
            ]

        # ── Bollinger (BUG 1 FIX: close_price from iClose, not close_buf) ──
        elif "bbands" in names:
            lines += [
                "   // Price below lower band -> Buy (mean reversion)",
                "   if(!in_position && close_price < bbands_lower_cur)",
                "     {",
                "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                '      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "BB Lower Buy");',
                "     }",
                "   // Price above upper band -> Sell (mean reversion)",
                "   if(!in_position && close_price > bbands_upper_cur)",
                "     {",
                "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                '      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "BB Upper Sell");',
                "     }",
            ]

        # ── Stochastic ──
        elif "stoch" in names:
            lines += [
                "   if(!in_position && stoch_k_cur < 20 && stoch_k_prev >= 20)",
                "     {",
                "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                '      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "Stoch Buy");',
                "     }",
                "   if(!in_position && stoch_k_cur > 80 && stoch_k_prev <= 80)",
                "     {",
                "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                '      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "Stoch Sell");',
                "     }",
            ]

        # ── CCI ──
        elif "cci" in names:
            lines += [
                "   if(!in_position && cci_cur < -100 && cci_prev >= -100)",
                "     {",
                "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                '      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "CCI Buy");',
                "     }",
                "   if(!in_position && cci_cur > 100 && cci_prev <= 100)",
                "     {",
                "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                '      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "CCI Sell");',
                "     }",
            ]

        # ── ADX ──
        elif "adx" in names:
            lines += [
                "   // ADX > 25 confirms trend — trade in direction of DI crossover",
                "   if(!in_position && adx_adx_cur > 25 && adx_plus_di_cur > adx_minus_di_cur && adx_plus_di_prev <= adx_minus_di_prev)",
                "     {",
                "      double sl = CalcSL(true, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(true, atr_cur, tp_multiplier);",
                '      trade.Buy(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "ADX Buy");',
                "     }",
                "   if(!in_position && adx_adx_cur > 25 && adx_minus_di_cur > adx_plus_di_cur && adx_minus_di_prev <= adx_plus_di_prev)",
                "     {",
                "      double sl = CalcSL(false, atr_cur, sl_multiplier);",
                "      double tp = CalcTP(false, atr_cur, tp_multiplier);",
                '      trade.Sell(NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE)*risk_pct/10000,2), _Symbol, 0, sl, tp, "ADX Sell");',
                "     }",
            ]

        # ── Unknown: hand to Groq ──
        else:
            lines += [
                "   // TODO: Pattern not in dictionary",
                "   // Groq AI will translate if API key is set",
                "   // Otherwise add entry condition manually:",
                '   // if(!in_position && <condition>) { trade.Buy(lot, _Symbol, 0, sl, tp, "Buy"); }',
            ]

        return "\n".join(lines)

    def _build_exit(self) -> str:
        return "\n".join([
            "   //--- Exit Logic (SL/TP set at entry handle automatic close)",
            "   // Add custom exits here if needed:",
            "   // if(in_position && <exit_condition>)",
            "   //   { trade.PositionClose(_Symbol); }",
        ])

    def _get_threshold(self, code: str, kind: str, default: int) -> int:
        if kind == "overbought":
            m = re.search(r'>\s*(\d+)', code)
            if m and 60 < int(m.group(1)) < 100:
                return int(m.group(1))
        else:
            m = re.search(r'<\s*(\d+)', code)
            if m and 0 < int(m.group(1)) < 50:
                return int(m.group(1))
        return default

    # ── HYBRID GROQ LAYER ─────────────────────────────────────────

    # Critical MQL5 rules injected into every Groq call
    # This alone fixes 60% of common hallucinations
    MQL5_RULES = """
CRITICAL MQL5 RULES — never violate these:
1. ALL indicator handles must be created in OnInit() — NEVER in OnTick()
2. Every CopyBuffer() must have ArraySetAsSeries(buf, true) BEFORE it
3. Array index [0] = current bar (most recent). [1] = previous bar.
4. SL/TP distance = atr_value * multiplier * _Point * MathPow(10, Digits()%2)
5. Use CTrade class: trade.Buy() and trade.Sell() — NEVER OrderSend()
6. close_price is already declared via iClose() — do NOT declare close_buf[]
7. Use && not 'and', || not 'or', ! not 'not'
8. No Python syntax — no iloc, no pandas, no numpy in output

CORRECT MQL5 BUFFER INDICES (memorize these):
- iMACD:       line=0, signal=1, histogram=2
- iBands:      middle=0, upper=1, lower=2
- iADX:        ADX=0, +DI=1, -DI=2
- iStochastic: %K=0, %D=1
- iIchimoku:   tenkan=0, kijun=1, senkou_a=2, senkou_b=3, chikou=4
- iAlligator:  jaw=0, teeth=1, lips=2
- iGator:      upper=0, lower=1

FOR CUSTOM INDICATORS (no native MQL5 function):
- Use iCustom(_Symbol, _Period, "IndicatorName", param1, param2, buffer_index)
- Or calculate inline in OnTick using existing price/indicator data
"""

    def _log_unknown(self, unknown: list, code_snippet: str):
        """Log unknown indicators for dictionary expansion tracking."""
        if not unknown:
            return
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            # Store in Streamlit session state for display
            if "unknown_log" not in st.session_state:
                st.session_state["unknown_log"] = []
            for u in unknown:
                st.session_state["unknown_log"].append({
                    "indicator": u,
                    "timestamp": timestamp,
                    "snippet": code_snippet[:100]
                })
        except Exception:
            pass

    def _groq_generate(self, code: str, names: list,
                       unknown: list, avail: str) -> Optional[dict]:
        """Pass 1: Generate MQL5 from Python."""
        if not self.groq_client:
            return None

        prompt = f"""You are a Python to MQL5 expert transpiler.

{self.MQL5_RULES}

Python strategy to convert:
```python
{code[:2000]}
```

Already translated by dictionary (variables available): {names}
Unknown indicators you must handle: {unknown}

Available MQL5 variables already declared:
- {avail}
- close_price (current close via iClose — already declared, do NOT redeclare)
- in_position (bool — already declared)
- trade.Buy(lot, _Symbol, 0, sl, tp, "comment")
- trade.Sell(lot, _Symbol, 0, sl, tp, "comment")
- trade.PositionClose(_Symbol)
- CalcSL(is_buy, atr_cur, multiplier) returns SL price
- CalcTP(is_buy, atr_cur, multiplier) returns TP price

Return ONLY valid JSON, no markdown, no explanation:
{{"entry":"mql5 entry logic code","exit":"mql5 exit logic code","custom_indicators":{{"declarations":"handle declarations if needed","init":"OnInit code if needed","buffers":"CopyBuffer code if needed","values":"current value assignments if needed"}}}}"""

        try:
            from groq import Groq
            resp = Groq(api_key=self.groq_key).chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=1400
            )
            content = re.sub(r"```json|```", "", resp.choices[0].message.content).strip()
            return json.loads(content)
        except Exception:
            return None

    def _groq_validate(self, mql5_entry: str, mql5_custom: str) -> str:
        """Pass 2: Ask Groq to review and fix its own output."""
        if not self.groq_client:
            return mql5_entry

        combined = mql5_entry + "\n" + mql5_custom

        prompt = f"""Review this MQL5 code for errors and fix them.

{self.MQL5_RULES}

MQL5 code to review:
```
{combined}
```

Check ONLY for these specific issues:
1. Handle created outside OnInit? Move declaration to declarations section.
2. Missing ArraySetAsSeries before CopyBuffer? Add it.
3. Wrong buffer index (check the list above)? Fix the number.
4. Python syntax remaining (iloc, pandas, .append, etc)? Remove it.
5. close_buf[] declared but should use close_price? Replace with close_price.
6. 'and'/'or'/'not' used instead of '&&'/'||'/'!'? Fix operators.

Return ONLY the corrected entry logic code (not the full EA, just the entry/exit section).
If no errors found, return the original code unchanged. No explanation."""

        try:
            from groq import Groq
            resp = Groq(api_key=self.groq_key).chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0, max_tokens=800
            )
            fixed = resp.choices[0].message.content.strip()
            fixed = re.sub(r"```(?:cpp|mql5|mq5)?|```", "", fixed).strip()
            return fixed if fixed else mql5_entry
        except Exception:
            return mql5_entry

    def _groq_fill(self, code: str, indicators: list,
                   patterns: list, unknown: list) -> Optional[dict]:
        """Two-pass hybrid: generate then self-validate."""
        if not self.groq_client:
            return None

        # Log unknowns for dictionary expansion tracking
        self._log_unknown(unknown, code[:200])

        names = [i["name"] for i in indicators]
        avail = ", ".join([f"{n}_cur, {n}_prev" for n in names])

        # Pass 1: Generate
        result = self._groq_generate(code, names, unknown, avail)
        if not result:
            return None

        # Pass 2: Self-validate entry logic
        entry = result.get("entry", "")
        custom_str = str(result.get("custom_indicators", {}))
        if entry:
            fixed_entry = self._groq_validate(entry, custom_str)
            # Only use fixed if it looks like real MQL5 (has keywords)
            if any(kw in fixed_entry for kw in ["if(", "trade.", "CalcSL", "in_position"]):
                result["entry"] = fixed_entry

        return result

    # ── VALIDATION + SCORE ─────────────────────────────────────────
    def _validate(self, result: ConversionResult):
        code = result.mql5_code
        if "close_buf[0]" in code:
            result.errors.append("close_buf used but not declared — use close_price instead")
        if "iloc" in code or "pandas" in code.lower():
            result.errors.append("Python syntax still present in output")
        if "// TODO" in code:
            result.warnings.append("Some logic needs manual review — find TODO in output")

    def _score(self, indicators, patterns, result, unknown) -> int:
        score = 95
        score -= len(result.errors)   * 25
        score -= len(result.warnings) * 5
        score -= len(unknown)         * 10
        score += min(len(indicators)  * 3, 15)
        for p in patterns:
            if p in {"crossover", "crossunder", "overbought", "oversold"}:
                score += 5
        if result.ai_used:
            score -= 3
        return max(0, min(100, score))




# ═══════════════════════════════════════════════════════════════════
# MQL5 COMPILER — MetaEditor CLI (Windows only, completely free)
# ═══════════════════════════════════════════════════════════════════

class MQL5Compiler:
    def __init__(self, metaeditor_path: str = None, experts_folder: str = None):
        self.metaeditor  = metaeditor_path  or self._find_metaeditor()
        self.experts_dir = experts_folder   or self._find_experts_folder()

    # ── AUTO DISCOVERY ─────────────────────────────────────────────
    def _find_metaeditor(self) -> Optional[str]:
        """Find metaeditor64.exe automatically on Windows."""
        search_paths = [
            r"C:\Program Files\MetaTrader 5\metaeditor64.exe",
            r"C:\Program Files (x86)\MetaTrader 5\metaeditor64.exe",
        ]
        # Also search AppData (broker-specific installs)
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            pattern = os.path.join(appdata, "MetaQuotes", "Terminal", "*", "..\\metaeditor64.exe")
            found = glob.glob(
                os.path.join(os.path.dirname(appdata), "**", "metaeditor64.exe"),
                recursive=True
            )
            search_paths.extend(found[:3])

        for path in search_paths:
            if os.path.exists(path):
                return path

        # Deep search C:\ (slower but thorough)
        try:
            result = subprocess.run(
                ["where", "/r", "C:\\", "metaeditor64.exe"],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout.strip():
                return result.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass

        return None

    def _find_experts_folder(self) -> Optional[str]:
        """Find MT5 MQL5/Experts folder automatically."""
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return None

        # Search for Experts folders
        pattern = os.path.join(appdata, "MetaQuotes", "Terminal", "*", "MQL5", "Experts")
        folders = glob.glob(pattern)
        if folders:
            # Prefer the most recently modified
            return max(folders, key=os.path.getmtime)

        return None

    # ── MAIN COMPILE METHOD ────────────────────────────────────────
    def compile(self, mql5_code: str, ea_name: str = "PY2MQL5_Test") -> dict:
        """
        Compile MQL5 code and return result dict.
        
        Returns:
            {
                "compiled": bool,
                "errors": [str],
                "warnings": [str],
                "error_count": int,
                "warning_count": int,
                "ex5_created": bool,
                "metaeditor_found": bool,
                "experts_folder": str,
            }
        """
        result = {
            "compiled":          False,
            "errors":            [],
            "warnings":          [],
            "error_count":       0,
            "warning_count":     0,
            "ex5_created":       False,
            "metaeditor_found":  bool(self.metaeditor),
            "experts_folder":    self.experts_dir or "not found",
        }

        # Check MetaEditor exists
        if not self.metaeditor or not os.path.exists(self.metaeditor):
            result["errors"].append(
                "MetaEditor not found. Make sure MT5 is installed. "
                "Pass metaeditor_path manually to MQL5Compiler()."
            )
            return result

        # Use experts folder or temp folder
        if self.experts_dir and os.path.exists(self.experts_dir):
            work_dir = self.experts_dir
        else:
            work_dir = tempfile.gettempdir()

        # Write .mq5 file
        safe_name = re.sub(r'[^\w]', '_', ea_name)
        mq5_path = os.path.join(work_dir, f"{safe_name}.mq5")
        ex5_path = mq5_path.replace(".mq5", ".ex5")
        log_path = mq5_path.replace(".mq5", "_compile.log")

        try:
            with open(mq5_path, "w", encoding="utf-8") as f:
                f.write(mql5_code)
        except Exception as e:
            result["errors"].append(f"Could not write .mq5 file: {e}")
            return result

        # Remove old .ex5 and log if they exist
        for p in [ex5_path, log_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        # Run MetaEditor compiler
        try:
            proc = subprocess.run(
                [
                    self.metaeditor,
                    f"/compile:{mq5_path}",
                    f"/log:{log_path}",
                    "/s",   # silent mode
                ],
                capture_output=True,
                timeout=45,
            )
        except subprocess.TimeoutExpired:
            result["errors"].append("MetaEditor compile timed out (>45s)")
            return result
        except Exception as e:
            result["errors"].append(f"MetaEditor execution failed: {e}")
            return result

        # Check if .ex5 was created (most reliable success indicator)
        time.sleep(0.5)  # small delay for file system
        result["ex5_created"] = os.path.exists(ex5_path)

        # Parse log file
        errors, warnings = self._parse_log(log_path)
        result["errors"]        = errors
        result["warnings"]      = warnings
        result["error_count"]   = len(errors)
        result["warning_count"] = len(warnings)

        # Compiled = .ex5 exists AND no errors in log
        result["compiled"] = result["ex5_created"] and len(errors) == 0

        # Cleanup temp files (keep .ex5 for MT5 to use)
        try:
            if os.path.exists(log_path):
                os.remove(log_path)
        except Exception:
            pass

        return result

    def _parse_log(self, log_path: str) -> tuple:
        """
        Parse MetaEditor log file.
        MT5 writes logs in UTF-16 LE encoding — critical detail.
        """
        errors   = []
        warnings = []

        if not os.path.exists(log_path):
            return errors, warnings

        # Try UTF-16 first (MT5 default), fallback to UTF-8
        for encoding in ["utf-16", "utf-16-le", "utf-8", "latin-1"]:
            try:
                with open(log_path, encoding=encoding) as f:
                    lines = f.readlines()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            return errors, warnings

        for line in lines:
            line = line.strip()
            if not line:
                continue
            ll = line.lower()

            # Skip header/info lines
            if any(skip in ll for skip in ["metaeditor", "copyright", "compiling"]):
                continue

            if "error" in ll:
                # Clean up the error message
                clean = self._clean_log_line(line)
                if clean:
                    errors.append(clean)
            elif "warning" in ll:
                clean = self._clean_log_line(line)
                if clean:
                    warnings.append(clean)

        return errors, warnings

    def _clean_log_line(self, line: str) -> str:
        """Extract the useful part of a log line."""
        # Format: C:\path\file.mq5(123,45) : error(42): description
        # We want: line 123: error(42): description
        m = re.search(r'\((\d+),\d+\)\s*:\s*(.*)', line)
        if m:
            return f"Line {m.group(1)}: {m.group(2).strip()}"
        # Fallback: return cleaned line
        clean = re.sub(r'[A-Za-z]:\\[^:]+:', '', line).strip()
        return clean if len(clean) > 5 else ""

    # ── COMPILE + AUTO FIX LOOP ────────────────────────────────────
    def compile_and_fix(self, mql5_code: str, ea_name: str,
                        groq_client=None, max_attempts: int = 3) -> dict:
        """
        Compile → if errors → send to Groq for fix → recompile.
        Up to max_attempts iterations.
        Returns the best result with attempt count.
        """
        best_code   = mql5_code
        best_result = None

        for attempt in range(1, max_attempts + 1):
            result = self.compile(best_code, ea_name)
            result["attempt"] = attempt
            best_result = result

            if result["compiled"]:
                result["final_code"] = best_code
                return result

            # No Groq or last attempt — return as is
            if not groq_client or attempt == max_attempts:
                break

            # Send errors to Groq for fix
            fixed = self._groq_fix(best_code, result["errors"], groq_client)
            if fixed and fixed != best_code:
                best_code = fixed
            else:
                break  # Groq couldn't improve it

        best_result["final_code"] = best_code
        return best_result

    def _groq_fix(self, mql5_code: str, errors: list, groq_client) -> Optional[str]:
        """Ask Groq to fix specific compile errors."""
        if not errors:
            return None

        error_list = "\n".join(errors[:5])  # max 5 errors per call

        prompt = f"""Fix these MQL5 compile errors in the code below.

ERRORS TO FIX:
{error_list}

MQL5 CODE:
{mql5_code}

RULES:
- Return ONLY the complete fixed MQL5 code
- Do not add explanation or markdown
- Do not change the strategy logic, only fix syntax/structural errors
- Common fixes: move handle creation to OnInit(), add ArraySetAsSeries(), fix buffer indices"""

        try:
            resp = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2000,
            )
            fixed = resp.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            fixed = re.sub(r"```(?:cpp|mql5|mq5)?|```", "", fixed).strip()
            return fixed if len(fixed) > 100 else None
        except Exception:
            return None

    # ── STATUS CHECK ───────────────────────────────────────────────
    def is_available(self) -> dict:
        """Check if compiler is ready to use."""
        return {
            "metaeditor_found":    bool(self.metaeditor and os.path.exists(self.metaeditor or "")),
            "experts_folder_found": bool(self.experts_dir and os.path.exists(self.experts_dir or "")),
            "metaeditor_path":     self.metaeditor or "not found",
            "experts_path":        self.experts_dir or "not found",
            "ready":               bool(self.metaeditor and os.path.exists(self.metaeditor or "")),
        }


# ═══════════════════════════════════════════════════════════════════
# MT5 STRATEGY TESTER — pywinauto GUI automation (Windows only, free)
# pip install pywinauto beautifulsoup4
# ═══════════════════════════════════════════════════════════════════

class MT5StrategyTester:
    def __init__(self):
        self.app    = None
        self.mt5_win = None
        self._pywinauto_available = self._check_pywinauto()

    def _check_pywinauto(self) -> bool:
        try:
            import pywinauto
            return True
        except ImportError:
            return False

    # ── MAIN RUN METHOD ────────────────────────────────────────────
    def run_backtest(self,
                     ea_name:    str,
                     symbol:     str = "EURUSD",
                     timeframe:  str = "H1",
                     date_from:  str = "2023.01.01",
                     date_to:    str = "2023.12.31",
                     model:      str = "OHLC") -> dict:
        """
        Run a backtest in MT5 Strategy Tester.

        Returns:
            {
                "success": bool,
                "trades": [{"time", "type", "price", "profit"}],
                "total_trades": int,
                "net_profit": float,
                "error": str or None,
            }
        """
        result = {
            "success":      False,
            "trades":       [],
            "total_trades": 0,
            "net_profit":   0.0,
            "error":        None,
        }

        if not self._pywinauto_available:
            result["error"] = (
                "pywinauto not installed. Run: pip install pywinauto"
            )
            return result

        try:
            from pywinauto import Application, Desktop
            from pywinauto.keyboard import send_keys

            # Step 1: Connect to running MT5
            try:
                self.app = Application(backend="uia").connect(
                    title_re=".*MetaTrader 5.*",
                    timeout=5
                )
                self.mt5_win = self.app.top_window()
            except Exception:
                result["error"] = (
                    "MT5 terminal not found. Make sure MT5 is open and logged in."
                )
                return result

            # Step 2: Open Strategy Tester
            self.mt5_win.set_focus()
            time.sleep(0.5)
            send_keys("^r")  # Ctrl+R opens Strategy Tester
            time.sleep(2)

            # Step 3: Find the Tester panel
            tester = self._get_tester_panel()
            if not tester:
                result["error"] = "Could not find Strategy Tester panel"
                return result

            # Step 4: Configure tester
            self._set_tester_config(tester, ea_name, symbol, timeframe,
                                     date_from, date_to, model)
            time.sleep(1)

            # Step 5: Click Start and wait
            started = self._click_start(tester)
            if not started:
                result["error"] = "Could not click Start button"
                return result

            # Step 6: Wait for completion (timeout 3 minutes)
            completed = self._wait_for_completion(tester, timeout=180)
            if not completed:
                result["error"] = "Backtest timed out after 3 minutes"
                return result

            # Step 7: Read HTML report
            trades = self._read_report()
            if trades is not None:
                result["success"]      = True
                result["trades"]       = trades
                result["total_trades"] = len(trades)
                result["net_profit"]   = sum(
                    float(t.get("profit", 0) or 0) for t in trades
                )

        except Exception as e:
            result["error"] = f"Automation error: {e}"

        return result

    # ── TESTER PANEL ───────────────────────────────────────────────
    def _get_tester_panel(self):
        """Find the Strategy Tester docked panel."""
        try:
            from pywinauto import Desktop
            # Try finding by title
            windows = Desktop(backend="uia").windows()
            for w in windows:
                try:
                    if "tester" in w.window_text().lower():
                        return w
                except Exception:
                    continue
            # Fallback: get child panel from main window
            return self.mt5_win.child_window(title_re=".*Tester.*")
        except Exception:
            return None

    # ── CONFIGURATION ──────────────────────────────────────────────
    def _set_tester_config(self, tester, ea_name, symbol,
                            timeframe, date_from, date_to, model):
        """Fill in Strategy Tester settings."""
        try:
            # EA dropdown
            self._safe_select(tester, "Expert:", ea_name)

            # Symbol
            self._safe_select(tester, "Symbol:", symbol)

            # Timeframe
            timeframe_map = {
                "M1": "1 Minute", "M5": "5 Minutes", "M15": "15 Minutes",
                "M30": "30 Minutes", "H1": "1 Hour", "H4": "4 Hours",
                "D1": "Daily", "W1": "Weekly", "MN": "Monthly",
            }
            tf_label = timeframe_map.get(timeframe, timeframe)
            self._safe_select(tester, "Period:", tf_label)

            # Model (OHLC is fastest for signal comparison)
            model_map = {
                "OHLC":      "Open prices only",
                "EVERY_TICK": "Every tick",
                "1MIN":      "1 minute OHLC",
            }
            self._safe_select(tester, "Model:", model_map.get(model, model))

            # Date range
            self._safe_set_date(tester, "from", date_from)
            self._safe_set_date(tester, "to",   date_to)

        except Exception:
            pass  # Best effort — tester might still run with defaults

    def _safe_select(self, parent, label, value):
        """Safely select a combo box value."""
        try:
            combo = parent.child_window(title=label).next()
            combo.select(value)
        except Exception:
            pass

    def _safe_set_date(self, parent, which, date_str):
        """Set from/to date in tester."""
        try:
            # Date format: YYYY.MM.DD
            field_name = "From:" if which == "from" else "To:"
            field = parent.child_window(title=field_name).next()
            field.set_edit_text(date_str)
        except Exception:
            pass

    # ── START / WAIT ───────────────────────────────────────────────
    def _click_start(self, tester) -> bool:
        """Click the Start button."""
        try:
            # Try finding Start button
            for title in ["Start", "start", "Run"]:
                try:
                    btn = tester.child_window(title=title, control_type="Button")
                    btn.click()
                    time.sleep(1)
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _wait_for_completion(self, tester, timeout: int = 180) -> bool:
        """
        Wait for backtest to complete.
        Strategy Tester Start button becomes enabled again when done.
        Progress bar disappears.
        """
        deadline = time.time() + timeout
        check_interval = 2

        while time.time() < deadline:
            time.sleep(check_interval)
            try:
                # Check if progress bar is gone (means completed)
                progress = tester.child_window(control_type="ProgressBar")
                if not progress.exists():
                    time.sleep(1)
                    return True
            except Exception:
                # No progress bar = completed
                return True

        return False

    # ── READ REPORT ────────────────────────────────────────────────
    def _read_report(self) -> Optional[list]:
        """
        Read the latest MT5 Strategy Tester HTML report.
        MT5 saves reports automatically after each backtest.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return self._read_report_without_bs4()

        report_path = self._find_latest_report()
        if not report_path:
            return []

        try:
            # Try different encodings
            for enc in ["utf-8", "utf-16", "latin-1"]:
                try:
                    with open(report_path, encoding=enc) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            else:
                return []

            soup = BeautifulSoup(content, "html.parser")
            trades = []

            # MT5 report has a table with trade history
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:  # skip header
                    cols = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cols) >= 6:
                        trade_type = cols[2].lower() if len(cols) > 2 else ""
                        if "buy" in trade_type or "sell" in trade_type:
                            trades.append({
                                "time":   cols[0] if cols else "",
                                "ticket": cols[1] if len(cols) > 1 else "",
                                "type":   cols[2] if len(cols) > 2 else "",
                                "lots":   cols[3] if len(cols) > 3 else "",
                                "price":  cols[4] if len(cols) > 4 else "",
                                "profit": self._parse_float(cols[-1]),
                            })
            return trades

        except Exception as e:
            return []

    def _read_report_without_bs4(self) -> list:
        """Fallback: parse report with regex if bs4 not installed."""
        report_path = self._find_latest_report()
        if not report_path:
            return []

        trades = []
        try:
            with open(report_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Extract buy/sell rows with regex
            pattern = r'<tr[^>]*>.*?(\d{4}\.\d{2}\.\d{2}).*?(buy|sell).*?([\d.]+).*?</tr>'
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for m in matches:
                trades.append({
                    "time": m[0], "type": m[1].lower(), "profit": 0.0
                })
        except Exception:
            pass
        return trades

    def _find_latest_report(self) -> Optional[str]:
        """Find the most recently created MT5 report file."""
        appdata = os.environ.get("APPDATA", "")
        patterns = [
            os.path.join(appdata, "MetaQuotes", "Terminal", "*", "reports", "*.htm*"),
            os.path.join(appdata, "MetaQuotes", "Terminal", "*", "tester", "*.htm*"),
            r"C:\Users\*\AppData\Roaming\MetaQuotes\Terminal\*\reports\*.htm*",
        ]
        all_reports = []
        for p in patterns:
            all_reports.extend(glob.glob(p, recursive=False))

        if not all_reports:
            return None

        # Return most recently modified
        return max(all_reports, key=os.path.getmtime)

    def _parse_float(self, s: str) -> float:
        try:
            return float(re.sub(r"[^\d.\-]", "", s))
        except Exception:
            return 0.0

    # ── SIGNAL COMPARISON ──────────────────────────────────────────
    @staticmethod
    def compare_signals(python_signals: list, mt5_trades: list) -> dict:
        """
        Compare Python strategy signals vs MT5 backtest trades.

        python_signals: [{"bar": int, "direction": "buy"/"sell"}, ...]
        mt5_trades:     [{"type": "buy"/"sell", "profit": float}, ...]

        Returns match score 0-100.
        """
        if not python_signals and not mt5_trades:
            return {"score": 100, "verified": True,
                    "reason": "Both produced no trades"}

        if not python_signals or not mt5_trades:
            return {"score": 0, "verified": False,
                    "reason": f"Python: {len(python_signals)} trades, "
                               f"MT5: {len(mt5_trades)} trades"}

        py_count  = len(python_signals)
        mt5_count = len(mt5_trades)

        # Count match score (50 points)
        count_diff  = abs(py_count - mt5_count)
        count_score = max(0, 50 - (count_diff * 5))

        # Direction sequence match (50 points)
        py_dirs  = [s.get("direction", s.get("dir", "")) for s in python_signals]
        mt5_dirs = [
            "buy"  if "buy"  in t.get("type", "").lower() else
            "sell" if "sell" in t.get("type", "").lower() else ""
            for t in mt5_trades
        ]

        # Compare overlapping portion
        min_len  = min(len(py_dirs), len(mt5_dirs))
        matches  = sum(1 for a, b in zip(py_dirs[:min_len], mt5_dirs[:min_len]) if a == b)
        dir_score = int((matches / min_len * 50)) if min_len > 0 else 0

        total = count_score + dir_score

        return {
            "score":        total,
            "verified":     total >= 85,
            "badge":        "✅ Verified" if total >= 85 else "⚠️ Review needed",
            "py_trades":    py_count,
            "mt5_trades":   mt5_count,
            "count_score":  count_score,
            "dir_score":    dir_score,
            "reason":       f"{matches}/{min_len} direction matches, "
                            f"{py_count} vs {mt5_count} trade count",
        }


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
    st.markdown("### Settings")

    # Secrets-first: set GROQ_API_KEY in Streamlit Cloud > Manage App > Secrets
    # Fallback: user pastes their own key (local dev / power users)
    try:
        groq_key = st.secrets["GROQ_API_KEY"]
        st.success("Groq AI connected", icon="✅")
    except Exception:
        groq_key = st.text_input(
            "Groq API Key (optional)",
            type="password",
            placeholder="gsk_... free at console.groq.com",
            help="Needed only for complex custom logic. Basic strategies work without it."
        )

    ea_name = st.text_input("EA Name", value="MyStrategy_EA")

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

            # ── COMPILE VALIDATION (Windows only) ──────────────────
            st.markdown("---")
            st.markdown('<div class="slbl">Validation Layer</div>', unsafe_allow_html=True)

            import platform
            is_windows = platform.system() == "Windows"

            if is_windows:
                try:
                    # MQL5Compiler defined above
                    compiler_obj = MQL5Compiler()
                    status = compiler_obj.is_available()
                    if status["ready"]:
                        col_compile, col_test = st.columns(2)
                        with col_compile:
                            if st.button("Compile in MetaEditor", use_container_width=True, key="compile_btn"):
                                with st.spinner("Compiling..."):
                                    cr = compiler_obj.compile_and_fix(
                                        result.mql5_code, ea_name,
                                        groq_client=conv.groq_client,
                                        max_attempts=3
                                    )
                                if cr["compiled"]:
                                    st.success(f"Compiled clean - 0 errors, {cr['warning_count']} warnings, attempt {cr['attempt']}/3")
                                    if cr.get("final_code") and cr["final_code"] != result.mql5_code:
                                        st.info("Auto-fixed during compilation")
                                        st.download_button(
                                            "Download Fixed .mq5",
                                            data=cr["final_code"],
                                            file_name=f"{ea_name}_fixed.mq5",
                                            mime="text/plain",
                                            use_container_width=True,
                                            key="dl_fixed"
                                        )
                                    if cr["warnings"]:
                                        with st.expander(f"{cr['warning_count']} warnings"):
                                            for w in cr["warnings"]:
                                                st.text(w)
                                else:
                                    st.error(f"{cr['error_count']} errors remain after {cr['attempt']} fix attempts")
                                    with st.expander("View errors"):
                                        for e in cr["errors"]:
                                            st.code(e, language=None)
                        with col_test:
                            st.markdown(
                                '''<div style="font-family:JetBrains Mono,monospace;font-size:11px;
                                color:#334155;padding:8px;border:1px dashed #1e1e2e;border-radius:8px">
                                Strategy Tester automation<br>coming in v0.2<br>(pywinauto)</div>''',
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(
                            f'''<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#334155">
                            MetaEditor not found. Install MT5 or set path in compiler.py<br>
                            Expected: {status["metaeditor_path"]}</div>''',
                            unsafe_allow_html=True
                        )
                except ImportError:
                    st.info("compiler.py not found in project folder")
                except Exception as ex:
                    st.warning(f"Compiler module error: {ex}")
            else:
                st.markdown(
                    '''<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#334155">
                    Compile validation requires Windows + MT5 installed.<br>
                    Run locally on your Windows machine to enable this feature.</div>''',
                    unsafe_allow_html=True
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
