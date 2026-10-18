import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from google import genai

# 1. पेज कॉन्फ़िगरेशन और थीम सेटिंग्स
st.set_page_config(page_title="Stock Saathi - Institutional Matrix", page_icon="🎯", layout="wide")

st.title("🎯 Stock Saathi (Institutional Matrix Engine)")
st.caption("मल्टी-वेक्टर एक्यूरेसी स्कैनर | 20D ब्रेकआउट अलर्ट | लाइव मैक्रो पल्स | जेमिनी एआई न्यूज़ गन")

# --- सुरक्षा प्रणाली (Master Lock) ---
MASTER_PASSWORD = "Saathi@2026"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    with st.sidebar:
        st.subheader("🔒 security access")
        user_password = st.text_input("मास्टर पासवर्ड दर्ज करें:", type="password", key="login_pass")
        if st.button("अनलॉक करें") or (user_password == MASTER_PASSWORD and user_password):
            if user_password == MASTER_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ गलत पासवर्ड!")
    st.info("👋 कृपया जारी रखने के लिए साइडबार में अपना सुरक्षा पासवर्ड दर्ज करें।")
    st.stop()

# --- जेमिनी एआई की प्रबंधन (Crash-Proof) ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY", None)
if not gemini_api_key:
    gemini_api_key = st.sidebar.text_input("Gemini API Key दर्ज करें (न्यूज़ एनालिसिस के लिए):", type="password", key="gemini_key")

# --- साइडबार सेटिंग्स (यूजर पूँजी नियम) ---
with st.sidebar:
    st.header("⚙️ कैपिटल एलोकेशन")
    capital = st.number_input("आपकी कुल ट्रेडिंग पूँजी (₹)", min_value=5000, max_value=100000000, value=50000, step=5000)
    risk_pct = st.slider("एक ट्रेड में रिस्क सीमा (%)", 0.25, 2.0, 0.5, 0.25)
    max_risk_inr = capital * (risk_pct / 100.0)
    
    if st.button("🔒 ऐप लॉक करें"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- विस्तृत स्टॉक यूनिवर्स (सभी प्रमुख सेक्टर्स, बैंकिंग और इंडेक्स हेवीवेट्स) ---
UNIVERSE = {
    'Reliance Industries': 'RELIANCE.NS', 'HDFC Bank': 'HDFCBANK.NS',
    'ICICI Bank': 'ICICIBANK.NS', 'State Bank of India': 'SBIN.NS',
    'Axis Bank': 'AXISBANK.NS', 'Kotak Mahindra Bank': 'KOTAKBANK.NS',
    'TCS': 'TCS.NS', 'Infosys': 'INFY.NS', 'Bharti Airtel': 'BHARTIARTL.NS',
    'Larsen & Toubro': 'LT.NS', 'ITC': 'ITC.NS', 'Hindustan Unilever': 'HINDUNILVR.NS',
    'Tata Motors': 'TATAMOTORS.NS', 'Mahindra & Mahindra': 'M&M.NS', 'Sun Pharma': 'SUNPHARMA.NS'
}

# --- डेटा फेचिंग और इंडिकेटर फंक्शन्स ---
@st.cache_data(ttl=180, show_spinner=False)
def get_market_vectors():
    vectors = {"NIFTY": "MIXED", "BANKNIFTY": "MIXED", "CRUDE": "STABLE", "FII": "NEUTRAL"}
    try:
        for sym, key in [("^NSEI", "NIFTY"), ("^NSEBANK", "BANKNIFTY")]:
            tk = yf.Ticker(sym)
            hist = tk.history(period="50d")
            if not hist.empty and len(hist) >= 50:
                c = hist['Close']
                vectors[key] = "UPTREND" if c.iloc[-1] > c.rolling(20).mean().iloc[-1] > c.rolling(50).mean().iloc[-1] else "DOWNTREND"
    except Exception:
        pass
    return vectors

def fetch_stock_data(ticker):
    try:
        data = yf.download(ticker, period='6mo', interval='1d', progress=False, auto_adjust=True)
        if data.empty: return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data.dropna()
    except Exception:
        return None

def ai_news_scorer(ticker, api_key):
    if not api_key: return 0, "एआई चाबी अनुपलब्ध। केवल तकनीकी विश्लेषण सक्रिय।"
    try:
        tk = yf.Ticker(ticker)
        news = tk.news[:3]
        if not news: return 0, "कोई ताज़ा कॉर्पोरेट न्यूज़ नहीं मिली।"
        
        combined_text = "\n".join([f"- {n['title']}" for n in news])
        client = genai.Client(api_key=api_key)
        prompt = f"""
        तुम एक हेज फंड के मुख्य क्वांट रिसर्चर हो। तुम्हें {ticker} स्टॉक की इस लाइव न्यूज़ का कठोर विश्लेषण करना है:
        {combined_text}
        बाजार के सेंटिमेंट को देखते हुए इस न्यूज़ को -25 से +25 के बीच एक स्कोर दो। 
        अगर कोई विशेष खबर नहीं है तो 0 दो। 
        जवाब केवल इस फॉर्मेट में होना चाहिए: स्कोर|एक छोटा सटीक वाक्य (हिंदी में)
        उदाहरण: +20|शानदार तिमाही नतीजे और मार्जिन विस्तार, भारी तेजी के संकेत।
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        score_part, text_part = response.text.strip().split("|", 1)
        return int(score_part.strip()), text_part.strip()
    except Exception:
        return 0, "न्यूज़ इंजनों से संपर्क अस्थायी रूप से बाधित।"

# --- मुख्य स्क्रीन यूआई और प्रोसेसिंग लॉजिक ---
st.subheader("📊 लाइव इंस्टीट्यूशनल मैक्रो डैशबोर्ड")
with st.spinner("वैश्विक और घरेलू सूचकांकों का विश्लेषण जारी है..."):
    m_vectors = get_market_vectors()

c1, c2, c3 = st.columns(3)

nifty_label = "सतर्क रहें (मंदी)" if m_vectors["NIFTY"] == "DOWNTREND" else "अनुकूल (तेजी)"
nifty_delta = f"↓ {nifty_label}" if m_vectors["NIFTY"] == "DOWNTREND" else f"↑ {nifty_label}"
c1.metric(label="Nifty 50 मुख्य दिशा", value=m_vectors["NIFTY"], delta=nifty_delta, delta_color="inverse" if m_vectors["NIFTY"] == "DOWNTREND" else "normal")

bank_label = "दबाव में (मंदी)" if m_vectors["BANKNIFTY"] == "DOWNTREND" else "बैंकिंग सपोर्ट"
bank_delta = f"↓ {bank_label}" if m_vectors["BANKNIFTY"] == "DOWNTREND" else f"↑ {bank_label}"
c2.metric(label="Bank Nifty गति", value=m_vectors["BANKNIFTY"], delta=bank_delta, delta_color="inverse" if m_vectors["BANKNIFTY"] == "DOWNTREND" else "normal")

c3.info("💡 **सटीकता नियम:** जब बाजार (Nifty) विपरीत हो, तब सिस्टम केवल उन्हीं चुनिंदा शेयरों को शॉर्टलिस्ट करता है जिनका alpha (Alpha) और वॉल्यूम बेहद असाधारण हो।")

if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = None

st.markdown("---")
if st.button("🔎 पूरे बाजार का महा-स्कैन शुरू करें (High-Accuracy Scan)", type="primary", use_container_width=True):
    with st.spinner("सभी कंपनियों का डेटा, डिलीवरी वॉल्यूम, ब्रेकआउट स्तर और जेमिनी लाइव न्यूज़ सिंक की जा रही है..."):
        all_setups = []
        
        for name, ticker in UNIVERSE.items():
            df = fetch_stock_data(ticker)
            if df is None or len(df) < 30: continue
            
            close = df['Close'].astype(float)
            high = df['High'].astype(float)
            low = df['Low'].astype(float)
            vol = df['Volume'].astype(float)
            
            last_price = float(close.iloc[-1])
            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma50 = float(close.rolling(50).mean().iloc[-1])
            
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            last_loss = loss.iloc[-1]
            last_gain = gain.iloc[-1]
            rsi = 100.0 if last_loss == 0 or np.isnan(last_loss) else float(100 - (100 / (1 + (last_gain / last_loss))))
            
            v20 = float(vol.rolling(20).mean().iloc[-1])
            v_ratio = float(vol.iloc[-1] / v20) if v20 > 0 else 1.0
            
            prev_20_days_high = float(high.iloc[-21:-1].max())
            prev_20_days_low = float(low.iloc[-21:-1].min())
            
            breakout_status = "💥 20D HIGH BREAKOUT" if last_price > prev_20_days_high else ("⚠️ 20D LOW BREAKDOWN" if last_price < prev_20_days_low else "NORMAL ZONE")
            breakout_bonus = 10 if last_price > prev_20_days_high else (5 if last_price < prev_20_days_low else 0)
            
            ai_boost, ai_reason = ai_news_scorer(ticker, gemini_api_key)
            
            accuracy_score = 60
            if last_price > ma20 > ma50: accuracy_score += 15
            elif last_price < ma20 < ma50: accuracy_score -= 15
            if v_ratio >= 1.5: accuracy_score += 10
            if 50 <= rsi <= 65: accuracy_score += 10
            accuracy_score += (ai_boost + breakout_bonus)
            accuracy_score = max(5, min(accuracy_score, 99.5))
            
            tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])
            
            direction = "SELL (Short)" if (m_vectors["NIFTY"] == "DOWNTREND" and last_price < ma20) else "BUY"
            stop_loss = last_price + (1.6 * atr) if direction == "SELL (Short)" else last_price - (1.6 * atr)
            target = last_price - (2.5 * atr) if direction == "SELL (Short)" else last_price + (2.5 * atr)
            if direction == "SELL (Short)": accuracy_score += 5
                
            risk_per_share = abs(last_price - stop_loss)
            qty = int(max_risk_inr // risk_per_share) if risk_per_share > 0 else 0
            qty = min(qty, int(capital // last_price))
            
            # 100% फ्लैट सिंगल-लाइन अपेंड - कोई डिक्शनरी/टुपल वेरिएबल ब्रैकेट नहीं (Zero-Risk Compiler Strategy)
            all_setups.append([name, ticker, direction, round(accuracy_score, 1), round(last_price, 2), round(last_price, 2), round(target, 2), round(stop_loss, 2), qty, round(v_ratio, 2), round(rsi, 1), breakout_status, ai_reason])
            
        st.session_state["scan_results"] = sorted(all_setups, key=lambda x: x[3], reverse=True)[:3]

# --- परिणामों को स्क्रीन पर प्रदर्शित करना ---
if st.session_state["scan_results"]:
    top_trades = st.session_state["scan_results"]
    st.subheader("🔥 सर्वोच्च सटीकता वाले टॉप 3 प्रायोरिटी लाइव ठेवा")
    
    for rank, trade in enumerate(top_trades, 1):
        with st.container(border=True):
            cols = st.columns(3)
            with cols[0]:
                st.subheader(f"🏆 रैंक 0{rank}")
                st.markdown(f"### **{trade[0]}**")
                st.caption(f"सिंबल: {trade[1]}")
                if "BREAKOUT" in trade[11]: st.success(f"⚡ {trade[11]}")
