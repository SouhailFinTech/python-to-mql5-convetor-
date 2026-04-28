import streamlit as st
import os
import sys

# Fix path for both local and Streamlit Cloud
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.converter import PY2MQL5Converter

# ─── PAGE CONFIG ───────────────────────────────────────────────────
st.set_page_config(
    page_title="PY2MQL5 — Python to MQL5 Converter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;700;800&display=swap');

:root {
    --bg:       #0a0a0f;
    --surface:  #111118;
    --border:   #1e1e2e;
    --accent:   #00ff88;
    --accent2:  #7c3aed;
    --warn:     #f59e0b;
    --error:    #ef4444;
    --text:     #e2e8f0;
    --muted:    #64748b;
}

html, body, .stApp {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Syne', sans-serif;
}

/* Header */
.hero {
    text-align: center;
    padding: 2.5rem 0 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.hero h1 {
    font-size: 3rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #00ff88, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.hero p {
    color: var(--muted);
    font-size: 1rem;
    margin-top: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Confidence badge */
.conf-high   { color: #00ff88; font-weight: 700; font-size: 1.4rem; }
.conf-medium { color: #f59e0b; font-weight: 700; font-size: 1.4rem; }
.conf-low    { color: #ef4444; font-weight: 700; font-size: 1.4rem; }

/* Tags */
.tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    margin: 2px;
    font-family: 'JetBrains Mono', monospace;
}
.tag-green  { background: #052e1c; color: #00ff88; border: 1px solid #00ff8844; }
.tag-purple { background: #1e0a3c; color: #a78bfa; border: 1px solid #7c3aed44; }
.tag-amber  { background: #2d1a00; color: #fbbf24; border: 1px solid #f59e0b44; }
.tag-red    { background: #2d0a0a; color: #f87171; border: 1px solid #ef444444; }

/* Cards */
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.metric-card h4 {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin: 0 0 0.5rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Section labels */
.section-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 0.5rem;
    padding-left: 2px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #00ff88, #00cc6a) !important;
    color: #0a0a0f !important;
    font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 2rem !important;
    font-size: 0.95rem !important;
    width: 100%;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* Text areas and inputs */
.stTextArea textarea, .stTextInput input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
    border-radius: 8px !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* Alert boxes */
.stAlert { border-radius: 8px !important; }

/* Expander */
.streamlit-expanderHeader {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* Code blocks */
.stCodeBlock {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* Download button */
.stDownloadButton > button {
    background: var(--surface) !important;
    color: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>⚡ PY2MQL5</h1>
    <p>Python strategy → MQL5 Expert Advisor · No martingale · No BS</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    groq_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="gsk_...",
        help="Free at console.groq.com — used for complex logic only"
    )

    st.markdown("---")
    st.markdown("### 📋 EA Settings")
    ea_name = st.text_input("EA Name", value="MyStrategy_EA")

    st.markdown("---")
    st.markdown("### 💡 Supported Indicators")
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#64748b;line-height:2">
    ✅ ta.rsi → iRSI<br>
    ✅ ta.ema / ta.sma → iMA<br>
    ✅ ta.macd → iMACD<br>
    ✅ ta.bbands → iBands<br>
    ✅ ta.atr → iATR<br>
    ✅ ta.stoch → iStochastic<br>
    ✅ ta.adx → iADX<br>
    ✅ ta.cci → iCCI<br>
    ✅ ta.obv → iOBV<br>
    ✅ ta.wma / ta.dema → iMA<br>
    🤖 Custom logic → Groq AI
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem;color:#64748b;font-family:'JetBrains Mono',monospace">
    MVP v0.1 · Built by a quant<br>
    for quants who hate MQL5
    </div>
    """, unsafe_allow_html=True)

# ─── EXAMPLE STRATEGIES ────────────────────────────────────────────
EXAMPLES = {
    "RSI Overbought/Oversold": """\
import pandas_ta as ta

# Calculate RSI
rsi = ta.rsi(close, length=14)

# Entry logic
if rsi.iloc[-1] < 30:  # oversold — buy
    buy()

if rsi.iloc[-1] > 70:  # overbought — sell
    sell()

# Exit logic
if rsi.iloc[-1] > 50 and in_long:
    close_position()
""",

    "MA Crossover": """\
import pandas_ta as ta

# Two moving averages
ma_fast = ta.ema(close, length=10)
ma_slow = ta.ema(close, length=50)

# Golden cross — buy
if ma_fast.iloc[-1] > ma_slow.iloc[-1] and ma_fast.iloc[-2] <= ma_slow.iloc[-2]:
    buy()

# Death cross — sell
if ma_fast.iloc[-1] < ma_slow.iloc[-1] and ma_fast.iloc[-2] >= ma_slow.iloc[-2]:
    sell()
""",

    "MACD Signal Cross": """\
import pandas_ta as ta

# MACD
macd_result = ta.macd(close, fast=12, slow=26, signal=9)
macd_line   = macd_result['MACD_12_26_9']
signal_line = macd_result['MACDs_12_26_9']

# Buy when MACD crosses above signal
if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
    buy()

# Sell when MACD crosses below signal
if macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:
    sell()
""",

    "Bollinger Band Breakout": """\
import pandas_ta as ta

# Bollinger Bands
bb = ta.bbands(close, length=20, std=2.0)
upper = bb['BBU_20_2.0']
lower = bb['BBL_20_2.0']

# ATR for stops
atr = ta.atr(high, low, close, length=14)

# Price touches lower band — buy
if close.iloc[-1] < lower.iloc[-1]:
    buy()

# Price touches upper band — sell
if close.iloc[-1] > upper.iloc[-1]:
    sell()
""",
}

# ─── MAIN LAYOUT ───────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-label">Python Strategy Input</div>', unsafe_allow_html=True)

    # Example loader
    example_choice = st.selectbox(
        "Load example strategy",
        ["— paste your own —"] + list(EXAMPLES.keys()),
        label_visibility="collapsed"
    )

    default_code = EXAMPLES.get(example_choice, "")
    python_code = st.text_area(
        "python_input",
        value=default_code,
        height=400,
        placeholder="Paste your Python trading strategy here...\n\nSupports: pandas-ta indicators, manual calculations, buy/sell signals",
        label_visibility="collapsed"
    )

    convert_btn = st.button("⚡ Convert to MQL5", use_container_width=True)

with col_right:
    st.markdown('<div class="section-label">MQL5 Expert Advisor Output</div>', unsafe_allow_html=True)

    if convert_btn and python_code.strip():
        with st.spinner("Converting..."):
            converter = PY2MQL5Converter(groq_api_key=groq_key if groq_key else None)
            result = converter.convert(python_code, ea_name=ea_name)

        # ─ Metrics row ─
        m1, m2, m3 = st.columns(3)

        with m1:
            conf = result.confidence
            cls  = "conf-high" if conf >= 75 else "conf-medium" if conf >= 50 else "conf-low"
            st.markdown(f"""
            <div class="metric-card">
                <h4>Confidence</h4>
                <span class="{cls}">{conf}%</span>
            </div>""", unsafe_allow_html=True)

        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Indicators</h4>
                <span style="font-size:1.4rem;font-weight:700;color:#a78bfa">
                    {len(result.detected_indicators)}
                </span>
            </div>""", unsafe_allow_html=True)

        with m3:
            ai_txt = "Yes 🤖" if result.ai_used else "No ⚡"
            ai_col = "#f59e0b" if result.ai_used else "#00ff88"
            st.markdown(f"""
            <div class="metric-card">
                <h4>AI Assist</h4>
                <span style="font-size:1.1rem;font-weight:700;color:{ai_col}">
                    {ai_txt}
                </span>
            </div>""", unsafe_allow_html=True)

        # ─ Detected indicators tags ─
        if result.detected_indicators:
            tags_html = " ".join(
                f'<span class="tag tag-green">{i["name"].upper()}</span>'
                for i in result.detected_indicators
            )
            st.markdown(f'<div style="margin-bottom:0.8rem">{tags_html}</div>',
                        unsafe_allow_html=True)

        # ─ Patterns detected ─
        if result.detected_patterns:
            clean = [p for p in result.detected_patterns
                     if p not in ("has_long", "has_short")]
            if clean:
                tags_html = " ".join(
                    f'<span class="tag tag-purple">{p.replace("_"," ")}</span>'
                    for p in clean
                )
                st.markdown(f'<div style="margin-bottom:1rem">{tags_html}</div>',
                            unsafe_allow_html=True)

        # ─ Errors ─
        for err in result.errors:
            st.markdown(f'<span class="tag tag-red">❌ {err}</span>',
                        unsafe_allow_html=True)

        # ─ Warnings ─
        for warn in result.warnings:
            st.markdown(f'<span class="tag tag-amber">⚠️ {warn}</span>',
                        unsafe_allow_html=True)

        # ─ Notes ─
        for note in result.notes:
            st.info(f"ℹ️ {note}")

        st.markdown("---")

        # ─ MQL5 output ─
        if result.mql5_code:
            st.code(result.mql5_code, language="cpp")
            st.download_button(
                label=f"⬇️ Download {ea_name}.mq5",
                data=result.mql5_code,
                file_name=f"{ea_name}.mq5",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.error("Conversion failed — check errors above")

    elif convert_btn and not python_code.strip():
        st.warning("Paste your Python strategy first")
    else:
        # Empty state
        st.markdown("""
        <div style="height:300px;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;
                    border:1px dashed #1e1e2e;border-radius:12px;
                    color:#334155;font-family:'JetBrains Mono',monospace;
                    font-size:0.85rem;text-align:center;gap:1rem">
            <div style="font-size:2.5rem">⚡</div>
            <div>Paste your Python strategy<br>and click Convert</div>
            <div style="font-size:0.7rem;color:#1e3a5f">
                RSI · MACD · MA · Bollinger · ATR · ADX · more
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── BOTTOM INFO ───────────────────────────────────────────────────
st.markdown("---")
bcol1, bcol2, bcol3 = st.columns(3)
with bcol1:
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#334155">
    <strong style="color:#00ff88">How it works</strong><br>
    1. AST parser reads your Python<br>
    2. Dictionary maps indicators<br>
    3. Groq AI fills edge cases<br>
    4. Validator checks output
    </div>""", unsafe_allow_html=True)
with bcol2:
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#334155">
    <strong style="color:#00ff88">Always correct</strong><br>
    ✅ Handles in OnInit()<br>
    ✅ ArraySetAsSeries()<br>
    ✅ No index reversal bugs<br>
    ✅ CTrade order execution
    </div>""", unsafe_allow_html=True)
with bcol3:
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#334155">
    <strong style="color:#00ff88">MVP v0.1</strong><br>
    More indicators coming<br>
    Multi-timeframe support soon<br>
    Risk manager built-in<br>
    FTMO rules module next
    </div>""", unsafe_allow_html=True)
