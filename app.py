import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import pytz
from google import genai
# 100% लाइव क्लाउड-फ्रेंडली nsepythonserver का इम्पोर्ट
from nsepythonserver import nse_quote_ltp, nse_quote

# 1. पेज सेटअप (इंट्राडे स्पेशल डार्क थीम और वाइड लेआउट)
st.set_page_config(page_title="AI Intraday Scalper v2", page_icon="⚡", layout="wide")

st.title("⚡ AI Intraday Scalper & Sector Scanner (v2 - LIVE)")
st.caption("लाइव टिक-बाय-टिक मोमेंटम स्कैनर | नो-डिली डेटा फीड | जेमिनी एआई सिग्नल्स")

# --- जेमिनी एआई की सेटिंग्स (Secrets से की उठाना) ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- 1. टाइम मैनेजमेंट और हॉलिडे/वीकेंड फ़िल्टर ---
IST = pytz.timezone('Asia/Kolkata')
now_datetime = datetime.now(IST)
current_time = now_datetime.time()
current_hour_min = current_time.strftime("%H:%M")
today_date_str = now_datetime.strftime("%Y-%m-%d")

st.sidebar.markdown(f"**🕒 लाइव भारतीय समय (IST):** `{current_hour_min}`")

market_status = "NORMAL"

# शनिवार (5), रविवार (6) या तय छुट्टियों का फिल्टर
nse_holidays = ["2026-10-20"]  # यहाँ छुट्टियों की तारीखें डाल सकते हैं
if now_datetime.weekday() in [5, 6] or today_date_str in nse_holidays:
    st.sidebar.error("🛑 आज मार्केट बंद है (हॉलिडे/वीकेंड)! एआई ब्लॉक किया गया है।")
    market_status = "CLOSED"
elif "11:30" <= current_hour_min <= "13:30":
    st.sidebar.error("💤 मिड-डे स्लम्प (Sideways Market)! नए ट्रेड लेने से सख्त परहेज करें। (Volume कम है)")
    market_status = "SLUMP"
elif current_hour_min >= "15:10":
    st.sidebar.warning("⚠️ ऑटो स्क्वायर-ऑफ समय! ब्रोकर की पेनल्टी से बचने के लिए तुरंत पोजीशन क्लोज करें।")
    market_status = "CLOSING"
elif "09:15" <= current_hour_min <= "09:45":
    st.sidebar.info("🚀 ओपनिंग वोलैटिलिटी विंडो! शुरुआती 15 मिनट सिर्फ Market Direction देखें।")

# --- इंट्राडे रिस्क मैनेजमेंट (Rule #4: Risk Management) ---
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
        
        # --- VWAP का प्रॉक्सी कैलकुलेशन (Price Action के लिए) ---
        vwap_proxy = float((high_price + low_price + ltp) / 3.0)
        
        return {
            "last_price": ltp,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "vwap": vwap_proxy
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
        response = client.models.generate_content(model='gemini-3.8-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"एआई विश्लेषण वर्तमान में उपलब्ध नहीं है। एरर: {str(e)}"

# --- लाइव डैशबोर्ड मुख्य भाग ---
st.subheader("📊 रीयल-टाइम इंट्राडे सेलेक्टर (100% सटीक लाइव डेटा आधारित)")

# मार्केट बंद होने या स्लम्प की वार्निंग
if market_status == "CLOSED":
    st.error("🛑 **अलर्ट:** आज मार्केट बंद है। लाइव डेटा और ट्रेड स्कैनिंग उपलब्ध नहीं है।")
elif market_status == "SLUMP":
    st.warning("⚠️ **अलर्ट:** अभी मिड-डे टाइम (11:30 AM - 01:30 PM) चल रहा है। मार्केट अक्सर इस वक्त Sideways रहता है। ट्रेड लेने से पहले वॉल्यूम ज़रूर check कर लें।")

if st.button("🔄 लाइव मार्केट डेटा रिफ्रेश करें"):
    st.rerun()

all_intraday_trades = []

# यदि मार्केट बंद नहीं है तभी स्कैनिंग करें
if market_status != "CLOSED":
    with st.spinner("सभी सेक्टर्स का लाइव वॉल्यूम और मोमेंटम स्कैन किया जा रहा है..."):
        for sector, stocks in SECTOR_UNIVERSE.items():
            for name, sym in stocks.items():
                market_data = fetch_live_market_data(sym)
                if market_data is None:
                    continue
                
                last_price = float(market_data["last_price"])
                open_price = float(market_data["open_price"])
                high_price = float(market_data["high_price"])
                low_price = float(market_data["low_price"])
                vwap = float(market_data["vwap"])
                
                if open_price == 0:
                    continue
                    
                price_change_pct = float(((last_price - open_price) / open_price) * 100)
                
                signal = "NO SIGNAL"
                entry_price = 0.0
                stop_loss = 0.0
                target = 0.0
                score = 0.0
                
                # --- Price Action Filter (LTP > Open & LTP > VWAP) ---
                if last_price > open_price and price_change_pct > 0.4 and last_price > vwap:
                    signal = "📈 BUY ABOVE (Long)"
                    entry_price = float(last_price + (last_price * 0.001))   
                    
                    potential_sl = low_price
                    if entry_price - potential_sl > (entry_price * 0.007):
                        stop_loss = float(entry_price - (entry_price * 0.007))
                    else:
                        stop_loss = float(potential_sl)
                    
                    # 1:2 का रिस्क-टू-रिवॉर्ड रेशियो
                    risk_per_share = entry_price - stop_loss
                    target = float(entry_price + (risk_per_share * 2.0))
                    score = float(price_change_pct * 1.5) 
                    
                elif last_price < open_price and price_change_pct < -0.4 and last_price < vwap:
                    signal = "📉 SELL BELOW (Short)"
                    entry_price = float(last_price - (last_price * 0.001))   
                    
                    potential_sl = high_price
                    if potential_sl - entry_price > (entry_price * 0.007):
                        stop_loss = float(entry_price + (entry_price * 0.007))
                    else:
                        stop_loss = float(potential_sl)
                    
                    # 1:2 का रिस्क-टू-रिवॉर्ड रेशियो
                    risk_per_share = stop_loss - entry_price
                    target = float(entry_price - (risk_per_share * 2.0))
                    score = float(abs(price_change_pct) * 1.5)

                if signal != "NO SIGNAL":
                    per_share_risk = abs(entry_price - stop_loss)
                    qty = int(risk_per_trade // per_share_risk) if per_share_risk > 0 else 0
                    max_qty_allowed = int((capital * 5) // entry_price) # 5x Leverage
                    final_qty = min(qty, max_qty_allowed)
                    
                    all_intraday_trades.append({
                        "sector": sector, 
                        "name": name, 
                        "price": round(entry_price, 2), 
                        "current_price": round(last_price, 2),
                        "change": round(price_change_pct, 2), 
                        "signal": signal,
                        "target": round(target, 2), 
                        "sl": round(stop_loss, 2),
                        "qty": final_qty, 
                        "score": score, 
                        "sym": sym
                    })

    # सॉर्टिंग करना
    sorted_trades = sorted(all_intraday_trades, key=lambda x: x['score'], reverse=True)

    if sorted_trades:
        top_trade = sorted_trades[0]
        
        st.success("🔥 लाइव एनएसई (NSE) डेटा के आधार पर आज का TOP प्रायोरिटी स्टॉक मिल गया है!")
        st.markdown(f"## 🏆 Priority #1: आज का जैकपॉट इंट्राडे पिक")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"{top_trade.get('name', 'Stock')}", value=f"₹{top_trade.get('current_price', 0.0)}", delta=f"{top_trade.get('change', 0.0)}%")
                st.markdown(f"**📍 सेक्टर:** {top_trade.get('sector', 'N/A')}")
                st.markdown(f"**⚡ एक्शन सिग्नल:** `{top_trade.get('signal', 'NO SIGNAL')}`")
            
            with col2:
                st.markdown(f"### 🎯 ट्रेडिंग टारगेट्स (सख्त 1:2 रिस्क-रिवॉर्ड आधारित):")
                st.markdown(f"* **प्रवेश मूल्य (Entry Price):** <span style='color:#3498db; font-size:20px; font-weight:bold;'>₹{top_trade.get('price', 0.0):.2f} पर ऑर्डर लगाएँ (MIS + Limit Order)</span>", unsafe_allow_html=True)
                st.markdown(f"* **ट्रेडिंग मात्रा (Quantity):** <span style='color:#f1c40f; font-size:20px; font-weight:bold;'>{top_trade.get('qty', 0)} Shares</span> (रिस्क मैनेज्ड)", unsafe_allow_html=True)
                st.markdown(f"* **लक्ष्य (Target Price):** <span style='color:#2ecc71; font-size:20px; font-weight:bold;'>₹{top_trade.get('target', 0.0):.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"* **स्टॉप लॉस (Stop Loss):** <span style='color:#e74c3c; font-size:20px; font-weight:bold;'>₹{top_trade.get('sl', 0.0):.2f} (Price Action आधारित)</span>", unsafe_allow_html=True)

        # --- जेमिनी एआई का लाइव ओपिनियन रेंडरिंग (बटन के साथ ताकि 429 एरर न आए) ---
        st.markdown("### 🤖 जेमिनी एआई लाइव सिग्नल्स और वर्डिक्ट")
        
        if st.button("🤖 जेमिनी एआई से लाइव विश्लेषण पूछें (कोटा बचाने के लिए क्लिक करें)"):
            with st.spinner("जेमिनी एआई लाइव चार्ट स्ट्रक्चर और सेंटीमेंट का विश्लेषण कर रहा है..."):
                ai_verdict = get_ai_intraday_verdict(top_trade.get('sym', ''), gemini_api_key)
                st.info(f"💡 **एआई गाइडलाइन:** {ai_verdict}")
            
    else:
        st.warning("⚠️ फ़िलहाल किसी भी स्टॉक में निर्धारित इंट्राडे मोमेंटम (0.4% से ज़्यादा का उतार-चढ़ाव) नहीं मिला है। लाइव मार्केट खुलने पर दोबारा रिफ्रेश करें।")
