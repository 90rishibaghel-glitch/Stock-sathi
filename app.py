import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import pytz
from google import genai
import holidays  
import yfinance as yf
from nsepythonserver import nse_quote_ltp, nse_quote
import json
import os

# 1. Page Configuration
st.set_page_config(page_title="AI Multi-Timeframe Scalper v3", page_icon="⚡", layout="wide")

st.title("⚡ AI Multi-Timeframe Scalper & Sector Scanner (v3 - HIGH ACCURACY)")
st.caption("5Min + 15Min कंबाइंड कन्फर्मेशन इंजन | जेमिनी एआई सिग्नल्स & सेल्फ-लर्निंग मेमोरी")

# --- Gemini AI Key from Streamlit Secrets ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- Time & Market Status Management ---
IST = pytz.timezone('Asia/Kolkata')
now_datetime = datetime.now(IST)
current_time = now_datetime.time()
current_hour_min = current_time.strftime("%H:%M")

st.sidebar.markdown(f"**🕒 लाइव भारतीय समय (IST):** `{current_hour_min}`")

market_status = "NORMAL"

# Step A: Safe Automatic Holiday Check
try:
    nse_official_holidays = holidays.financial.NSE()
except AttributeError:
    try:
        nse_official_holidays = holidays.country_holidays('IN')
    except:
        nse_official_holidays = {}

if now_datetime.date() in nse_official_holidays:
    st.sidebar.error("🛑 आज मार्केट बंद है (एनएससी राष्ट्रीय अवकाश/हॉलिडे)! एआई ब्लॉक किया गया है।")
    market_status = "CLOSED"

# Step B: Weekend Check (Fixed syntax here)
if market_status != "CLOSED":
    # 5 = Saturday, 6 = Sunday
    if now_datetime.weekday() in (5, 6):
        st.sidebar.error("🛑 आज वीकेंड (शनिवार/रविवार) है! लाइव मार्केट बंद है।")
        market_status = "CLOSED"

# Step C: Intra-day Time Window Restraints
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

# --- Risk Management ---
st.sidebar.header("💰 इंट्राडे रिस्क मैनेजमेंट")
capital = st.sidebar.number_input("आपकी ट्रेडिंग पूँजी (₹)", min_value=2000, value=25000, step=1000)
risk_per_trade = st.sidebar.slider("एक ट्रेड में अधिकतम रिस्क (₹)", 100, 2000, 500, 50)

# --- Self-Learning Trade Memory ---
MEMORY_FILE = "trade_memory.json"
def load_trade_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_trade_memory(memory_data):
    try:
        with open(MEMORY_FILE, "w") as f: json.dump(memory_data, f)
    except: pass

trade_memory = load_trade_memory()

# --- 25 Stock Watchlist ---
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
        "NTPC": "NTPC", "Power Grid": "POWERGRID"
    },
    "🚗 AUTOMOBILES": {
        "Tata Motors": "TATAMOTORS", "Mahindra & Mahindra": "M_M", 
        "Maruti Suzuki": "MARUTI", "Bajaj Auto": "BAJAJ-AUTO"
    },
    "🛒 CONSUMER GOODS & OTHERS": {
        "ITC": "ITC", "Hindustan Unilever": "HINDUNILVR", 
        "Bharti Airtel": "BHARTIARTL", "Larsen & Toubro": "LT"
    }
}

# --- Upgraded Multi-Timeframe Data Engine ---
def fetch_multi_timeframe_data(ticker_sym):
    yf_sym = "M&M.NS" if ticker_sym == "M_M" else f"{ticker_sym}.NS"
    nse_sym = "M&M" if ticker_sym == "M_M" else ticker_sym
    
    try:
        ltp = float(nse_quote_ltp(nse_sym))
        time.sleep(0.1) 
        
        meta_data = nse_quote(nse_sym, "priceInfo")
        open_price = float(meta_data.get('open', ltp))
        
        stock_obj = yf.Ticker(yf_sym)
        df_5m = stock_obj.history(period="3d", interval="5m")
        df_15m = stock_obj.history(period="3d", interval="15m")
        
        if df_5m.empty or df_15m.empty:
            return None
            
        df_5m['ema9'] = df_5m['Close'].ewm(span=9, adjust=False).mean()
        last_ema9_5m = float(df_5m['ema9'].iloc[-1])
        
        df_15m['ema20'] = df_15m['Close'].ewm(span=20, adjust=False).mean()
        last_ema20_15m = float(df_15m['ema20'].iloc[-1])
        
        high_low_dict = meta_data.get('intraDayHighLow', {})
        high_price = float(high_low_dict.get('max', ltp))
        low_price = float(high_low_dict.get('min', ltp))
        
        vwap_proxy = float((high_price + low_price + ltp) / 3.0)
        
        return {
            "last_price": ltp,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "vwap": vwap_proxy,
            "ema9_5m": last_ema9_5m,
            "ema20_15m": last_ema20_15m
        }
    except:
        return None

# --- Gemini Core ---
def get_ai_intraday_verdict(ticker_sym, api_key):
    if not api_key: return "AI न्यूज़ स्कैनर बंद है।"
    try:
        client = genai.Client(api_key=api_key)
        prompt = (f"तुम एक एक्सपर्ट डे-ट्रेडर हो। स्टॉक {ticker_sym} आज 5Min और 15Min चार्ट पर डबल कन्फर्मेशन "
                  f"ब्रेकआउट दे रहा है। इसके लिए सख्त स्टॉपलॉस के साथ हिंदी में 1 सटीक ट्रेडिंग गाइडलाइन दो।")
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"एआई सर्वर कनेक्ट नहीं हो पाया: {str(e)}"

# --- Frontend Rendering ---
st.subheader("📊 रीयल-टाइम इंट्राडे सेलेक्टर (5Min + 15Min डबल कन्फर्मेशन)")

if market_status == "CLOSED":
    st.error("🛑 **अलर्ट:** आज मार्केट बंद है या डेटा फ़ीड उपलब्ध नहीं है। वीकेंड/हॉलिडे पर लाइव स्कैनिंग बंद रहती है।")
elif market_status == "SLUMP":
    st.warning("⚠️ **अलर्ट:** अभी मिड-डे टाइम चल रहा है। वॉल्यूम कम हो सकता है।")

if st.button("🔄 लाइव Market Data Refresh करें"):
    st.rerun()

all_intraday_trades = []

if market_status != "CLOSED":
    progress_bar = st.progress(0)
    total_stocks = sum(len(stocks) for stocks in SECTOR_UNIVERSE.values())
    processed_count = 0
    
    with st.spinner("सभी सेक्टर्स का 5Min + 15Min चार्ट स्कैन किया जा रहा है..."):
        for sector, stocks in SECTOR_UNIVERSE.items():
            for name, sym in stocks.items():
                processed_count += 1
                progress_bar.progress(processed_count / total_stocks)
                
                market_data = fetch_multi_timeframe_data(sym)
                if market_data is None:
                    continue
                
                last_price = market_data["last_price"]
                open_price = market_data["open_price"]
                high_price = market_data["high_price"]
                low_price = market_data["low_price"]
                vwap = market_data["vwap"]
                ema9_5m = market_data["ema9_5m"]
                ema20_15m = market_data["ema20_15m"]
                
                price_change_pct = float(((last_price - open_price) / open_price) * 100)
                
                signal = "NO SIGNAL"
                entry_price, stop_loss, target = 0.0, 0.0, 0.0
                score = float(price_change_pct * 1.5) 

                if sym in trade_memory and trade_memory[sym].get("penalty_count", 0) > 0:
                    score *= 0.5 

                # HIGH ACCURACY CRITERIA (5Min + 15Min Double Confirmation)
                if last_price > open_price and price_change_pct > 0.4 and last_price > vwap and last_price > ema9_5m and last_price > ema20_15m:
                    signal = "📈 BUY ABOVE (Double Confirmed)"
                    entry_price = float(last_price + (last_price * 0.001))   
                    potential_sl = min(low_price, ema9_5m)
                    stop_loss = float(entry_price - (entry_price * 0.007)) if (entry_price - potential_sl > (entry_price * 0.007)) else float(potential_sl)
                    risk_per_share = entry_price - stop_loss
                    target = float(entry_price + (risk_per_share * 2.0))
                    
                elif last_price < open_price and price_change_pct < -0.4 and last_price < vwap and last_price < ema9_5m and last_price < ema20_15m:
                    signal = "📉 SELL BELOW (Double Confirmed)"
                    entry_price = float(last_price - (last_price * 0.001))   
                    potential_sl = max(high_price, ema9_5m)
                    stop_loss = float(entry_price + (entry_price * 0.007)) if (potential_sl - entry_price > (entry_price * 0.007)) else float(potential_sl)
                    risk_per_share = stop_loss - entry_price
                    target = float(entry_price - (risk_per_share * 2.0))

                if signal != "NO SIGNAL":
                    per_share_risk = abs(entry_price - stop_loss)
                    qty = int(risk_per_trade // per_share_risk) if per_share_risk > 0 else 0
                    max_qty_allowed = int((capital * 5) // entry_price)
                    final_qty = min(qty, max_qty_allowed)
                    
                    all_intraday_trades.append({
                        "sector": sector, "name": name, "price": round(entry_price, 2), 
                        "current_price": round(last_price, 2), "change": round(price_change_pct, 2), 
                        "signal": signal, "target": round(target, 2), "sl": round(stop_loss, 2),
                        "qty": final_qty, "score": score, "sym": sym
                    })

    progress_bar.empty()

    sorted_trades = sorted(all_intraday_trades, key=lambda x: x['score'], reverse=True)

    if sorted_trades:
        top_trade = sorted_trades[0]
        st.toast(f"🚨 जैकपॉट पिक मिला: {top_trade.get('name')} ({top_trade.get('signal')})", icon="⚡")

        st.success("🔥 5Min + 15Min डबल कन्फर्मेशन के आधार पर आज का TOP प्रायोरिटी स्टॉक मिल गया है!")
        st.markdown(f"## 🏆 Priority #1: आज का हाई-एक्यूरेसी इंट्राडे पिक")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label=f"{top_trade.get('name')}", value=f"₹{top_trade.get('current_price')}", delta=f"{top_trade.get('change')}%")
                st.markdown(f"**📍 सेक्टर:** {top_trade.get('sector')}")
                st.markdown(f"**⚡ एक्शन सिग्नल:** `{top_trade.get('signal')}`")
                
                st.markdown("---")
                st.markdown("💡 **क्या पिछला सिग्नल फेल हुआ?** (एआई को सिखाने के लिए क्लिक करें):")
                if st.button(f"⚠️ इस स्टॉक ({top_trade.get('name')}) को ब्लैकलिस्ट/पेनल्टी दें"):
                    sym_key = top_trade.get('sym')
                    if sym_key not in trade_memory:
                        trade_memory[sym_key] = {"penalty_count": 0}
                    trade_memory[sym_key]["penalty_count"] += 1
                    save_trade_memory(trade_memory)
                    st.success(f"✅ {top_trade.get('name')} की गलती दर्ज कर ली गई है।")
            
            with col2:
                st.markdown("### 🎯 ट्रेडिंग टारगेट्स (सख्त 1:2 रिस्क-रिवॉर्ड आधारित):")
                st.markdown(f"* **प्रवेश मूल्य (Entry Price):** <span style='color:#3498db; font-size:20px; font-weight:bold;'>₹{top_trade.get('price'):.2f} पर ऑर्डर लगाएँ (MIS + Limit Order)</span>", unsafe_allow_html=True)
                st.markdown(f"* **ट्रेडिंग मात्रा (Quantity):** <span style='color:#f1c40f; font-size:20px; font-weight:bold;'>{top_trade.get('qty')} Shares</span> (रिस्क मैनेज्ड)", unsafe_allow_html=True)
                st.markdown(f"* **लक्ष्य (Target Price):** <span style='color:#2ecc71; font-size:20px; font-weight:bold;'>₹{top_trade.get('target'):.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"* **स्टॉप लॉस (Stop Loss):** <span style='color:#e74c3c; font-size:20px; font-weight:bold;'>₹{top_trade.get('sl'):.2f} (Multi-TF आधारित)</span>", unsafe_allow_html=True)

        st.markdown("### 🤖 जेमिनी एआई लाइव सिग्नल्स और वर्डिक्ट")
        if st.button("🤖 जेमिनी एआई से लाइव विश्लेषण पूछें"):
            with st.spinner("जेमिनी एआई लाइव चार्ट स्ट्रक्चर का विश्लेषण कर रहा है..."):
                ai_verdict = get_ai_intraday_verdict(top_trade.get('sym'), gemini_api_key)
                st.info(f"💡 **एआई गाइडलाइन:** {ai_verdict}")
    else:
        st.warning("⚠️ फ़िलहाल किसी भी स्टॉक में 5Min + 15Min दोनों टाइमफ्रेम का कंबाइंड मोमेंटम नहीं मिला है।")
