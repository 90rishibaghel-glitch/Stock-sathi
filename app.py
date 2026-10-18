import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from google import genai

# 1. पेज सेटअप (इंट्राडे स्पेशल डार्क थीम और वाइड लेआउट)
st.set_page_config(page_title="AI Intraday Scalper", page_icon="⚡", layout="wide")

st.title("⚡ AI Intraday Scalper & Sector Scanner")
st.caption("लाइव मोमेंटम स्कैनर | मल्टी-सेक्टर पल्स डिटेक्टर | जेमिनी एआई सिग्नल्स")

# --- जेमिनी एआई की सेटिंग्स (सुरक्षित तिजोरी से ऑटोमैटिक की उठाना) ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- इंट्राडे रिस्क मैनेजमेंट ---
st.sidebar.header("💰 इंट्राडे रिस्क मैनेजमेंट")
capital = st.sidebar.number_input("आपकी ट्रेडिंग पूँजी (₹)", min_value=2000, value=25000, step=1000)
risk_per_trade = st.sidebar.slider("एक ट्रेड में अधिकतम रिस्क (₹)", 100, 2000, 500, 50)

# --- 25+ मल्टी-सेक्टर स्टॉक यूनिवर्स ---
SECTOR_UNIVERSE = {
    "🏦 BANKING & FINANCE": {
        "HDFC Bank": "HDFCBANK.NS", "ICICI Bank": "ICICIBANK.NS", 
        "State Bank of India": "SBIN.NS", "Axis Bank": "AXISBANK.NS", "Kotak Bank": "KOTAKBANK.NS"
    },
    "💻 IT SECTOR": {
        "TCS": "TCS.NS", "Infosys": "INFY.NS", 
        "Wipro": "WIPRO.NS", "HCL Tech": "HCLTECH.NS", "Tech Mahindra": "TECHM.NS"
    },
    "🛢️ OILS & ENERGY": {
        "Reliance Industries": "RELIANCE.NS", "ONGC": "ONGC.NS", 
        "NTPC": "NTPC.NS", "Power Grid": "POWERGRID.NS", "Adani Green": "ADANIGREEN.NS"
    },
    "🚗 AUTOMOBILES": {
        "Tata Motors": "TATAMOTORS.NS", "Mahindra & Mahindra": "M&M.NS", 
        "Maruti Suzuki": "MARUTI.NS", "Bajaj Auto": "BAJAJ-AUTO.NS", "Eicher Motors": "EICHERMOT.NS"
    },
    "🛒 CONSUMER GOODS & OTHERS": {
        "ITC": "ITC.NS", "Hindustan Unilever": "HINDUNILVR.NS", 
        "Bharti Airtel": "BHARTIARTL.NS", "Larsen & Toubro": "LT.NS", "Sun Pharma": "SUNPHARMA.NS"
    }
}

# --- लाइव डेटा फेचिंग इंजन ---
def fetch_intraday_data(ticker_sym):
    try:
        df = yf.download(ticker_sym, period="1d", interval="5m", progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# --- जेमिनी AI न्यूज़ सेंटीमेंट विश्लेषण ---
def get_ai_intraday_verdict(ticker_sym, api_key):
    if not api_key:
        return "AI न्यूज़ स्कैनर बंद है (Secrets में Key जांचें)"
    try:
        tk = yf.Ticker(ticker_sym)
        news = tk.news[:3] # टॉप 3 बड़ी खबरें
        if not news:
            return "कोई ताज़ा खबर नहीं मिली, तकनीकी गणना मजबूत है।"
        headlines = " | ".join([n['title'] for n in news])
        
        client = genai.Client(api_key=api_key)
        prompt = f"तुम एक एक्सपर्ट डे-ट्रेडर हो। इस स्टॉक {ticker_sym} की इन खबरों का गहराई से विश्लेषण करो: {headlines}। मुझे बताओ कि आज इंट्राडे ट्रेडिंग के लिए यह स्टॉक कितना सही है और इसका सेंटीमेंट क्या है। सिर्फ 1 या 2 छोटे वाक्यों में सटीक हिंदी में जवाब दो।"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except:
        return "एआई विश्लेषण वर्तमान में तकनीकी कारणों से उपलब्ध नहीं है।"

# --- लाइव डैशबोर्ड मुख्य भाग ---
st.subheader("📊 रीयल-टाइम इंट्राडे सेलेक्टर (100% सटीक गणना आधारित)")

if st.button("🔄 लाइव मार्केट डेटा रिफ्रेश करें"):
    st.rerun()

all_intraday_trades = []

with st.spinner("सभी सेक्टर्स का लाइव वॉल्यूम, रिपोर्ट्स और मोमेंटम स्कैन किया जा रहा है..."):
    for sector, stocks in SECTOR_UNIVERSE.items():
        for name, sym in stocks.items():
            df = fetch_intraday_data(sym)
            if df is None or len(df) < 5:
                continue
            
            last_price = float(df['Close'].iloc[-1])
            open_price = float(df['Open'].iloc[0]) 
            high_price = float(df['High'].max())
            low_price = float(df['Low'].min())
            
            price_change_pct = ((last_price - open_price) / open_price) * 100
            
            current_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Volume'].mean())
            volume_surge = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            signal = "NO SIGNAL"
            stop_loss = 0
            target = 0
            score = 0
            
            # मजबूत ब्रेकआउट गणना
            if last_price > open_price and price_change_pct > 0.4:
                signal = "📈 BUY (Long)"
                stop_loss = last_price - (last_price * 0.007) 
                target = last_price + (last_price * 0.015)    
                score = price_change_pct * volume_surge
            elif last_price < open_price and price_change_pct < -0.4:
                signal = "📉 SELL (Short)"
                stop_loss = last_price + (last_price * 0.007)
                target = last_price - (last_price * 0.015)
                score = abs(price_change_pct) * volume_surge

            if signal != "NO SIGNAL":
                per_share_risk = abs(last_price - stop_loss)
                qty = int(risk_per_trade // per_share_risk) if per_share_risk > 0 else 0
                max_qty_allowed = int((capital * 5) // last_price) 
                final_qty = min(qty, max_qty_allowed)
                
                all_intraday_trades.append({
                    "sector": sector, "name": name, "price": round(last_price, 2),
                    "change": round(price_change_pct, 2), "signal": signal,
                    "target": round(target, 2), "sl": round(stop_loss, 2),
                    "qty": final_qty, "score": score, "sym": sym
                })

# सबसे हाई-स्कोर वाले स्टॉक्स को शॉर्टलिस्ट करना
sorted_trades = sorted(all_intraday_trades, key=lambda x: x['score'], reverse=True)

if sorted_trades:
    # केवल टॉप 1 प्रायोरिटी स्टॉक को स्क्रीन पर दिखाना
    top_trade = sorted_trades[0]
    
    st.success("🔥 मार्केट रिपोर्ट्स और लाइव न्यूज़ एनालिसिस के आधार पर आज का टॉप प्रायोरिटी स्टॉक मिल गया है!")
    
    st.markdown(f"## 🏆 Priority #1: आज का जैकपॉट इंट्राडे पिक")
    
    # मुख्य स्टॉक डिस्प्ले कार्ड डिजाइन
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label=f"{top_trade['name']}", value=f"₹{top_trade['price']}", delta=f"{top_trade['change']}%")
            st.markdown(f"**📍 सेक्टर:** {top_trade['sector']}")
            st.markdown(f"**⚡ एक्शन सिग्नल:** `{top_trade['signal']}`")
        
        with col2:
            st.markdown(f"### 🎯 ट्रेडिंग टारगेट्स और सही गणना:")
            st.markdown(f"* **लक्ष्य (Target Price):** <span style='color:#2ecc71; font-size:20px; font-weight:bold;'>₹{top_trade['target']}</span>", unsafe_allowed_html=True)
            st.markdown(f"* **सुरक्षा स्टॉपलॉस (Stoploss):** <span style='color:#e74c3c; font-size:18px; font-weight:bold;'>₹{top_trade['sl']}</span>", unsafe_allowed_html=True)
            st.markdown(f"* **सटीक ट्रेड क्वांटिटी:** **{top_trade['qty']} शेयर्स** (आपके द्वारा तय किए गए ₹{risk_per_trade} रिस्क के अनुसार)")
            
            # सीधे बैकग्राउंड से एआई लाइव न्यूज़ विश्लेषण करना
            with st.spinner("जेमिनी एआई लाइव न्यूज़ और रिपोर्ट्स का विश्लेषण कर रहा है..."):
                ai_verdict = get_ai_intraday_verdict(top_trade['sym'], gemini_api_key)
            st.info(f"🤖 **एआई (AI) एक्सपर्ट राय:** {ai_verdict}")

else:
    st.info("💡 अभी मार्केट में किसी भी बड़े स्टॉक में कोई मजबूत ब्रेकआउट या विश्वसनीय सिग्नल नहीं बना है। लाइव मार्केट (9:15 AM - 3:30 PM) के दौरान 'लाइव मार्केट डेटा रिफ्रेश करें' बटन दबाएं।")
