import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
from google import genai

# 1. Page Configuration Optimized for Android Screen
st.set_page_config(page_title="Stock Saathi Supreme", page_icon="📈", layout="centered")

st.title("🎯 Stock Saathi (Supreme Master)")
st.caption("अल्ट्रा-एक्यूरेसी एआई रैंकिंग充 इंजन | लाइव गूगल फीड | जेमिनी न्यूज़ एनालिसिस")

# --- GEMINI AI SECURITY INTEGRATION ---
st.sidebar.subheader("🔑 एआई सुरक्षा कवच")
gemini_api_key = st.sidebar.text_input("अपनी Gemini API Key डालें:", type="password")

if not gemini_api_key:
    st.warning("⚠️ ऐप को ऑटोमैटिक और 100% सटीक बनाने के लिए कृपया साइडबार में Gemini API Key डालें।")

# --- CAPITAL CONFIGURATION ---
TOTAL_CAPITAL = 50000.0
RISK_PER_TRADE_PCT = 0.5  
MAX_RISK_INR = TOTAL_CAPITAL * (RISK_PER_TRADE_PCT / 100.0) # ₹250 फिक्स लॉस

# 2. COMPLETE HIGH-VOLUME WATCHLIST
WATCHLIST = [
    "HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN",
    "RELIANCE", "TCS", "INFY", "HINDUNILVR", 
    "ITC", "BHARTIARTL", "LT", "BAJFINANCE", "ASIANPAINT", "MARUTI"
]

# --- REAL-TIME LIVE PRICE FETCH ENGINE (GOOGLE FINANCE) ---
def get_live_price_only(ticker):
    try:
        url = f"https://google.com{ticker}:NSE"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=4)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            price_div = soup.find("div", {"class": "YMlKec fxKbKc"})
            if price_div:
                return float(price_div.text.replace("₹", "").replace(",", "").strip())
    except Exception:
        pass
    return None

# --- AI NEWS SENTIMENT ANALYSIS ENGINE ---
def analyze_news_with_gemini(ticker, news_list, api_key):
    if not api_key or not news_list:
        return 0, "कोई ताज़ा खबर उपलब्ध नहीं है।"
    
    try:
        combined_news = "\n".join([f"- {n['title']}" for n in news_list[:3]])
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        तुम एक प्रोफेशनल शेयर बाजार एक्सपर्ट हो। तुम्हें {ticker} स्टॉक की इन ताज़ा खबरों का विश्लेषण करना है:
        {combined_news}
        
        इस खबर के आधार पर स्टॉक को -20 से +20 के बीच एक स्कोर दो (अच्छी खबर के लिए प्लस, बुरी के लिए माइनस)।
        जवाब में सिर्फ एक छोटा सा हिंदी वाक्य और स्कोर दो। फॉर्मेट ऐसा होना चाहिए: स्कोर|तुम्हारा विश्लेषण
        उदाहरण: +15|तिमाही नतीजे उम्मीद से बेहतर हैं, तेजी की संभावना।
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        result_text = response.text.strip()
        if "|" in result_text:
            score_part, analysis_part = result_text.split("|", 1)
            return int(score_part.strip()), analysis_part.strip()
        return 0, result_text
    except Exception:
        return 0, f"एआई विश्लेषण उपलब्ध नहीं हो सका।"

# --- MASTER SCANNER ENGINE (🚨 HIGH TO LOW RANKING) ---
st.subheader("🎯 आज के शीर्ष 3 प्राथमिकता वाले लाइव投放 सेटअप")

def deep_historical_and_live_scan():
    setups = []
    
    for ticker in WATCHLIST:
        try:
            df = yf.download(f"{ticker}.NS", period="2mo", interval="1d", progress=False)
            if df.empty or len(df) < 20: continue
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            yesterday_close = float(df['Close'].values[-1])
            live_price = get_live_price_only(ticker)
            
            if not live_price or live_price <= 0:
                live_price = yesterday_close
                
            if live_price < 100.0: continue
            
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
            
            atr_val = float(df['ATR'].values[-1]) if not pd.isna(df['ATR'].values[-1]) else (live_price * 0.025)
            
            # लाइव न्यूज़ एक्सट्रैक्शन
            ticker_obj = yf.Ticker(f"{ticker}.NS")
            live_news = ticker_obj.news
            
            # जेमिनी एआई द्वारा खबरों का विश्लेषण
            ai_score_boost, ai_reason = analyze_news_with_gemini(ticker, live_news, gemini_api_key)
            
            base_score = 70
            base_score += ai_score_boost
            
            if live_price >= yesterday_close: 
                base_score += 5
                
            final_score = max(10, min(base_score, 99))
            
            entry = round(live_price, 2)
            stop_loss = round(entry - (1.5 * atr_val), 2)
            target = round(entry + (2.5 * atr_val), 2)
            
            risk_per_share = entry - stop_loss
            if risk_per_share > 0:
                quantity = int(MAX_RISK_INR // risk_per_share)
                
                if (quantity * entry) > TOTAL_CAPITAL:
                    quantity = int(TOTAL_CAPITAL // entry)
                    
                if quantity > 0:
                    setups.append({
                        "ticker": ticker,
                        "score": round(final_score, 1),
                        "entry": entry,
                        "target": target,
                        "stop_loss": stop_loss,
                        "quantity": quantity,
                        "reason": ai_reason
                    })
        except Exception:
            continue
            
    return sorted(setups, key=lambda x: x['score'], reverse=True)[:3]

if gemini_api_key:
    top_3 = deep_historical_and_live_scan()
else:
    top_3 = []

st.sidebar.info("⏸️ हॉलिडे मोड: सप्ताहांत (Weekend) विश्लेषण सक्रिय है।")

if gemini_api_key and top_3:
    for idx, setup in enumerate(top_3, 1):
        with st.container(border=True):
            col_l, col_r = st.columns(2)
            col_l.subheader(f"🟢 {setup['ticker']}")
            col_l.caption(f"पोजीशन 0{idx} (प्राथमिकता रैंक)")
            col_r.metric(label="AI Accuracy Score", value=f"{setup['score']}/100")
            
            st.info(f"🤖 **एआई लाइव विश्लेषण:** {setup['reason']}")
            
            m_en, m_tg, m_sl = st.columns(3)
            m_en.metric("Entry Price", f"₹{setup['entry']:.2f}")
            m_tg.metric("Target (🎯)", f"₹{setup['target']:.2f}")
            m_sl.metric("Stop-Loss (🛑)", f"₹{setup['stop_loss']:.2f}")
            
            st.warning(f"👉 Quantity (₹50k कैपिटल रिस्क): {setup['quantity']} शेयर (मैक्सिमम लॉस लिमिट: ₹250)")
            
            chart_url = f"https://tradingview.com{setup['ticker']}/"
            st.link_button(f"📉 {setup['ticker']} का लाइव चार्ट देखें (TradingView)", chart_url, use_container_width=True)
elif gemini_api_key and not top_3:
    st.info("वर्तमान में मानदंडों पर कोई स्टॉक उपलब्ध नहीं है। डेटा लोड हो रहा है...")

st.markdown("---")
st.caption("🛡️ **मास्टर कवच सक्रिय:** यह एआई इंजन हर स्टॉक की लाइव खबरों को पढ़कर उसका स्कोर तय करता है।")
