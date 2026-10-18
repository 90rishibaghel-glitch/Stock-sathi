import streamlit as st
import pandas as pd
import numpy as np
import time
from google import genai
# yfinance को पूरी तरह हटाकर 100% लाइव क्लाउड-फ्रेंडली nsepythonserver इम्पोर्ट किया गया है
from nsepythonserver import nse_quote_ltp, nse_quote

# 1. पेज सेटअप (इंट्राडे स्पेशल डार्क थीम और वाइड लेआउट)
st.set_page_config(page_title="AI Intraday Scalper v2", page_icon="⚡", layout="wide")

st.title("⚡ AI Intraday Scalper & Sector Scanner (v2 - LIVE)")
st.caption("लाइव टिक-बाय-टिक मोमेंटम स्कैनर | नो-डिली डेटा फीड | जेमिनी एआई सिग्नल्स")

# --- जेमिनी एआई की सेटिंग्स (Secrets से की उठाना) ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- इंट्राडे रिस्क मैनेजमेंट ---
st.sidebar.header("💰 इंट्राडे रिस्क मैनेजमेंट")
capital = st.sidebar.number_input("आपकी ट्रेडिंग पूँजी (₹)", min_value=2000, value=25000, step=1000)
risk_per_trade = st.sidebar.slider("एक ट्रेड में अधिकतम रिस्क (₹)", 100, 2000, 500, 50)

# --- 25+ मल्टी-सेक्टर स्टॉक यूनिवर्स (Yahoo Finance ".NS" हटा दिया गया है) ---
SECTOR_UNIVERSE = {
    "🏦 BANKING & FINANCE": {
        "HDFC Bank": "HDFCBANK", "ICICI Bank": "ICICIBANK", 
        "State Bank of India": "SBIN", "Axis Bank": "AXISBANK", "Kotak Bank": "KOTAKBANK"
    },
    "💻 IT SECTOR": {
        "TCS": "TCS", "Infosys": "INFY", 
        "Wipro": "WIPRO", "HCL Tech": "HCLTECH", "Tech Mahindra": "TECHM"
    },
    "🛢️ OILS & ENERGY": {
        "Reliance Industries": "RELIANCE", "ONGC": "ONGC", 
        "NTPC": "NTPC", "Power Grid": "POWERGRID", "Adani Green": "ADANIGREEN"
    },
    "🚗 AUTOMOBILES": {
        "Tata Motors": "TATAMOTORS", "Mahindra & Mahindra": "M&M", 
        "Maruti Suzuki": "MARUTI", "Bajaj Auto": "BAJAJ-AUTO", "Eicher Motors": "EICHERMOT"
    },
    "🛒 CONSUMER GOODS & OTHERS": {
        "ITC": "ITC", "Hindustan Unilever": "HINDUNILVR", 
        "Bharti Airtel": "BHARTIARTL", "Larsen & Toubro": "LT", "Sun Pharma": "SUNPHARMA"
    }
}

# --- 100% लाइव डेटा फेचिंग इंजन (NSE लाइव फीड) ---
def fetch_live_market_data(ticker_sym):
    try:
        # लाइव भाव (Last Traded Price) सीधे NSE से
        ltp = float(nse_quote_ltp(ticker_sym))
        
        # आज का प्राइसबैंड और ओपन/हाई/लो डेटा निकालना (नया nse_quote स्ट्रक्चर)
        meta_data = nse_quote(ticker_sym, "priceInfo")
        open_price = float(meta_data['open'])
        high_price = float(meta_data['intraDayHighLow']['max'])
        low_price = float(meta_data['intraDayHighLow']['min'])
        
        return {
            "last_price": ltp,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price
        }
    except:
        return None

# --- जेमिनी AI न्यूज़ सेंटीमेंट विश्लेषण ---
def get_ai_intraday_verdict(ticker_sym, api_key):
    if not api_key:
        return "AI न्यूज़ स्कैनर बंद है (Secrets में Key जांचें)"
    try:
        client = genai.Client(api_key=api_key)
        prompt = (f"तुम एक एक्सपर्ट डे-ट्रेडर हो। स्टॉक {ticker_sym} आज लाइव मार्केट में ब्रेकआउट दे रहा है। "
                  f"इस स्टॉक के टेक्निकल स्ट्रक्चर को ध्यान में रखते हुए इंट्राडे ट्रेडिंग के लिए "
                  f"सटीक गाइडलाइन सिर्फ 1 या 2 छोटे वाक्यों में हिंदी में दो।")
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except:
        return "एआई विश्लेषण वर्तमान में तकनीकी कारणों से उपलब्ध नहीं है।"

# --- लाइव डैशबोर्ड मुख्य भाग ---
st.subheader("📊 रीयल-टाइम इंट्राडे सेलेक्टर (100% सटीक लाइव डेटा आधारित)")

if st.button("🔄 लाइव特色 मार्केट डेटा रिफ्रेश करें"):
    st.rerun()

all_intraday_trades = []

with st.spinner("सभी सेक्टर्स का लाइव वॉल्यूम और मोमेंटम स्कैन किया जा रहा है..."):
    for sector, stocks in SECTOR_UNIVERSE.items():
        for name, sym in stocks.items():
            market_data = fetch_live_market_data(sym)
            if market_data is None:
                continue
            
            last_price = market_data["last_price"]
            open_price = market_data["open_price"]
            
            # लाइव चेंज% की गणना
            price_change_pct = ((last_price - open_price) / open_price) * 100
            
            signal = "NO SIGNAL"
            stop_loss = 0.0
            target = 0.0
            score = 0.0
            
            # मजबूत ब्रेकआउट गणना (Float सुरक्षित और सटीक टाइपकास्टिंग)
            if last_price > open_price and price_change_pct > 0.4:
                signal = "📈 BUY (Long)"
                stop_loss = float(last_price - (last_price * 0.007)) 
                target = float(last_price + (last_price * 0.015))    
                score = float(price_change_pct * 1.5) # मोमेंटम स्कोर
            elif last_price < open_price and price_change_pct < -0.4:
                signal = "📉 SELL (Short)"
                stop_loss = float(last_price + (last_price * 0.007))
                target = float(last_price - (last_price * 0.015))
                score = float(abs(price_change_pct) * 1.5)

            if signal != "NO SIGNAL":
                per_share_risk = abs(last_price - stop_loss)
                qty = int(risk_per_trade // per_share_risk) if per_share_risk > 0 else 0
                max_qty_allowed = int((capital * 5) // last_price) # 5x लेवरेज
                final_qty = min(qty, max_qty_allowed)
                
                all_intraday_trades.append({
                    "sector": sector, "name": name, "price": round(last_price, 2),
                    "change": round(price_change_pct, 2), "signal": signal,
                    "target": round(target, 2), "sl": round(stop_loss, 2),
                    "qty": final_qty, "score": score, "sym": sym
                })

# सबसे हाई-स्कोर वाले लाइव स्टॉक्स को शॉर्टलिस्ट करना
sorted_trades = sorted(all_intraday_trades, key=lambda x: x['score'], reverse=True)

if sorted_trades:
    top_trade = sorted_trades[0]
    
    st.success("🔥 लाइव एनएसई (NSE) डेटा के आधार पर आज का टॉप प्रायोरिटी स्टॉक मिल गया है!")
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
            
            with st.spinner("जेमिनी एआई लाइव सिचुएशन का विश्लेषण कर रहा है..."):
                ai_verdict = get_ai_intraday_verdict(top_trade['sym'], gemini_api_key)
            st.info(f"🤖 **एआई (AI) एक्सपर्ट राय:** {ai_verdict}")

else:
    st.info("💡 अभी मार्केट में किसी भी बड़े स्टॉक में कोई मजबूत ब्रेकआउट या विश्वसनीय सिग्नल नहीं बना है। लाइव मार्केट (9:15 AM - 3:30 PM) के दौरान 'लाइव मार्केट डेटा रिफ्रेश करें' बटन दबाएं।")
