import streamlit as st
import pandas as pd
import numpy as np
import time
from google import genai
# 100% लाइव क्लाउड-फ्रेंडली nsepythonserver का इम्पोर्ट
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

# --- 25+ मल्टी-सेक्टर स्टॉक यूनिवर्स ---
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
        ltp = float(nse_quote_ltp(ticker_sym))
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

if st.button("🔄 लाइव मार्केट डेटा रिफ्रेश करें"):
    st.rerun()

all_intraday_trades = []

with st.spinner("सभी सेक्टर्स का लाइव वॉल्यूम और मोमेंटम स्कैन किया जा रहा है..."):
    for sector, stocks in SECTOR_UNIVERSE.items():
        for name, sym in stocks.items():
            market_data = fetch_live_market_data(sym)
            if market_data is None:
                continue
            
            last_price = float(market_data["last_price"])
            open_price = float(market_data["open_price"])
            
            if open_price == 0:
                continue
                
            price_change_pct = float(((last_price - open_price) / open_price) * 100)
            
            signal = "NO SIGNAL"
            stop_loss = 0.0
            target = 0.0
            score = 0.0
            
            if last_price > open_price and price_change_pct > 0.4:
                signal = "📈 BUY (Long)"
                stop_loss = float(last_price - (last_price * 0.007)) 
                target = float(last_price + (last_price * 0.015))    
                score = float(price_change_pct * 1.5) 
            elif last_price < open_price and price_change_pct < -0.4:
                signal = "📉 SELL (Short)"
                stop_loss = float(last_price + (last_price * 0.007))
                target = float(last_price - (last_price * 0.015))
                score = float(abs(price_change_pct) * 1.5)

            if signal != "NO SIGNAL":
                per_share_risk =
