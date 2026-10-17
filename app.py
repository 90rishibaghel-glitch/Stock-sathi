import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import datetime

# Page configuration for mobile devices - Fixed layout error
st.set_page_config(page_title="Stock Saathi", page_icon="📈", layout="centered")

st.title("🎯 Stock Saathi")
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
    """
    try:
        sym = ticker.replace(".NS", "")
        url = f"https://google.com{sym}:NSE"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
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
    """
    news_items = []
    rss_urls = [
        "https://indiatimes.com"
    ]
    for url in rss_urls:
        try:
            resp = requests.get(url, timeout=5)
            soup = BeautifulSoup(resp.content, features="xml")
            items = soup.find_all("item")
            for item in items[:3]:
                title = item.title.text if item.title else ""
                if title and title not in [n['title'] for n in news_items]:
                    news_items.append({"title": title})
        except Exception:
            pass
    return news_items

# --- 1. NIFTY DATA CHECK & TREND FILTER ---
st.subheader("📊 Nifty 50 बाज़ार स्थिति की जाँच")

@st.cache_data(ttl=300)
def check_nifty_health():
    try:
        nifty = yf.download("^NSEI", period="3mo", interval="1d", progress=False)
        if nifty.empty:
            return None, "Yahoo Finance से Nifty डेटा प्राप्त नहीं हो सका।"
        
        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = nifty.columns.get_level_values(0)
            
        nifty['MA20'] = nifty['Close'].rolling(window=20).mean()
        nifty['MA50'] = nifty['Close'].rolling(window=50).mean()
        
        last_row = nifty.iloc[-1]
        last_date = nifty.index[-1].date()
        today = datetime.date.today()
        
        days_diff = (today - last_date).days
        status_warning = ""
        if days_diff > 4:
            status_warning = f"चेतावनी: डेटा पुराना है! आखिरी डेटा {last_date} का है।"
            
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
    col2.metric("बंद भाव", f"₹{nifty_status['close']:.2f}")
    col3.metric("20-Day MA", f"₹{nifty_status['ma20']:.2f}")
    col4.metric("50-Day MA", f"₹{nifty_status['ma50']:.2f}")
    
    if nifty_status["trend"] == "DOWN":
        st.error("⚠️ बाज़ार चेतावनी: Nifty 50 MA के नीचे है। जोखिम अधिक होने के कारण नए लॉन्ग सेटअप रोके गए हैं।")
        market_safe = False
    else:
        st.success("✅ Nifty लॉन्ग-टर्म ट्रेंड सामान्य (Above 50 MA) है।")

# --- 2. NEWS ANALYSIS ---
st.subheader("📰 वित्तीय समाचार और घोषणाएं")
latest_news = fetch_rss_news()
if latest_news:
    for nw in latest_news:
        st.info(f"🔹 {nw['title']}")
else:
    st.write("इस समय कोई नई आधिकारिक घोषणा उपलब्ध नहीं है।")

# --- 3. SCANNING & SETUP GENERATION ---
st.subheader("🎯 शीर्ष संभावित टेक्निकल सेटअप (अधिकतम 3)")

@st.cache_data(ttl=600)
def scan_market():
    setups = []
    for ticker in WATCHLIST:
        try:
            df = yf.download(ticker, period="3mo", interval="1d", progress=False)
            if df.empty or len(df) < 50:
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            yf_price = float(df['Close'].iloc[-1])
            gf_price = get_google_finance_price(ticker)
            
            if gf_price is not None:
                price_diff_pct = abs(yf_price - gf_price) / yf_price * 100
                if price_diff_pct > 1.5:
                    continue
            
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['ATR'] = df['High'].rolling(window=14).mean() - df['Low'].rolling(window=14).mean()
            
            last_close = float(df['Close'].iloc[-1])
            ma20_val = float(df['MA20'].iloc[-1])
            atr_val = float(df['ATR'].iloc[-1]) if not pd.isna(df['ATR'].iloc[-1]) else (last_close * 0.02)
            
            if last_close > ma20_val:
                score = 70
                if last_close > float(df['Close'].iloc[-2]):
                    score += 15
                
                entry = round(last_close, 2)
                stop_loss = round(entry - (1.5 * atr_val), 2)
                target = round(entry + (3.0 * atr_val), 2)
                
                risk_per_share = entry - stop_loss
                if risk_per_share > 0:
                    quantity = int(MAX_RISK_INR // risk_per_share)
                    if (quantity * entry) > TOTAL_CAPITAL:
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
            
    setups = sorted(setups, key=lambda x: x['score'], reverse=True)
    return setups[:3]

if not market_safe:
    st.warning("⚠️ मार्केट डाउनट्रेंड में होने के कारण सुरक्षा नियमों के तहत लाइव सेटअप ब्लॉक कर दिए गए हैं।")
    final_setups = []
else:
    with st.spinner("डेटा स्रोतों का मिलान जारी है..."):
        final_setups = scan_market()

if final_setups:
    for setup in final_setups:
        with st.expander(f"🟢 {setup['ticker']} (मैच स्कोर: {setup['score']}/100)", expanded=True):
            st.write(f"**Entry Price:** ₹{setup['entry']}")
            st.write(f"**Target:** ₹{setup['target']}")
            st.write(f"**Stop-Loss:** ₹{setup['stop_loss']}")
            st.info(f"👉 **Quantity (₹50,000 पूँजी के अनुसार):** {setup['quantity']} Shares")
else:
    if market_safe:
        st.info("❌ वर्तमान में रिस्क मैनेजमेंट या डेटा शुद्धता मानदंडों पर कोई भी स्टॉक खरा नहीं उतरा।")

# --- 4. DISCLAIMER ---
st.markdown("---")
st.markdown("""
### 🔍 अत्यंत महत्वपूर्ण सूचना
- **डेटा सीमा:** यह ऐप मुफ़्त ऐतिहासिक डेटा (Yahoo/Google) का मिलान करता. है। यह लाइव एक्सचेंज फीड नहीं है।
- **सुरक्षा:** निवेश करने से पहले अपने वित्तीय सलाहकार से अवश्य संपर्क करें।
""")
            
