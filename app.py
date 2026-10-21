import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import pytz
from google import genai
import holidays  
from nsepythonserver import nse_quote_ltp, nse_quote
import json
import os
from concurrent.futures import ThreadPoolExecutor

# 1. Page Configuration
st.set_page_config(page_title="AI Live Nifty50 Scalper v5.1 Pro", page_icon="⚡", layout="wide")

st.title("⚡ AI Nifty 50 Real-Time Scalper & Scanner (v5.1 Pro - Locked Top 3)")
st.caption("100% लाइव डेटा इंजन (No yfinance Lag) | एनएसई डायरेक्ट फीड | फिक्सड टॉप 3 प्रायोरिटी + ऑन-डिमांड AI")

# --- Gemini AI Key from Streamlit Secrets ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- Time & Market Status Management ---
IST = pytz.timezone('Asia/Kolkata')
now_datetime = datetime.now(IST)
current_time = now_datetime.time()
current_hour_min = current_time.strftime("%H:%M")

st.sidebar.markdown(f"**🕒 लाइव भारतीय समय (IST):** `{current_hour_min}`")

market_status = "NORMAL"

# Safe Automatic Holiday Check
try:
    nse_official_holidays = holidays.financial.NSE()
except AttributeError:
    try:
        nse_official_holidays = holidays.country_holidays('IN')
    except:
        nse_official_holidays = {}

if now_datetime.date() in nse_official_holidays:
    st.sidebar.error("🛑 आज मार्केट बंद है (एनएससी राष्ट्रीय अवकाश)! एआई ब्लॉक किया गया है।")
    market_status = "CLOSED"

if market_status != "CLOSED":
    if now_datetime.weekday() in (5, 6):
        st.sidebar.error("🛑 आज वीकेंड (शनिवार/रविवार) है! लाइव मार्केट बंद है।")
        market_status = "CLOSED"

if market_status != "CLOSED":
    if current_hour_min < "09:15":
        st.sidebar.warning("💤 मार्केट अभी खुला नहीं है। प्री-ओपन सेशन का इंतज़ार करें।")
        market_status = "CLOSED"
    elif "11:30" <= current_hour_min <= "13:30":
        st.sidebar.error("💤 मिड-डे स्लम्प (Sideways Market)! नए ट्रेड लेने से सख्त परहेज करें।")
        market_status = "SLUMP"
    elif current_hour_min >= "15:10":
        st.sidebar.warning("⚠️ ऑटो स्क्वायर-ऑफ समय! तुरंत पोजीशन क्लोज करें।")
        market_status = "CLOSING"

# --- Capital Management Input ---
st.sidebar.header("💰 Capital Management")
capital = st.sidebar.number_input("आपकी ट्रेडिंग पूँजी (₹)", min_value=2000, value=25000, step=1000)

# --- Dynamic Nifty 50 Ticker List ---
NIFTY_50_TICKERS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", 
    "BAJFINANCE", "BAJAJFINSV", "BEL", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", 
    "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", 
    "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC", 
    "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", 
    "NTPC", "NESTLEIND", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", 
    "SUNPHARMA", "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM", 
    "TITAN", "ULTRACEMCO", "WIPRO", "ZOMATO"
]

# --- 100% Live NSE Data Engine ---
def process_single_stock_live(ticker):
    try:
        meta_data = nse_quote(ticker, "priceInfo")
        if not meta_data:
            return None
            
        ltp = float(meta_data.get('lastPrice', 0))
        open_price = float(meta_data.get('open', 0))
        high_price = float(meta_data.get('max', 0))
        low_price = float(meta_data.get('min', 0))
        prev_close = float(meta_data.get('previousClose', 0))
        vwap = float(meta_data.get('vwap', ltp))
        
        if ltp == 0 or open_price == 0:
            return None
            
        return {
            "sym": ticker,
            "last_price": ltp,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "vwap": vwap,
            "prev_close": prev_close
        }
    except Exception as e:
        return None

# --- Gemini Core Function with Quota Error Catching ---
def get_ai_intraday_verdict(ticker_sym, signal_type, price, target, sl, open_p, high_p, low_p, market_state, api_key):
    if not api_key: 
        return "⚠️ Gemini API Key सेट नहीं है।"
    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            f"तुम एक प्रोफेशनल लाइव एनएसई (NSE) रिस्क मैनेजर और प्रो-ट्रेडर हो।\n"
            f"स्टॉक: {ticker_sym}\n"
            f"लाइव सिग्नल: {signal_type}\n"
            f"आज का डेटा -> Open: {open_p}, High: {high_p}, Low: {low_p}, Current Price: {price}\n"
            f"सिस्टम आर्डर -> Entry: {price}, Target: {target}, StopLoss: {sl}\n"
            f"मार्केट टाइमिंग मोड: {market_state}\n\n"
            f"इस डेटा का एनालिसिस करो और ट्रेडर को हिंदी में सिर्फ 2 पॉइंट में जवाब दो:\n"
            f"1. क्या एंट्री पॉइंट सही है? टारगेट कितनी देर में (या किस समय तक) हिट हो सकता है?\n"
            f"2. लाइव एडवाइस: क्या पोजीशन बनाए रखें, या टारगेट छोटा/बड़ा करें, या स्टॉप-लॉस ट्रेल करें?"
        )
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            return "⚠️ **Google AI Quota Limit Exceeded (429):** आपके फ्री टियर की दैनिक सीमा समाप्त हो गई है। कृपया कल कोशिश करें या पेड प्लान देखें। आपके लेवल्स (Entry, Target, SL) पूरी तरह सुरक्षित हैं।"
        return f"एआई सर्वर कनेक्ट नहीं हो पाया: {err_str}"

# --- Frontend Rendering ---
st.subheader("📊 रीयल-टाइम Nifty 50 लाइव स्कैनर (No Lag - NSE Direct)")

if market_status == "CLOSED":
    st.error("🛑 **अलर्ट:** आज मार्केट बंद है। लाइव स्कैनिंग वर्किंग डेज पर सुबह 9:15 से दोपहर 3:30 के बीच ही काम करती है।")
elif market_status == "SLUMP":
    st.warning("⚠️ **अलर्ट:** अभी मिड-डे टाइम चल रहा है। वॉल्यूम कम हो सकता है।")

# Session State initialize करना ताकि स्टॉक बार-बार न बदलें
if 'top_3_locked' not in st.session_state:
    st.session_state.top_3_locked = None

if st.button("🔄 Nifty 50 लाइव स्कैन शुरू करें (नया स्कैन)"):
    all_intraday_trades = []
    if market_status != "CLOSED":
        results = []
        with st.spinner("Nifty 50 के सभी 50 स्टॉक्स का 100% लाइव डेटा NSE से निकाला जा रहा है..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(process_single_stock_live, NIFTY_50_TICKERS))
                
        for market_data in results:
            if market_data is None:
                continue
                
            sym = market_data["sym"]
            last_price = market_data["last_price"]
            open_price = market_data["open_price"]
            high_price = market_data["high_price"]
            low_price = market_data["low_price"]
            vwap = market_data["vwap"]
            prev_close = market_data["prev_close"]
            
            price_change_pct = float(((last_price - open_price) / open_price) * 100)
            
            signal = "NO SIGNAL"
            entry_price, stop_loss, target = 0.0, 0.0, 0.0
            
            score = float(abs(price_change_pct) * 3.0)

            if last_price > open_price and price_change_pct > 0.4 and last_price > vwap:
                signal = "📈 BUY ABOVE (Live Confirmed)"
                entry_price = float(last_price + (last_price * 0.0005))   
                stop_loss = float(vwap) if (entry_price - vwap < entry_price * 0.01) else float(entry_price - (entry_price * 0.006))
                risk_per_share = entry_price - stop_loss
                target = float(entry_price + (risk_per_share * 2.0))
                
            elif last_price < open_price and price_change_pct < -0.4 and last_price < vwap:
                signal = "📉 SELL BELOW (Live Confirmed)"
                entry_price = float(last_price - (last_price * 0.0005))   
                stop_loss = float(vwap) if (vwap - entry_price < entry_price * 0.01) else float(entry_price + (entry_price * 0.006))
                risk_per_share = stop_loss - entry_price
                target = float(entry_price - (risk_per_share * 2.0))

            if signal != "NO SIGNAL" and (entry_price - stop_loss) != 0:
                all_intraday_trades.append({
                    "sym": sym, "price": round(entry_price, 2), 
                    "current_price": round(last_price, 2), "change": round(price_change_pct, 2), 
                    "signal": signal, "target": round(target, 2), "sl": round(stop_loss, 2),
                    "score": score,
                    "open_price": open_price, "high_price": high_price, "low_price": low_price
                })

        sorted_trades = sorted(all_intraday_trades, key=lambda x: x['score'], reverse=True)
        # Top 3 स्टॉक्स को Session State में लॉक कर दिया गया है
        st.session_state.top_3_locked = sorted_trades[:3]

# --- Display Top 3 Locked Stocks (AI बटन या कैपिटल बदलने पर यह नहीं बदलेंगे) ---
if st.session_state.top_3_locked:
    st.success(f"🔥 टॉप 3 प्रायोरिटी स्टॉक लॉक हैं। आप बेझिझक AI बटन या कैपिटल बदल सकते हैं।")
    
    st.markdown("## 🏆 Top 3 High-Accuracy Priority Picks + On-Demand AI Mentor")
    
    top_3 = st.session_state.top_3_locked
    priority_titles = ["🥇 Priority #1 Pick", "🥈 Priority #2 Pick", "🥉 Priority #3 Pick"]
    
    for idx, trade in enumerate(top_3):
        # कैपिटल के आधार पर क्वांटिटी कैलकुलेशन
        per_share_risk = abs(trade['price'] - trade['sl'])
        max_qty_by_capital = int((capital * 5) // trade['price'])
        final_qty = max(1, max_qty_by_capital)

        total_trade_risk = round(per_share_risk * final_qty, 2)
        per_share_reward = abs(trade['target'] - trade['price'])
        total_potential_profit = round(per_share_reward * final_qty, 2)

        st.markdown(f"### {priority_titles[idx]}: {trade.get('sym')}")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"स्टॉक सिंबल: {trade.get('sym')}", value=f"₹{trade.get('current_price')}", delta=f"{trade.get('change')}%")
                st.markdown(f"**⚡ लाइव एक्शन:** `{trade.get('signal')}`")
                st.markdown(f"**📦 अनुशंसित मात्रा (Quantity):** `{final_qty} शेयर्स` (कैपिटल के आधार पर)")
                st.markdown(f"📉 **अनुमानित रिस्क:** ₹{total_trade_risk} | 🎯 **संभावित प्रॉफिट (1:2):** ₹{total_potential_profit}")
            
            with col2:
                st.markdown("### 🎯 लाइव ऑर्डर्स की जानकारी (1:2 रिस्क-रिवॉर्ड):")
                st.markdown(f"* **Entry Price Order:** <span style='color:#3498db; font-size:18px; font-weight:bold;'>₹{trade.get('price'):.2f}</span> (Limit Order लगाएँ)", unsafe_allow_html=True)
                st.markdown(f"* **Target Price (लक्ष्य):** <span style='color:#2ecc71; font-size:18px; font-weight:bold;'>₹{trade.get('target'):.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"* **Stop Loss (SL):** <span style='color:#e74c3c; font-size:18px; font-weight:bold;'>₹{trade.get('sl'):.2f}</span> (VWAP आधारित सुरक्षित SL)", unsafe_allow_html=True)

            # --- On-Demand AI Mentor Button ---
            st.markdown("---")
            ai_button_key = f"ai_btn_{trade.get('sym')}_{idx}"
            
            if st.button(f"🤖 {trade.get('sym')} का AI लाइव एनालिसिस प्राप्त करें", key=ai_button_key):
                with st.spinner(f"🤖 Gemini AI {trade.get('sym')} का लाइव एनालिसिस कर रहा है..."):
                    ai_verdict = get_ai_intraday_verdict(
                        ticker_sym=trade.get('sym'),
                        signal_type=trade.get('signal'),
                        price=trade.get('current_price'),
                        target=trade.get('target'),
                        sl=trade.get('sl'),
                        open_p=trade.get('open_price'),
                        high_p=trade.get('high_price'),
                        low_p=trade.get('low_price'),
                        market_state=market_status,
                        api_key=gemini_api_key
                    )
                st.info(f"💡 **AI लाइव ट्रेड मेंटॉर ({trade.get('sym')}):**\n\n{ai_verdict}")
else:
    st.info("ℹ️ कृपया ऊपर दिए गए **'🔄 Nifty 50 लाइव स्कैन शुरू करें'** बटन पर क्लिक करें ताकि टॉप 3 स्टॉक लोड हो सकें।")
