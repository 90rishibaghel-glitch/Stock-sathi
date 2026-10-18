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

# --- जेमिनी एआई की सेटिंग्स ---
gemini_api_key = st.sidebar.text_input("Gemini API Key दर्ज करें (न्यूज़ एनालिसिस के लिए):", type="password")

# --- इंट्राडे रिस्क कैलकुलेटर ---
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

# --- लाइव डेटा फेचिंग इंजन (इंट्राडे के लिए 1-दिन का 5-मिनट डेटा) ---
def fetch_intraday_data(ticker_sym):
    try:
        # इंट्राडे के लिए सबसे सटीक लाइव डेटा 5 या 15 मिनट का होता है
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
        return "AI न्यूज़ स्कैनर बंद है (Key डालें)"
    try:
        tk = yf.Ticker(ticker_sym)
        news = tk.news[:2]
        if not news:
            return "कोई ताज़ा खबर नहीं"
        headlines = " | ".join([n['title'] for n in news])
        
        client = genai.Client(api_key=api_key)
        prompt = f"तुम एक एक्सपर्ट डे-ट्रेडर हो। इस स्टॉक {ticker_sym} की हेडलाइंस का विश्लेषण करो: {headlines}। मुझे बताओ कि आज इंट्राडे में यह स्टॉक 'तेज' (BULLISH) रहेगा या 'मंदा' (BEARISH)। सिर्फ 1 वाक्य में हिंदी में उत्तर दो।"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except:
        return "एआई विश्लेषण अस्थायी रूप से अनुपलब्ध।"

# --- लाइव डैशबोर्ड मुख्य भाग ---
st.subheader("📊 रीयल-टाइम इंट्राडे सेलेक्टर्स (टॉप प्रॉफिट मेकर स्टॉक्स)")

# ऑटो-रिफ्रेश बटन
if st.button("🔄 लाइव मार्केट डेटा रिफ्रेश करें"):
    st.rerun()

all_intraday_trades = []

with st.spinner("सभी सेक्टर्स का लाइव वॉल्यूम और मोमेंटम स्कैन किया जा रहा है..."):
    for sector, stocks in SECTOR_UNIVERSE.items():
        for name, sym in stocks.items():
            df = fetch_intraday_data(sym)
            if df is None or len(df) < 5:
                continue
            
            # इंट्राडे कैलकुलेशन डेटा
            last_price = float(df['Close'].iloc[-1])
            open_price = float(df['Open'].iloc[0]) # आज सुबह का ओपन
            high_price = float(df['High'].max())
            low_price = float(df['Low'].min())
            
            price_change_pct = ((last_price - open_price) / open_price) * 100
            
            # इंट्राडे मोमेंटम स्कोर (वॉल्यूम और प्राइस एक्शन के आधार पर)
            current_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Volume'].mean())
            volume_surge = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            # सिग्नल तय करने का लॉजिक (ओपन-लो या ओपन-हाई ब्रेकआउट)
            signal = "NO SIGNAL"
            stop_loss = 0
            target = 0
            score = 0
            
            if last_price > open_price and price_change_pct > 0.5:
                signal = "📈 BUY (Long)"
                stop_loss = last_price - (last_price * 0.007) # 0.7% का स्टॉपलॉस
                target = last_price + (last_price * 0.015)    # 1.5% का टारगेट
                score = price_change_pct * volume_surge
            elif last_price < open_price and price_change_pct < -0.5:
                signal = "📉 SELL (Short)"
                stop_loss = last_price + (last_price * 0.007)
                target = last_price - (last_price * 0.015)
                score = abs(price_change_pct) * volume_surge

            if signal != "NO SIGNAL":
                # रिस्क के हिसाब से क्वांटिटी कैलकुलेटर
                per_share_risk = abs(last_price - stop_loss)
                qty = int(risk_per_trade // per_share_risk) if per_share_risk > 0 else 0
                max_qty_allowed = int((capital * 5) // last_price) # 5x इंट्राडे लेवरेज मानकर
                final_qty = min(qty, max_qty_allowed)
                
                all_intraday_trades.append({
                    "sector": sector, "name": name, "price": round(last_price, 2),
                    "change": round(price_change_pct, 2), "signal": signal,
                    "target": round(target, 2), "sl": round(stop_loss, 2),
                    "qty": final_qty, "score": score, "sym": sym
                })

# स्कोर के हिसाब से बेस्ट मोमेंटम स्टॉक्स को शॉर्टलिस्ट करें
sorted_trades = sorted(all_intraday_trades, key=lambda x: x['score'], reverse=True)

if sorted_trades:
    st.success(f"🔥 मार्केट से {len(sorted_trades)} हाई-मोमेंटम इंट्राडे सिग्नल्स मिले हैं!")
    
    # टॉप 3 बेस्ट स्टॉक्स को बड़े कार्ड्स में दिखाएं
    st.markdown("### 🏆 आज के टॉप 3 इंट्राडे प्रॉफिट पिक")
    t_cols = st.columns(3)
    for idx, trade in enumerate(sorted_trades[:3]):
        with t_cols[idx]:
            st.metric(label=f"#{idx+1} {trade['name']} ({trade['sector']})", value=f"₹{trade['price']}", delta=f"{trade['change']}%")
            st.markdown(f"**सिग्नल:** `{trade['signal']}`")
            st.markdown(f"🎯 **टारगेट:** ₹{trade['target']} | 🛑 **स्टॉपलॉस:** ₹{trade['sl']}")
            st.markdown(f"🛍️ **ट्रेड क्वांटिटी:** {trade['qty']} शेयर्स (रिस्क सेटिंग्स के अनुसार)")
            
            # लाइव एआई वर्डिक्ट
            ai_verdict = get_ai_intraday_verdict(trade['sym'], gemini_api_key)
            st.info(f"🤖 **AI राय:** {ai_verdict}")
            st.markdown("---")

    # बाकी बचे हुए स्टॉक्स को एक टेबल में व्यवस्थित रूप से दिखाएं
    st.markdown("### 🔍 अन्य सेक्टर्स के लाइव इंट्राडे सिग्नल्स")
    trade_df = pd.DataFrame(sorted_trades[3:])
    if not trade_df.empty:
        trade_df = trade_df[["sector", "name", "price", "change", "signal", "target", "sl", "qty"]]
        trade_df.columns = ["सेक्टर", "कंपनी", "लाइव भाव (₹)", "बदलाव (%)", "सिग्नल", "टारगेट", "स्टॉपलॉस", "क्वांटिटी"]
        st.dataframe(trade_df, use_container_width=True, hide_index=True)
else:
    st.info("💡 अभी किसी भी सेक्टर के स्टॉक में मजबूत इंट्राडे ब्रेकआउट नहीं हुआ है। लाइव मार्केट के दौरान 'लाइव मार्केट डेटा रिफ्रेश करें' बटन दबाएं।")
