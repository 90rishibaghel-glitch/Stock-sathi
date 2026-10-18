import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
from google import genai
# 100% लाइव क्लाउड-फ्रेंडली nsepythonserver का इम्पोर्ट
from nsepythonserver import nse_quote_ltp, nse_quote

# 1. पेज सेटअप (इंट्राडे स्पेशल डार्क थीम और वाइड लेआउट)
st.set_page_config(page_title="AI Intraday GTT Scalper v3", page_icon="⚡", layout="wide")

st.title("⚡ AI Intraday GTT Scalper & Self-Learning Tracker (v3)")
st.caption("30-मिनट ऑटोमैटिक मोमेंटम स्कैनर | टाइम-स्टैम्पड हिस्ट्री लॉग | जेमिनी एआई क्लोज्ड-लूप लर्निंग")

# --- जेमिनी एआई की सेटिंग्स (Secrets से की उठाना) ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- ऐप मेमोरी इनिशियलाइजेशन (Session State for History Tracking) ---
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []  # बंद हो चुके ट्रेड्स का रिकॉर्ड
if "active_tracked_trades" not in st.session_state:
    st.session_state.active_tracked_trades = {}  # जो ट्रेड्स अभी लाइव ट्रैक हो रहे हैं

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
    except Exception as e:
        # यहाँ पूरा एक्सेप्शन हैंडलिंग ब्लॉक जोड़ दिया गया है ताकि नेटवर्क एरर आने पर ऐप बंद न हो
        return None

# --- जेमिनी AI न्यूज़ सेंटीमेंट और भविष्यवाणी विश्लेषण ---
def get_ai_intraday_verdict(ticker_sym, api_key, history_context=""):
    if not api_key:
        return "AI न्यूज़ स्कैनर बंद है (Secrets में Key जांचें)"
    try:
        client = genai.Client(api_key=api_key)
        prompt = (f"तुम एक एक्सपर्ट डे-ट्रेडर हो। स्टॉक {ticker_sym} में अगले 30 मिनट के लिए फास्ट मोमेंटम बन रहा है। "
                  f"यहाँ आज की ट्रेड हिस्ट्री और एक्यूरेसी का डेटा है: [{history_context}]. "
                  f"अगर ऐप ने अतीत में गलतियाँ (SL Hit) की हैं, तो उसके आधार पर अपनी स्ट्रेटेजी को लाइव सुधारते हुए "
                  f"इस स्टॉक के लिए सटीक 1-2 वाक्यों में हिंदी में गाइडलाइन दो।")
                  
        response = client.models.generate_content(model='gemini-3.8-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"एआई विश्लेषण वर्तमान में उपलब्ध नहीं है। एरर: {str(e)}"

# --- लाइव डैशबोर्ड मुख्य भाग ---
st.subheader("📊 रीयल-टाइम इंट्राडे सेलेक्टर (30-मिनट फास्ट ट्रेंड आधारित)")

if st.button("🔄 लाइव मार्केट डेटा रिफ्रेश करें"):
    st.rerun()

all_intraday_trades = []

with st.spinner("सभी सेक्टर्स का 30-मिनट लाइव वॉल्यूम स्कैन किया जा रहा है..."):
    for sector, stocks in SECTOR_UNIVERSE.items():
        for name, sym in stocks.items():
            market_data = fetch_live_market_data(sym)
            if market_data is None:
                continue
            
            try:
                last_price = float(market_data["last_price"])
                open_price = float(market_data["open_price"])
            except (TypeError, ValueError):
                continue
            
            if open_price == 0:
                continue
                
            price_change_pct = float(((last_price - open_price) / open_price) * 100)
            
            signal = "NO SIGNAL"
            entry_price = 0.0
            stop_loss = 0.0
            target = 0.0
            score = 0.0
            
            # 30-मिनट फास्ट मोमेंटम लॉजिक (0.3% फ़िल्टर, 0.6% SL, 1.2% Target)
            if last_price > open_price and price_change_pct > 0.3:
                signal = "⚡ GTT BUY ABOVE"
                entry_price = float(last_price + (last_price * 0.0005))   
                stop_loss = float(entry_price - (entry_price * 0.006))     
                target = float(entry_price + (entry_price * 0.012))        
                score = float(price_change_pct * 2.0) 
            elif last_price < open_price and price_change_pct < -0.3:
                signal = "⚡ GTT SELL BELOW"
                entry_price = float(last_price - (last_price * 0.0005))   
                stop_loss = float(entry_price + (entry_price * 0.006))     
                target = float(entry_price - (entry_price * 0.012))        
                score = float(abs(price_change_pct) * 2.0)

            if signal != "NO SIGNAL":
                per_share_risk = abs(entry_price - stop_loss)
                qty = int(risk_per_trade // per_share_risk) if per_share_risk > 0 else 0
                max_qty_allowed = int((capital * 5) // entry_price)
                final_qty = min(qty, max_qty_allowed)
                
                trade_obj = {
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
                }
                all_intraday_trades.append(trade_obj)
                
                # लाइव ट्रैकिंग मेमोरी सेटअप
                trade_id = f"{sym}_{signal}"
                if trade_id not in st.session_state.active_tracked_trades:
                    already_closed = any(h['id'] == trade_id for h in st.session_state.trade_history)
                    if not already_closed:
                        st.session_state.active_tracked_trades[trade_id] = {
                            "id": trade_id, "name": name, "sym": sym, "signal": signal,
                            "entry_level": round(entry_price, 2), "target": round(target, 2), "sl": round(stop_loss, 2),
                            "triggered": False, "trigger_time": None
                        }

# --- एक्टिव ट्रेड्स का लाइव स्टेटस अपडेट इंजन ---
for tid, tdata in list(st.session_state.active_tracked_trades.items()):
    live_rates = next((t for t in all_intraday_trades if t['sym'] == tdata['sym']), None)
    if live_rates:
        current_ltp = live_rates['current_price']
        now_str = datetime.now().strftime("%H:%M:%S")
        
        # 1. चेक एंट्री ट्रिगर
        if not tdata['triggered']:
            if (tdata['signal'] == "⚡ GTT BUY ABOVE" and current_ltp >= tdata['entry_level']) or \
               (tdata['signal'] == "⚡ GTT SELL BELOW" and current_ltp <= tdata['entry_level']):
                st.session_state.active_tracked_trades[tid]['triggered'] = True
                st.session_state.active_tracked_trades[tid]['trigger_time'] = now_str
                st.toast(f"🔔 {tdata['name']} का एंट्री पॉइंट ट्रिगर हो गया है!")
                
        # 2. चेक टारगेट / एसएल एग्जिट
        else:
            is_target_hit = False
            is_sl_hit = False
            
            if tdata['signal'] == "⚡ GTT BUY ABOVE":
                if current_ltp >= tdata['target']: is_target_hit = True
                elif current_ltp <= tdata['sl']: is_sl_hit = True
            elif tdata['signal'] == "⚡ GTT SELL BELOW":
                if current_ltp <= tdata['target']: is_target_hit = True
                elif current_ltp >= tdata['sl']: is_sl_hit = True
                
            if is_target_hit or is_sl_hit:
                status_text = "🎯 TARGET" if is_target_hit else "🛑 STOP LOSS"
                st.session_state.trade_history.append({
                    "id": tid, "name": tdata['name'], "signal": tdata['signal'],
                    "entry_level": tdata['entry_level'], "target": tdata['target'], "sl": tdata['sl'],
                    "trigger_time": tdata['trigger_time'], "exit_time": now_str, "result": status_text
                })
                del st.session_state.active_tracked_trades[tid]
                st.toast(f"📢 {tdata['name']} का {status_text} हिट हो गया है!")

# एआई के लिए हिस्ट्री कांटेक्स्ट स्ट्रिंग
history_summary = ", ".join([f"{h['name']}({h['result']} Hit at {h['exit_time']})" for h in st.session_state.trade_history[-5:]])

# स्कोर के आधार पर सॉर्ट करके फ्रंट-एंड रेंडरिंग
sorted_trades = sorted(all_intraday_trades, key=lambda x: x['score'], reverse=True)

if sorted_trades:
    st.success("🔥 लाइव एनएसई (NSE) डेटा के आधार पर आज के टॉप 3 ऑटोमैटिक GTT स्टॉक्स मिल गए हैं!")
    
    for index, top_trade in enumerate(sorted_trades[:3]):
