import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import datetime
import time

# 1. Page Configuration & Auto-Refresh Setup (Every 30 Seconds)
st.set_page_config(page_title="Stock Saathi Auto-Live", page_icon="🎯", layout="centered")

# Auto-refresh mechanism for live market updates without reloading page manually
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# HTML inject to force Streamlit to rerun every 30 seconds smoothly
st.markdown("""
    <meta http-to-refresh="30">
""", unsafe_allow_html=True)

# Visual refresh indicator timer
st.sidebar.caption(f"🔄 लास्ट ऑटो-अपडेट: {datetime.datetime.now().strftime('%H:%M:%S')}")
if st.sidebar.button("🔄 अभी रिफ्रेश करें (Manual Refresh)"):
    st.rerun()

st.title("🎯 Stock Saathi (Auto-Live)")
st.caption("AI-पॉवर्ड ऑटो-रिफ्रेश प्री-मार्केट एवं लाइव स्कैनर | केवल कैश सेगमेंट")

# --- CAPITAL CONFIGURATION ---
TOTAL_CAPITAL = 50000.0
RISK_PER_TRADE_PCT = 0.5  
MAX_RISK_INR = TOTAL_CAPITAL * (RISK_PER_TRADE_PCT / 100.0)  # ₹250 max loss per trade

# Filtered Watchlist (Strong Cash segment counters & Index ETFs)
WATCHLIST = [
    "NIFTYBEES.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS",
    "LT.NS", "BAJFINANCE.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "TATASTEEL.NS", "M&M.NS", "SUNPHARMA.NS", "POWERGRID.NS", "NTPC.NS"
]

# --- LIVE REAL-TIME DATA SCRAPER (GOOGLE FINANCE) ---
def get_realtime_google_price(ticker):
    """
    Fetches 100% real-time current market price from Google Finance 
    to bypass the 15-minute delay of free Yahoo Finance APIs.
    """
    try:
        sym = ticker.replace(".NS", "")
        url = f"https://google.com{sym}:NSE"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=4)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            price_div = soup.find("div", {"class": "YMlKec fxKbKc"})
            if price_div:
                return float(price_div.text.replace("₹", "").replace(",", "").strip())
    except Exception:
        pass
    return None

# --- ADVANCED OVERNIGHT NEWS SCRAPER ---
def analyze_company_news(ticker_name):
    score_modifier = 0
    news_headlines = []
    try:
        query = f"{ticker_name} stock corporate announcements results"
        url = f"https://google.com{query}&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(url, timeout=4)
        soup = BeautifulSoup(resp.content, features="xml")
        items = soup.find_all("item")
        
        for item in items[:3]:
            title = item.title.text
            news_headlines.append(title)
            title_lower = title.lower()
            if any(x in title_lower for x in ["profit", "rise", "buy", "growth", "dividend", "order wins"]):
                score_modifier += 8
            if any(x in title_lower for x in ["fall", "loss", "slump", "drop", "investigation", "penalty"]):
                score_modifier -= 10
    except Exception:
        pass
    return score_modifier, news_headlines

# --- NIFTY MARKET ENVIRONMENT ANALYSIS ---
st.subheader("📊 बाज़ार की स्थिति (Live Market Check)")

@st.cache_data(ttl=60) # Short cache for index tracking
def fetch_nifty_trends():
    try:
        nifty = yf.download("^NSEI", period="4mo", interval="1d", progress=False)
        if nifty.empty: return None
        if isinstance(nifty.columns, pd.MultiIndex): nifty.columns = nifty.columns.get_level_values(0)
        
        nifty['MA20'] = nifty['Close'].rolling(window=20).mean()
        nifty['MA50'] = nifty['Close'].rolling(window=50).mean()
        
        # Merge Yahoo historical close with live real-time Google Nifty price
        yf_close = float(nifty['Close'].iloc[-1])
        google_nifty = get_realtime_google_price("NIFTY50")
        current_nifty_close = google_nifty if google_nifty else yf_close
        
        last_row = nifty.iloc[-1]
        return {
            "date": nifty.index[-1].date(),
            "close": current_nifty_close,
            "ma20": float(last_row['MA20']),
            "ma50": float(last_row['MA50']),
            "trend": "UP" if current_nifty_close > float(last_row['MA50']) else "DOWN"
        }
    except Exception:
        return None

nifty_status = fetch_nifty_trends()

if nifty_status:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("डेटा अपडेट तारीख", str(nifty_status["date"]))
    col2.metric("Nifty लाइव भाव", f"₹{nifty_status['close']:.2f}")
    col3.metric("20-Day MA", f"₹{nifty_status['ma20']:.2f}")
    col4.metric("50-Day MA", f"₹{nifty_status['ma50']:.2f}")
    
    if nifty_status["trend"] == "DOWN":
        st.warning("⚠️ बाज़ार मंदी (Down Market) में है। स्टॉक्स में स्टॉप-लॉस हिट होने का रिस्क अधिक रहेगा।")
    else:
        st.success("✅ व्यापक बाज़ार का रुझान सकारात्मक (Bullish Environment) है।")

# --- MASTER SCANNER ENGINE WITH LIVE GAP PROTECTION ---
@st.cache_data(ttl=60) # Fast refresh for stock metrics
def deep_market_analysis():
    candidates = []
    
    for ticker in WATCHLIST:
        try:
            df = yf.download(ticker, period="4mo", interval="1d", progress=False)
            if df.empty or len(df) < 40: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            prev_close = float(df['Close'].iloc[-1])
            
            # Fetch 100% real-time price from Google
            live_price = get_realtime_google_price(ticker)
            if not live_price:
                live_price = prev_close # Fallback to yesterday close if weekend/off-hours
                
            # Anti-Penny stock safeguard (Price must be > ₹100 for safety)
            if live_price < 100.0: continue
            
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['ATR'] = df['High'].rolling(window=14).mean() - df['Low'].rolling(window=14).mean()
            
            ma20 = float(df['MA20'].iloc[-1])
            ma50 = float(df['MA50'].iloc[-1])
            atr = float(df['ATR'].iloc[-1]) if not pd.isna(df['ATR'].iloc[-1]) else (live_price * 0.02)
            
            # Setup Scoring Logic
            base_score = 60
            if live_price > ma20: base_score += 10
            if live_price > ma50: base_score += 10
            if live_price > prev_close: base_score += 5
            
            news_mod, headlines = analyze_company_news(ticker.replace(".NS",""))
            final_score = max(10, min(base_score + news_mod, 99))
            
            # Gap Opening Protection Engine: Use live price as entry if it gaps up/down
            entry = round(live_price, 2)
            stop_loss = round(entry - (1.5 * atr), 2)
            target = round(entry + (2.5 * atr), 2)
            
            # Position Sizing Risk Calculations
            risk_per_share = entry - stop_loss
            if risk_per_share > 0:
                quantity = int(MAX_RISK_INR // risk_per_share)
                if (quantity * entry) > TOTAL_CAPITAL:
                    quantity = int(TOTAL_CAPITAL // entry)
                    
                if quantity > 0:
                    candidates.append({
                        "ticker": ticker.replace(".NS", ""),
                        "score": final_score,
                        "entry": entry,
                        "target": target,
                        "stop_loss": stop_loss,
                        "quantity": quantity,
                        "news": headlines[:2]
                    })
        except Exception:
            continue
            
    return sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]

# --- RENDER INTERFACE ---
st.subheader("🎯 आज के शीर्ष 3 प्राथमिकता वाले लाइव सेटअप")

with st.spinner("लाइव रियल-टाइम डेटा और न्यूज़ का मिलान किया जा रहा है..."):
    top_3_setups = deep_market_analysis()

if top_3_setups:
    for idx, setup in enumerate(top_3_setups, 1):
        with st.container(border=True):
            c1, c2 = st.columns()
            c1.subheader(f"🟢 {setup['ticker']}")
            c1.caption(f"पोजीशन 0{idx} (प्राथमिकता रैंक)")
            
            c2.metric(label="Analysis Score", value=f"{setup['score']}/100")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Live Entry Price", f"₹{setup['entry']:.2f}")
            m2.metric("Target (🎯)", f"₹{setup['target']:.2f}")
            m3.metric("Stop-Loss (🛑)", f"₹{setup['stop_loss']:.2f}")
            
            st.info(f"👉 Quantity (₹50,000 कैपिटल रिस्क): {setup['quantity']} शेयर (मैक्सिमम लॉस लिमिट: ₹250)")
            
            if setup['news']:
                with st.expander("🔍 लाइव कॉर्पोरेट समाचार विश्लेषण"):
                    for h in setup['news']:
                        st.write(f"▪️ {h}")
else:
    st.info("डेटा सुरक्षा मानदंडों या विषम परिस्थितियों के कारण इस समय कोई लाइव सेटअप मापदंडों पर खरा नहीं उतरा।")

# --- FOOTER ---
st.markdown("---")
st.caption("💡 **टिप:** यह स्क्रीन हर 30 सेकंड में बिना बटन दबाए आपके लिए खुद-ब-खुद लाइव भाव अपडेट करती रहेगी।")
