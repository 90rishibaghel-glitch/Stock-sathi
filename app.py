import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from google import genai

# 1. पेज कॉन्फ़िगरेशन (पूरी स्क्रीन का उपयोग करने के लिए WIDE लेआउट)
st.set_page_config(page_title="Stock Saathi Supreme", page_icon="📈", layout="wide")

st.title("🎯 Stock Saathi (Supreme Quant Engine)")
st.caption("अल्ट्रा-एक्यूरेसी क्वांट स्कैनर | 20D ब्रेकआउट अलर्ट सिस्टम | लाइव मैक्रो पल्स")

# --- सुरक्षा कवच (Master Protection Lock) ---
MASTER_PASSWORD = "Saathi@2026"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    with st.sidebar:
        st.subheader("🔒 सुरक्षा एक्सेस")
        user_password = st.text_input("मास्टर पासवर्ड दर्ज करें:", type="password", key="app_login_key")
        if st.button("ऐप अनलॉक करें") or (user_password == MASTER_PASSWORD and user_password):
            if user_password == MASTER_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.sidebar.error("❌ गलत पासवर्ड!")
    st.info("👋 सुरक्षा लॉक सक्रिय है। ऐप का इस्तेमाल शुरू करने के लिए कृपया साइडबार में पासवर्ड दर्ज करें।")
    st.stop()

# --- जेमिनी एआई की तिजोरी ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY", None)
if not gemini_api_key:
    gemini_api_key = st.sidebar.text_input("Gemini API Key डालें:", type="password", key="gemini_lock_key")

# --- पूँजी प्रबंधन सेटिंग्स ---
with st.sidebar:
    st.header("⚙️ कैपिटल मैनेजमेंट")
    capital = st.number_input("आपकी कुल ट्रेडिंग पूँजी (₹)", min_value=5000, value=50000, step=5000)
    risk_pct = st.slider("एक ट्रेड में रिस्क सीमा (%)", 0.25, 2.0, 0.5, 0.25)
    max_risk_inr = capital * (risk_pct / 100.0) # ₹250 मैक्सिमम लॉस लिमिट
    
    st.markdown("---")
    if st.button("🔒 ऐप को दोबारा लॉक करें"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- एडवांस 20+ हेवीवेट स्टॉक यूनिवर्स (No Penny Stocks like Yes Bank) ---
UNIVERSE = {
    'Reliance Industries': 'RELIANCE.NS', 'HDFC Bank': 'HDFCBANK.NS',
    'ICICI Bank': 'ICICIBANK.NS', 'State Bank of India': 'SBIN.NS',
    'Axis Bank': 'AXISBANK.NS', 'Kotak Mahindra Bank': 'KOTAKBANK.NS',
    'TCS': 'TCS.NS', 'Infosys': 'INFY.NS', 'Bharti Airtel': 'BHARTIARTL.NS',
    'Larsen & Toubro': 'LT.NS', 'ITC': 'ITC.NS', 'Hindustan Unilever': 'HINDUNILVR.NS',
    'Tata Motors': 'TATAMOTORS.NS', 'Mahindra & Mahindra': 'M&M.NS', 'Sun Pharma': 'SUNPHARMA.NS'
}

# --- मैक्रो इंडेक्स डेटा इंजन ---
@st.cache_data(ttl=120, show_spinner=False)
def get_live_macro_pulses():
    pulses = {"NIFTY": "MIXED", "BANKNIFTY": "MIXED"}
    try:
        for symbol, key in [("^NSEI", "NIFTY"), ("^NSEBANK", "BANKNIFTY")]:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="50d")
            if not df.empty and len(df) >= 50:
                closes = df['Close']
                pulses[key] = "UPTREND" if closes.iloc[-1] > closes.rolling(20).mean().iloc[-1] > closes.rolling(50).mean().iloc[-1] else "DOWNTREND"
    except Exception:
        pass
    return pulses

def get_clean_history(ticker_sym):
    try:
        df = yf.download(ticker_sym, period='6mo', interval='1d', progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return None

def analyze_gemini_sentiment(ticker_sym, api_key):
    if not api_key: return 0, "तकनीकी विश्लेषण केवल सक्रिय है (AI Key अनुपलब्ध)।"
    try:
        tk = yf.Ticker(ticker_sym)
        raw_news = tk.news[:3]
        if not raw_news: return 0, "कोई ताज़ा हेडलाइंस उपलब्ध नहीं हैं।"
        
        news_summary = "\n".join([f"- {n['title']}" for n in raw_news])
        client = genai.Client(api_key=api_key)
        prompt = f"तुम एक क्वांट ट्रेडर हो। इस न्यूज़ का विश्लेषण करो: {news_summary}। इस स्टॉक {ticker_sym} को -25 से +25 के बीच एक स्कोर दो। केवल इस फॉर्मेट में उत्तर दो: स्कोर|छोटा हिंदी विश्लेषण वाक्य।"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        score_txt, reason_txt = response.text.strip().split("|", 1)
        return int(score_txt.strip()), reason_txt.strip()
    except Exception:
        return 0, "एआई सेंटीमेंट सिंक अस्थायी रूप से बाधित।"

# --- लाइव स्क्रीन रेंडरिंग ---
st.subheader("📊 लाइव इंस्टीट्यूशनल मैक्रो डैशबोर्ड")
macro_data = get_live_macro_pulses()

m1, m2, m3 = st.columns(3)
n_delta = "↓ सतर्क रहें (मंदी)" if macro_data["NIFTY"] == "DOWNTREND" else "↑ अनुकूल (तेजी)"
m1.metric("Nifty 50 मुख्य दिशा", macro_data["NIFTY"], delta=n_delta, delta_color="inverse" if macro_data["NIFTY"] == "DOWNTREND" else "normal")

b_delta = "↓ दबाव में" if macro_data["BANKNIFTY"] == "DOWNTREND" else "↑ बैंकिंग सपोर्ट"
m2.metric("Bank Nifty गति", macro_data["BANKNIFTY"], delta=b_delta, delta_color="inverse" if macro_data["BANKNIFTY"] == "DOWNTREND" else "normal")

m3.info("💡 **सटीकता नियम:** बाजार मंदी में होने पर सिस्टम शॉर्ट-सेलिंग (SELL) सिग्नल्स को प्राथमिकता देता है ताकि गिरते बाजार से भी पक्का मुनाफा निकल सके।")

if "supreme_trades" not in st.session_state:
    st.session_state["supreme_trades"] = None

st.markdown("---")
if st.button("🔎 पूरे बाजार का महा-स्कैन शुरू करें (High-Accuracy Scan)", type="primary", use_container_width=True):
    with st.spinner("सभी 15 कंपनियों का डिलीवरी डेटा, ब्रेकआउट और जेमिनी एआई न्यूज़ स्कैन किया जा रही है..."):
        all_candidates = []
        
        for name, sym in UNIVERSE.items():
            data_df = get_clean_history(sym)
            if data_df is None or len(data_df) < 30: continue
            
            c_close = data_df['Close'].astype(float)
            c_high = data_df['High'].astype(float)
            c_low = data_df['Low'].astype(float)
            c_vol = data_df['Volume'].astype(float)
            
            last_price = float(c_close.iloc[-1])
            ma20 = float(c_close.rolling(20).mean().iloc[-1])
            ma50 = float(c_close.rolling(50).mean().iloc[-1])
            
            # आरएसआई सेफ्टी इंजन (Safe RSI)
            diffs = c_close.diff()
            gains = diffs.clip(lower=0).rolling(14).mean()
            losses = (-diffs.clip(upper=0)).rolling(14).mean()
            l_loss = losses.iloc[-1]
            l_gain = gains.iloc[-1]
            rsi = 100.0 if l_loss == 0 or np.isnan(l_loss) else float(100 - (100 / (1 + (l_gain / l_loss))))
            
            # वॉल्यूम शॉक इंडेक्स
            v20_avg = float(c_vol.rolling(20).mean().iloc[-1])
            v_surge = float(c_vol.iloc[-1] / v20_avg) if v20_avg > 0 else 1.0
            
            # 20D ब्रेकआउट इंडिकेटर
            h20 = float(c_high.iloc[-21:-1].max())
            l20 = float(c_low.iloc[-21:-1].min())
            
            brk_alert = "NORMAL ZONE"
            brk_bonus = 0
            if last_price > h20:
                brk_alert = "💥 20D HIGH BREAKOUT"
                brk_bonus = 10
            elif last_price < l20:
                brk_alert = "⚠️ 20D LOW BREAKDOWN"
                brk_bonus = 5
                
            # एआई स्कोरर
            ai_score, ai_verdict = analyze_gemini_sentiment(sym, gemini_api_key)
            
            # क्वांटिटेटिव सटीकता स्कोरिंग मैट्रिक्स (Scoring Matrix)
            final_accuracy = 60
            if last_price > ma20 > ma50: final_accuracy += 15
            elif last_price < ma20 < ma50: final_accuracy -= 15
            if v_surge >= 1.5: final_accuracy += 10
            if 50 <= rsi <= 65: final_accuracy += 10
            final_accuracy += (ai_score + brk_bonus)
            final_accuracy = max(5, min(final_accuracy, 99.5))
            
            # रिस्क लेवल्स (ATR)
            tr_range = pd.concat([(c_high-c_low), (c_high-c_close.shift()).abs(), (c_low-c_close.shift()).abs()], axis=1).max(axis=1)
            atr_val = float(tr_range.rolling(14).mean().iloc[-1])
            
            trade_direction = "BUY"
            stop_loss = last_price - (1.6 * atr_val)
            target = last_price + (2.5 * atr_val)
            
            if macro_data["NIFTY"] == "DOWNTREND" and last_price < ma20:
                trade_direction = "SELL (Short)"
                stop_loss = last_price + (1.6 * atr_val)
                target = last_price - (2.5 * atr_val)
                final_accuracy += 5
                
            share_risk = abs(last_price - stop_loss)
            order_qty = int(max_risk_inr // share_risk) if share_risk > 0 else 0
            order_qty = min(order_qty, int(capital // last_price))
            
            # क्लीन डिक्शनरी मैपिंग (No Tuple Indexing Errors)
            stock_record = {
                "name": name, "ticker": sym, "direction": trade_direction,
                "score": round(final_accuracy, 1), "price": round(last_price, 2),
                "target": round(target, 2), "stop": round(stop_loss, 2), "qty": order_qty,
                "volume": round(v_surge, 2), "rsi": round(rsi, 1), "alert": brk_alert, "reason": ai_verdict
            }
            all_candidates.append(stock_record)
            
        st.session_state["supreme_trades"] = sorted(all_candidates, key=lambda x: x['score'], reverse=True)[:3]

# --- डिस्प्ले स्क्रीन इंजन (100% साफ और अलग-अलग बक्से) ---
if st.session_state["supreme_trades"]:
    for index, setup in enumerate(st.session_state["supreme_trades"], 1):
        with st.container(border=True):
            # स्क्रीन को तीन साफ अलग हिस्सों में बांटना
            left_col, center_col, right_col = st.columns([1, 1.5, 0.8])
            
            with left_col:
                st.subheader(f"🏆 रैंक 0{index}")
                st.markdown(f"### **{setup['name']}**")
                st.caption(f"सिंबल: {setup['ticker']}")
                
                # अलर्ट नोटिफिकेशन बैज (Notification Badge)
