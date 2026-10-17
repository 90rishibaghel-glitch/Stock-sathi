import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import datetime

# Page configuration for clean mobile preview
st.set_page_config(page_title="Stock Saathi Premium", page_icon="🎯", layout="centered")

st.title("🎯 Stock Saathi")
st.caption("AI-पॉवर्ड प्री-मार्केट डीप एनालिसिस स्कैनर | लाइव कैश सेगमेंट")

# --- CAPITAL CONFIGURATION ---
TOTAL_CAPITAL = 50000.0
RISK_PER_TRADE_PCT = 0.5  
MAX_RISK_INR = TOTAL_CAPITAL * (RISK_PER_TRADE_PCT / 100.0)  # ₹250 max loss

# Comprehensive high-probability watchlist for scan
WATCHLIST = [
    "NIFTYBEES.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS",
    "LT.NS", "BAJFINANCE.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "TATASTEEL.NS", "M&M.NS", "SUNPHARMA.NS", "POWERGRID.NS", "NTPC.NS"
]

# --- ADVANCED NEWS & REPORT SCRAPER ---
def analyze_company_news(ticker_name):
    """
    Scrapes actual financial news updates from Google News RSS for the target stock.
    """
    score_modifier = 0
    news_headlines = []
    try:
        query = f"{ticker_name} stock price analysis results"
        url = f"https://google.com{query}&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(url, timeout=4)
        soup = BeautifulSoup(resp.content, features="xml")
        items = soup.find_all("item")
        
        for item in items[:4]:
            title = item.title.text
            news_headlines.append(title)
            title_lower = title.lower()
            if any(x in title_lower for x in ["profit", "rise", "buy", "growth", "dividend", "beats"]):
                score_modifier += 6
            if any(x in title_lower for x in ["fall", "loss", "slump", "drop", "sell", "miss"]):
                score_modifier -= 8
    except Exception:
        pass
    return score_modifier, news_headlines

def get_alternative_price(ticker):
    """ Cross-verifies price against secondary server infrastructure """
    try:
        sym = ticker.replace(".NS", "")
        url = f"https://google.com{sym}:NSE"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=3)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            price_div = soup.find("div", {"class": "YMlKec fxKbKc"})
            if price_div:
                return float(price_div.text.replace("₹", "").replace(",", "").strip())
    except Exception:
        pass
    return None

# --- NIFTY MARKET ENVIRONMENT ANALYSIS ---
st.subheader("📊 बाज़ार खुलने से पहले की स्थिति (Pre-Market Check)")

@st.cache_data(ttl=600)
def fetch_nifty_trends():
    try:
        nifty = yf.download("^NSEI", period="4mo", interval="1d", progress=False)
        if nifty.empty: return None
        if isinstance(nifty.columns, pd.MultiIndex): nifty.columns = nifty.columns.get_level_values(0)
        
        nifty['MA20'] = nifty['Close'].rolling(window=20).mean()
        nifty['MA50'] = nifty['Close'].rolling(window=50).mean()
        last = nifty.iloc[-1]
        return {
            "date": nifty.index[-1].date(),
            "close": float(last['Close']),
            "ma20": float(last['MA20']),
            "ma50": float(last['MA50']),
            "trend": "UP" if last['Close'] > last['MA50'] else "DOWN"
        }
    except Exception:
        return None

nifty_status = fetch_nifty_trends()
market_warning_triggered = False

if nifty_status:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("डेटा तारीख", str(nifty_status["date"]))
    col2.metric("Nifty क्लोज", f"₹{nifty_status['close']:.2f}")
    col3.metric("20-Day MA", f"₹{nifty_status['ma20']:.2f}")
    col4.metric("50-Day MA", f"₹{nifty_status['ma50']:.2f}")
    
    if nifty_status["trend"] == "DOWN":
        st.warning("⚠️ बाज़ार मंदी (Down Market) में है। स्टॉक्स में स्टॉप-लॉस हिट होने का रिस्क अधिक रहेगा।")
        market_warning_triggered = True
    else:
        st.success("✅ व्यापक बाज़ार का रुझान सकारात्मक (Bullish Environment) है।")

# --- MASTER SCANNER ENGINE ---
@st.cache_data(ttl=1200)
def deep_market_analysis():
    candidates = []
    
    for ticker in WATCHLIST:
        try:
            df = yf.download(ticker, period="4mo", interval="1d", progress=False)
            if df.empty or len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            last_close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            
            alt_price = get_alternative_price(ticker)
            if alt_price:
                if (abs(last_close - alt_price) / last_close) * 100 > 2.0: continue
            
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['ATR'] = df['High'].rolling(window=14).mean() - df['Low'].rolling(window=14).mean()
            
            ma20 = float(df['MA20'].iloc[-1])
            ma50 = float(df['MA50'].iloc[-1])
            atr = float(df['ATR'].iloc[-1]) if not pd.isna(df['ATR'].iloc[-1]) else (last_close * 0.02)
            
            base_score = 60
            if last_close > ma20: base_score += 10
            if last_close > ma50: base_score += 10
            if last_close > prev_close: base_score += 5
            
            news_mod, headlines = analyze_company_news(ticker.replace(".NS",""))
            final_score = max(10, min(base_score + news_mod, 99))
            
            entry = round(last_close, 2)
            stop_loss = round(entry - (1.5 * atr), 2)
            target = round(entry + (2.5 * atr), 2)
            
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
st.subheader("🎯 आज के शीर्ष 3 प्राथमिकता वाले सेटअप")

with st.spinner("सभी कंपनियों की रिपोर्ट्स और न्यूज़ एनालिसिस की जा रही है..."):
    top_3_setups = deep_market_analysis()

if top_3_setups:
    for idx, setup in enumerate(top_3_setups, 1):
        # Using Streamlit Containers to perfectly mirror the requested preview logic safely
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            c1.subheader(f"🟢 {setup['ticker']}")
            c1.caption(f"पोजीशन 0{idx} (प्राथमिकता रैंक)")
            
            c2.metric(label="Analysis Score", value=f"{setup['score']}/100")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Entry Price", f"₹{setup['entry']:.2f}")
            m2.metric("Target", f"₹{setup['target']:.2f}")
            m3.metric("Stop-Loss", f"₹{setup['stop_loss']:.2f}")
            
            st.info(f"👉 Quantity (₹50,000 पूँजी रिस्क): {setup['quantity']} शेयर")
            
            if setup['news']:
                with st.expander("🔍 कंपनी समाचार विश्लेषण रिपोर्ट"):
                    for h in setup['news']:
                        st.write(f"▪️ {h}")
else:
    st.info("वर्तमान डेटा सुरक्षा मानदंडों के कारण कोई सेटअप उपलब्ध नहीं है।")

# --- MANDATORY RISK SAFEGUARD ---
st.markdown("---")
st.caption("**शैक्षिक अस्वीकरण:** एनालिसिस स्कोर तकनीकी इंडिकेटर्स का मैच रेट दिखाता है, यह मुनाफ़े की निश्चित गारंटी नहीं है।")
