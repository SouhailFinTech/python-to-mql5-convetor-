"""
Core Python → MQL5 converter engine.
Layer 1: AST parsing (deterministic)
Layer 2: Dictionary translation (deterministic)  
Layer 3: Groq API (edge cases only)
Layer 4: Validation
"""

import ast
import re
import os
from typing import Optional
from groq import Groq
from core.indicator_map import (
    INDICATOR_MAP, ARRAY_INDEX_MAP, OPERATOR_MAP,
    OHLCV_MAP, ORDER_PATTERNS, PATTERN_KEYWORDS
)
from core.templates import (
    EA_TEMPLATE, HANDLE_DECL, HANDLE_INIT_MAP,
    HANDLE_VALIDATION_SNIPPET, HANDLE_RELEASE_SNIPPET,
    COPY_BUFFER_SNIPPET, DEFAULT_INPUTS, INPUT_PARAM_MAP
)


class ConversionResult:
    def __init__(self):
        self.mql5_code = ""
        self.confidence = 0
        self.errors = []
        self.warnings = []
        self.detected_indicators = []
        self.detected_patterns = []
        self.ai_used = False
        self.notes = []


class PY2MQL5Converter:
    def __init__(self, groq_api_key: str = None):
        self.groq_key = groq_api_key
        self.groq_client = None
        if groq_api_key:
            self.groq_client = Groq(api_key=groq_api_key)

    # ─────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ─────────────────────────────────────────────
    def convert(self, python_code: str, ea_name: str = "MyEA") -> ConversionResult:
        result = ConversionResult()

        try:
            # 1. Parse Python AST
            tree = self._parse_ast(python_code)
            if tree is None:
                result.errors.append("Python syntax error — fix your code first")
                result.confidence = 0
                return result

            # 2. Detect indicators used
            indicators = self._detect_indicators(python_code)
            result.detected_indicators = indicators

            # 3. Detect strategy patterns
            patterns = self._detect_patterns(python_code)
            result.detected_patterns = patterns

            # 4. Build EA components
            handle_decls   = self._build_handle_declarations(indicators)
            handle_inits   = self._build_handle_inits(indicators)
            handle_vals    = self._build_handle_validations(indicators)
            handle_rels    = self._build_handle_releases(indicators)
            copy_bufs      = self._build_copy_buffers(indicators)
            current_vals   = self._build_current_values(indicators)
            input_params   = self._build_input_params(indicators)
            entry_logic    = self._translate_entry_exit(python_code, patterns, "entry")
            exit_logic     = self._translate_entry_exit(python_code, patterns, "exit")

            # 5. If entry/exit logic is unclear — use Groq
            if self._needs_ai(entry_logic, exit_logic):
                ai_result = self._groq_translate(python_code, indicators, patterns)
                if ai_result:
                    entry_logic = ai_result.get("entry", entry_logic)
                    exit_logic  = ai_result.get("exit", exit_logic)
                    result.ai_used = True
                    result.notes.append("Groq AI assisted with entry/exit logic translation")

            # 6. Assemble final EA
            mql5 = EA_TEMPLATE.format(
                ea_name           = ea_name,
                input_params      = input_params,
                handle_declarations = handle_decls,
                handle_init       = handle_inits,
                handle_validation = handle_vals,
                handle_release    = handle_rels,
                copy_buffers      = copy_bufs,
                current_values    = current_vals,
                entry_logic       = entry_logic,
                exit_logic        = exit_logic,
                risk_pct          = "1.0",
            )

            result.mql5_code = mql5
            result.confidence = self._calculate_confidence(
                indicators, patterns, result.ai_used, result.errors
            )

            # 7. Validate output
            self._validate(result)

        except Exception as e:
            result.errors.append(f"Conversion error: {str(e)}")
            result.confidence = 0

        return result

    # ─────────────────────────────────────────────
    # LAYER 1 — AST PARSING
    # ─────────────────────────────────────────────
    def _parse_ast(self, code: str):
        try:
            return ast.parse(code)
        except SyntaxError as e:
            return None

    # ─────────────────────────────────────────────
    # LAYER 2 — INDICATOR DETECTION
    # ─────────────────────────────────────────────
    def _detect_indicators(self, code: str) -> list:
        detected = []
        code_lower = code.lower()

        for key, info in INDICATOR_MAP.items():
            # Check primary key
            search_terms = [key.split(".")[-1].lower()]
            # Check aliases
            if "aliases" in info:
                search_terms += [a.lower() for a in info["aliases"]]

            for term in search_terms:
                if term in code_lower:
                    # Extract parameter values
                    params = self._extract_params(code, term, info)
                    detected.append({
                        "key": key,
                        "name": key.split(".")[-1].lower(),
                        "info": info,
                        "params": params,
                        "var_name": self._extract_var_name(code, term)
                    })
                    break

        return detected

    def _extract_params(self, code: str, indicator: str, info: dict) -> dict:
        """Try to extract numeric params from Python code."""
        params = {}
        # Look for patterns like ta.rsi(close, 14) or rsi_period = 14
        patterns_to_try = [
            rf'{indicator}\s*\([^,)]+,\s*(\d+)',
            rf'{indicator}_period\s*=\s*(\d+)',
            rf'period\s*=\s*(\d+)',
        ]
        for pat in patterns_to_try:
            m = re.search(pat, code, re.IGNORECASE)
            if m:
                params["period"] = int(m.group(1))
                break
        if "period" not in params:
            params["period"] = 14  # safe default

        # MACD specific
        if "macd" in indicator.lower():
            params["fast"] = 12
            params["slow"] = 26
            params["signal"] = 9
            # Try to find actual values
            m = re.search(r'macd[^(]*\([^,)]+,\s*(\d+)[^,]*,\s*(\d+)[^,]*,\s*(\d+)', code, re.IGNORECASE)
            if m:
                params["fast"]   = int(m.group(1))
                params["slow"]   = int(m.group(2))
                params["signal"] = int(m.group(3))

        # Bollinger Bands
        if "bbands" in indicator.lower() or "bband" in indicator.lower():
            params["deviation"] = 2.0
            m = re.search(r'std\s*=\s*([\d.]+)', code)
            if m:
                params["deviation"] = float(m.group(1))

        return params

    def _extract_var_name(self, code: str, indicator: str) -> str:
        """Try to find variable name assigned to indicator."""
        m = re.search(rf'(\w+)\s*=.*{indicator}', code, re.IGNORECASE)
        if m:
            return m.group(1)
        return indicator.replace(".", "_")

    # ─────────────────────────────────────────────
    # PATTERN DETECTION
    # ─────────────────────────────────────────────
    def _detect_patterns(self, code: str) -> list:
        detected = []
        code_lower = code.lower()
        for pattern, keywords in PATTERN_KEYWORDS.items():
            if any(k in code_lower for k in keywords):
                detected.append(pattern)
        # Detect long/short logic
        if any(w in code_lower for w in ["buy", "long", "enter_long", "go_long"]):
            detected.append("has_long")
        if any(w in code_lower for w in ["sell", "short", "enter_short", "go_short"]):
            detected.append("has_short")
        return list(set(detected))

    # ─────────────────────────────────────────────
    # BUILD MQL5 COMPONENTS
    # ─────────────────────────────────────────────
    def _build_handle_declarations(self, indicators: list) -> str:
        lines = []
        seen = set()
        for ind in indicators:
            name = ind["name"]
            if name not in seen:
                lines.append(f"int handle_{name} = INVALID_HANDLE;")
                seen.add(name)
        return "\n".join(lines) if lines else "// No indicator handles needed"

    def _build_handle_inits(self, indicators: list) -> str:
        lines = []
        seen = set()
        for ind in indicators:
            name  = ind["name"]
            info  = ind["info"]
            p     = ind["params"]
            func  = info.get("mql5_func", "")
            if name in seen or func not in HANDLE_INIT_MAP:
                continue
            seen.add(name)

            template = HANDLE_INIT_MAP[func]
            try:
                if func == "iMA":
                    method = info.get("ma_method", "MODE_SMA")
                    line = template.format(name=name, p1=p.get("period",14), method=method)
                elif func == "iMACD":
                    line = template.format(name=name, p1=p.get("fast",12),
                                           p2=p.get("slow",26), p3=p.get("signal",9))
                elif func == "iBands":
                    line = template.format(name=name, p1=p.get("period",20),
                                           p2=p.get("deviation",2.0))
                elif func == "iStochastic":
                    line = template.format(name=name, p1=p.get("period",14),
                                           p2=p.get("d_period",3), p3=p.get("slowing",3))
                else:
                    line = template.format(name=name, p1=p.get("period",14))
                lines.append(f"   {line}")
            except Exception:
                lines.append(f"   // TODO: manually init handle_{name}")
        return "\n".join(lines) if lines else "   // No handles to initialize"

    def _build_handle_validations(self, indicators: list) -> str:
        lines = []
        seen = set()
        for ind in indicators:
            name = ind["name"]
            if name not in seen and ind["info"].get("handle_required", True):
                lines.append(HANDLE_VALIDATION_SNIPPET.format(name=name))
                seen.add(name)
        return "\n".join(lines) if lines else "   // No handles to validate"

    def _build_handle_releases(self, indicators: list) -> str:
        lines = []
        seen = set()
        for ind in indicators:
            name = ind["name"]
            if name not in seen:
                lines.append(HANDLE_RELEASE_SNIPPET.format(name=name))
                seen.add(name)
        return "\n".join(lines) if lines else "   // No handles to release"

    def _build_copy_buffers(self, indicators: list) -> str:
        lines = []
        seen = set()
        for ind in indicators:
            name = ind["name"]
            info = ind["info"]
            if name in seen:
                continue
            seen.add(name)

            if "buffers" in info:
                # Multiple buffers (MACD, ADX, etc.)
                for buf_name, buf_idx in info["buffers"].items():
                    var = f"{name}_{buf_name}"
                    lines.append(COPY_BUFFER_SNIPPET.format(
                        name=var, buf_index=buf_idx,
                        handle_name=name
                    ).replace(f"handle_{var}", f"handle_{name}"))
            else:
                buf_idx = info.get("buffer", 0)
                lines.append(COPY_BUFFER_SNIPPET.format(
                    name=name, buf_index=buf_idx, handle_name=name
                ))
        return "\n".join(lines) if lines else "   // No buffers to copy"

    def _build_current_values(self, indicators: list) -> str:
        lines = ["   // Current bar values (0=current, 1=previous)"]
        seen = set()
        for ind in indicators:
            name = ind["name"]
            info = ind["info"]
            if name in seen:
                continue
            seen.add(name)

            if "buffers" in info:
                for buf_name in info["buffers"]:
                    var = f"{name}_{buf_name}"
                    lines.append(f"   double {var}_cur  = {var}_buf[0];")
                    lines.append(f"   double {var}_prev = {var}_buf[1];")
            else:
                lines.append(f"   double {name}_cur  = {name}_buf[0];")
                lines.append(f"   double {name}_prev = {name}_buf[1];")
        return "\n".join(lines)

    def _build_input_params(self, indicators: list) -> str:
        lines = []
        seen_indicators = {ind["name"] for ind in indicators}

        for ind in indicators:
            name = ind["name"]
            p    = ind["params"]
            period = p.get("period", 14)
            lines.append(f"input int      {name}_period  = {period};  // {name.upper()} period")
            if "fast" in p:
                lines.append(f"input int      macd_fast    = {p['fast']};   // MACD fast period")
                lines.append(f"input int      macd_slow    = {p['slow']};   // MACD slow period")
                lines.append(f"input int      macd_signal  = {p['signal']}; // MACD signal period")
            if "deviation" in p:
                lines.append(f"input double   bb_deviation = {p['deviation']}; // Bollinger deviation")

        lines.append("input double   risk_pct      = 1.0;  // Risk % per trade")
        lines.append("input double   sl_multiplier = 1.5;  // Stop loss ATR multiplier")
        lines.append("input double   tp_multiplier = 3.0;  // Take profit ATR multiplier")
        return "\n".join(lines) if lines else "input double   risk_pct = 1.0;"

    # ─────────────────────────────────────────────
    # ENTRY / EXIT LOGIC TRANSLATION
    # ─────────────────────────────────────────────
    def _translate_entry_exit(self, code: str, patterns: list, mode: str) -> str:
        """Build entry or exit logic from detected patterns."""

        has_long  = "has_long"  in patterns
        has_short = "has_short" in patterns

        if mode == "entry":
            lines = ["   // --- Entry Logic ---"]

            if "crossover" in patterns:
                lines.append("   // Detected: crossover pattern")
                if has_long:
                    lines.append("   if(!in_position && ma_short_cur > ma_long_cur && ma_short_prev <= ma_long_prev)")
                    lines.append("     {")
                    lines.append("      double sl = CalcSL(true, atr_cur, sl_multiplier);")
                    lines.append("      double tp = CalcTP(true, atr_cur, tp_multiplier);")
                    lines.append("      trade.Buy(NormalizeDouble(risk_pct/100.0, 2), _Symbol, 0, sl, tp, \"MA Cross Buy\");")
                    lines.append("     }")
                if has_short:
                    lines.append("   if(!in_position && ma_short_cur < ma_long_cur && ma_short_prev >= ma_long_prev)")
                    lines.append("     {")
                    lines.append("      double sl = CalcSL(false, atr_cur, sl_multiplier);")
                    lines.append("      double tp = CalcTP(false, atr_cur, tp_multiplier);")
                    lines.append("      trade.Sell(NormalizeDouble(risk_pct/100.0, 2), _Symbol, 0, sl, tp, \"MA Cross Sell\");")
                    lines.append("     }")

            elif "overbought" in patterns or "oversold" in patterns:
                lines.append("   // Detected: RSI overbought/oversold pattern")
                lines.append("   if(!in_position && rsi_cur < 30 && rsi_prev >= 30)")
                lines.append("     {")
                lines.append("      double sl = CalcSL(true, atr_cur, sl_multiplier);")
                lines.append("      double tp = CalcTP(true, atr_cur, tp_multiplier);")
                lines.append("      trade.Buy(NormalizeDouble(risk_pct/100.0, 2), _Symbol, 0, sl, tp, \"RSI Oversold\");")
                lines.append("     }")
                lines.append("   if(!in_position && rsi_cur > 70 && rsi_prev <= 70)")
                lines.append("     {")
                lines.append("      double sl = CalcSL(false, atr_cur, sl_multiplier);")
                lines.append("      double tp = CalcTP(false, atr_cur, tp_multiplier);")
                lines.append("      trade.Sell(NormalizeDouble(risk_pct/100.0, 2), _Symbol, 0, sl, tp, \"RSI Overbought\");")
                lines.append("     }")

            else:
                lines.append("   // TODO: Review entry logic — pattern not fully detected")
                lines.append("   // Original logic requires manual review")
                if has_long:
                    lines.append("   // if(!in_position && <your_buy_condition>)")
                    lines.append("   //   { trade.Buy(lot_size, _Symbol, 0, sl, tp, \"Buy\"); }")
                if has_short:
                    lines.append("   // if(!in_position && <your_sell_condition>)")
                    lines.append("   //   { trade.Sell(lot_size, _Symbol, 0, sl, tp, \"Sell\"); }")

            return "\n".join(lines)

        else:  # exit logic
            lines = ["   // --- Exit Logic ---"]
            lines.append("   if(in_position)")
            lines.append("     {")
            lines.append("      // Position managed by SL/TP set at entry")
            lines.append("      // Add custom exit conditions below if needed")
            lines.append("      // Example: if(rsi_cur > 70) trade.PositionClose(_Symbol);")
            lines.append("     }")
            return "\n".join(lines)

    def _needs_ai(self, entry: str, exit: str) -> bool:
        """Check if AI is needed for ambiguous logic."""
        todo_count = entry.count("TODO") + exit.count("TODO")
        return todo_count > 0 and self.groq_client is not None

    # ─────────────────────────────────────────────
    # LAYER 3 — GROQ AI (edge cases only)
    # ─────────────────────────────────────────────
    def _groq_translate(self, python_code: str, indicators: list, patterns: list) -> Optional[dict]:
        if not self.groq_client:
            return None

        indicator_names = [i["name"] for i in indicators]
        prompt = f"""You are a Python to MQL5 expert converter.

The user has a Python trading strategy. Convert ONLY the entry and exit logic to MQL5.

Python strategy code:
```python
{python_code[:2000]}
```

Detected indicators: {indicator_names}
Detected patterns: {patterns}

MQL5 context (already available in scope):
- Indicator current values named as: {{indicator}}_cur (current bar), {{indicator}}_prev (previous bar)
- For MACD: macd_macd_cur, macd_signal_cur, macd_histogram_cur
- For Bollinger: bbands_upper_cur, bbands_mid_cur, bbands_lower_cur
- trade.Buy(lot, _Symbol, 0, sl, tp, "comment") to buy
- trade.Sell(lot, _Symbol, 0, sl, tp, "comment") to sell
- trade.PositionClose(_Symbol) to close
- in_position (bool) — true if already in a position
- CalcSL(is_buy, atr_cur, multiplier) — returns SL price
- CalcTP(is_buy, atr_cur, multiplier) — returns TP price
- risk_pct input variable available

Rules:
- Array index [0] = current bar (most recent)
- Use && not 'and', || not 'or'
- No Python syntax — pure MQL5 only
- Return JSON with keys "entry" and "exit" containing MQL5 code strings
- No markdown, no explanation, just the JSON"""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000,
            )
            content = response.choices[0].message.content.strip()
            # Parse JSON response
            import json
            # Clean potential markdown
            content = re.sub(r"```json|```", "", content).strip()
            data = json.loads(content)
            return data
        except Exception as e:
            return None

    # ─────────────────────────────────────────────
    # LAYER 4 — VALIDATION
    # ─────────────────────────────────────────────
    def _validate(self, result: ConversionResult):
        code = result.mql5_code

        # Critical checks
        if "iRSI(" in code and "OnInit" not in code:
            result.errors.append("Indicator handle not in OnInit()")

        copy_count = code.count("CopyBuffer")
        series_count = code.count("ArraySetAsSeries")
        if copy_count > 0 and copy_count != series_count:
            result.warnings.append(
                f"CopyBuffer calls ({copy_count}) ≠ ArraySetAsSeries calls ({series_count})"
            )

        if "OrderSend" in code:
            result.warnings.append("Legacy OrderSend() detected — replaced with CTrade")

        if "TODO" in code:
            result.warnings.append(
                "Some logic needs manual review — search for TODO comments in the output"
            )

        if "iloc" in code or "pandas" in code.lower():
            result.errors.append("Python-specific syntax still present — check TODO sections")

    # ─────────────────────────────────────────────
    # CONFIDENCE SCORE
    # ─────────────────────────────────────────────
    def _calculate_confidence(self, indicators, patterns, ai_used, errors) -> int:
        score = 100

        # Deduct for errors
        score -= len(errors) * 20

        # Deduct for TODO items
        score -= len([p for p in patterns if "TODO" in str(p)]) * 10

        # Small deduction if AI was needed
        if ai_used:
            score -= 5

        # Bonus for well-known patterns
        known = ["crossover", "crossunder", "overbought", "oversold"]
        for p in patterns:
            if p in known:
                score += 5

        # Bonus for recognized indicators
        score += min(len(indicators) * 3, 15)

        return max(0, min(100, score))
