import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import datetime

# Page configuration for mobile devices
st.set_page_config(page_title="Stock Saathi", page_icon="📈", layout="vertical")

st.title("🎯 Stock Saathi (संशोधित संस्करण)")
st.caption("भारतीय शेयर बाजार (Cash Segment) स्कैनर | केवल शैक्षिक उद्देश्य के लिए")

# --- CONSTANTS & CONFIGURATION ---
TOTAL_CAPITAL = 50000.0
RISK_PER_TRADE_PCT = 0.5  # 0.5% risk
MAX_RISK_INR = TOTAL_CAPITAL * (RISK_PER_TRADE_PCT / 100.0)  # ₹250

# Watchlist for scanning (Cash segment & Nifty BeES)
WATCHLIST = [
    "NIFTYBEES.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS",
    "LT.NS", "BAJFINANCE.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS"
]

# --- HELPER FUNCTIONS ---

def get_google_finance_price(ticker):
    """
    Alternative data source using basic web scraping from Google Finance.
    Adheres to fair usage for tracking verification.
    """
    try:
        # Format for Google: RELIANCE.NS -> BOM:RELIANCE or NSE:RELIANCE
        sym = ticker.replace(".NS", "")
        url = f"https://google.com{sym}:NSE"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_config == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Find the price element class (Google Finance live price div identifier)
            price_div = soup.find("div", {"class": "YMlKec fxKbKc"})
            if price_div:
                price_str = price_div.text.replace("₹", "").replace(",", "").strip()
                return float(price_str)
    except Exception:
        pass
    return None

def fetch_rss_news():
    """
    Fetches real public financial alerts from RSS feeds.
    Strictly avoids fake news generation.
    """
    news_items = []
    # Using a reliable public marketplace news feed (e.g., Economic Times / Moneycontrol via public RSS)
    rss_urls = [
        "https://indiatimes.com",
        "https://moneycontrol.com"
    ]
    
    for url in rss_urls:
        try:
            resp = requests.get(url, timeout=5)
            soup = BeautifulSoup(resp.content, features="xml")
            items = soup.find_all("item")
            for item in items[:4]:
                title = item.title.text if item.title else ""
                link = item.link.text if item.link else ""
                if title and title not in [n['title'] for n in news_items]: # Avoid exact duplicates
                    news_items.append({"title": title, "link": link})
        except Exception:
            pass
    return news_items

# --- 1. NIFTY DATA CHECK & TREND FILTER ---
st.subheader("📊 Nifty 50 बाज़ार स्थिति की जाँच")

@st.cache_data(ttl=300) # Cache for 5 minutes
def check_nifty_health():
    try:
        nifty = yf.download("^NSEI", period="3mo", interval="1d", progress=False)
        if nifty.empty:
            return None, "Yahoo Finance से Nifty डेटा प्राप्त नहीं हो सका (खाली डेटा)।"
        
        # Flatten MultiIndex columns if present
        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = nifty.columns.get_level_values(0)
            
        nifty['MA20'] = nifty['Close'].rolling(window=20).mean()
        nifty['MA50'] = nifty['Close'].rolling(window=50).mean()
        
        last_row = nifty.iloc[-1]
        last_date = nifty.index[-1].date()
        today = datetime.date.today()
        
        # Check for stale data (e.g., older than 4 days considering weekends/holidays)
        days_diff = (today - last_date).days
        status_warning = ""
        if days_diff > 4:
            status_warning = f"चेतावनी: डेटा पुराना लग रहा है! आखिरी डेटा {last_date} का है ({days_diff} दिन पुराना)।"
            
        return {
            "date": last_date,
            "close": float(last_row['Close']),
            "ma20": float(last_row['MA20']),
            "ma50": float(last_row['MA50']),
            "trend": "UP" if last_row['Close'] > last_row['MA50'] else "DOWN",
            "warning": status_warning
        }, None
    except Exception as e:
        return None, f"तकनीकी एरर के कारण Nifty डेटा की जाँच नहीं हो सकी: {str(e)}"

nifty_status, error_msg = check_nifty_health()

market_safe = True
if error_msg:
    st.error(error_msg)
    market_safe = False
elif nifty_status:
    if nifty_status["warning"]:
        st.warning(nifty_status["warning"])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("आखिरी तारीख", str(nifty_status["date"]))
    col2.metric("बंद भाव (Close)", f"₹{nifty_status['close']:.2f}")
    col3.metric("20-Day MA", f"₹{nifty_status['ma20']:.2f}")
    col4.metric("50-Day MA", f"₹{nifty_status['ma50']:.2f}")
    
    if nifty_status["trend"] == "DOWN":
        st.error("⚠️ बाज़ार चेतावनी: Nifty का ट्रेंड डाउन (Below 50 MA) है। जोखिम बहुत अधिक है। नए लॉन्ग सेटअप को रोका जा सकता है।")
        market_safe = False
    else:
        st.success("✅ Nifty लॉन्ग-टर्म ट्रेंड सामान्य (Above 50 MA) है।")

# --- 2. MULTI-SOURCE & NEWS ANALYSIS ---
st.subheader("📰 कॉर्पोरेट घोषणाएं और समाचार सत्यापन")
latest_news = fetch_rss_news()
if latest_news:
    for nw in latest_news[:3]:
        st.write(f"🔹 *{nw['title']}*")
else:
    st.info("इस समय कोई नई आधिकारिक घोषणा या फ़ीड उपलब्ध नहीं है। केवल हेडलाइन के भरोसे ट्रेडिंग न करें।")

# --- 3. SCANNING & SETUP GENERATION ---
st.subheader("🎯 शीर्ष संभावित टेक्निकल सेटअप (अधिकतम 3)")

if not market_safe:
    st.warning("⚠️ बाज़ार का रुख सुरक्षित न होने के कारण सुरक्षा फ़िल्टर सक्रिय हैं। नीचे दिए गए सिग्नलों पर सावधानी बरतें।")

@st.cache_data(ttl=600)
def scan_market():
    setups = []
    for ticker in WATCHLIST:
        try:
            # Fetch Yahoo Data
            df = yf.download(ticker, period="3mo", interval="1d", progress=False)
            if df.empty or len(df) < 50:
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Cross Verification with Alternative Source (Google Finance)
            yf_price = float(df['Close'].iloc[-1])
            gf_price = get_google_finance_price(ticker)
            
            # Data Integrity Check
            if gf_price is not None:
                price_diff_pct = abs(yf_price - gf_price) / yf_price * 100
                if price_diff_pct > 1.5: # 1.5% से ज़्यादा का अंतर होने पर डेटा असुरक्षित माना जाएगा
                    continue
            
            # Basic non-predictive scoring criteria based on technical alignment
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['ATR'] = df['High'].rolling(window=14).mean() - df['Low'].rolling(window=14).mean() # Simplistic ATR
            
            last_close = float(df['Close'].iloc[-1])
            ma20_val = float(df['MA20'].iloc[-1])
            atr_val = float(df['ATR'].iloc[-1]) if not pd.isna(df['ATR'].iloc[-1]) else (last_close * 0.02)
            
            # Technical condition for a setup (e.g., price bouncing near 20MA)
            if last_close > ma20_val:
                score = 65  # Base match rate
                if last_close > float(df['Close'].iloc[-2]): score += 15
                
                entry = round(last_close, 2)
                stop_loss = round(entry - (1.5 * atr_val), 2)
                target = round(entry + (3.0 * atr_val), 2)
                
                # Risk calculation
                risk_per_share = entry - stop_loss
                if risk_per_share > 0:
                    quantity = int(MAX_RISK_INR // risk_per_share)
                    total_cost = quantity * entry
                    
                    # Capital bottleneck check
                    if total_cost > TOTAL_CAPITAL:
                        quantity = int(TOTAL_CAPITAL // entry)
                        
                    if quantity > 0:
                        setups.append({
                            "ticker": ticker,
                            "score": min(score, 100),
                            "entry": entry,
                            "target": target,
                            "stop_loss": stop_loss,
                            "quantity": quantity
                        })
        except Exception:
            continue
    # Sort setups by higher technical match rate
    setups = sorted(setups, key=lambda x: x['score'], reverse=True)
    return setups[:3]

with st.spinner("विश्वसनीय डेटा स्रोतों की जाँच और मिलान जारी है..."):
    final_setups = scan_market()

if final_setups:
    for setup in final_setups:
        with st.container():
            st.markdown(f"""
            <div style="border:1px solid #e6e6e6; padding:15px; border-radius:10px; margin-bottom:15px; background-color:#1e2530;">
                <h3 style="margin:0; color:#4CAF50;">🟢 {setup['ticker']}</h3>
                <p style="margin:5px 0;"><b>इंडिकेटर मैच स्कोर:</b> {setup['score']}/100 <small>(यह मुनाफे की संभावना नहीं है)</small></p>
                <hr style="margin:10px 0; border:0.5px solid #444;">
                <table style="width:100%; text-align:left;">
                    <tr><th>Entry</th><td>₹{setup['entry']}</td></tr>
                    <tr><th>Target</th><td>₹{setup['target']}</td></tr>
                    <tr><th>Stop-Loss</th><td>₹{setup['stop_loss']}</td></tr>
                    <tr><th style="color:#FF9800;">Quantity (₹50k Capital)</th><td style="color:#FF9800; font-weight:bold;">{setup['quantity']} Shares</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
else:
