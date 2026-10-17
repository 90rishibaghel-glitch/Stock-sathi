import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title='Stock Saathi', page_icon='📈', layout='wide')
st.title('📈 Stock Saathi — Indian Cash Market')
st.caption('Daily trend scanner • Hindi guidance • Manual trading only')

with st.sidebar:
    st.header('आपकी सेटिंग')
    capital = st.number_input('कुल पूँजी (₹)', min_value=1000, max_value=100000000, value=50000, step=1000)
    risk_pct = st.slider('एक ट्रेड में अधिकतम जोखिम (%)', 0.25, 2.0, 0.5, 0.25)
    max_positions = st.selectbox('एक दिन में अधिकतम ट्रेड', [1, 2], index=1)
    st.caption('यह स्कैनर सलाह/गारंटी नहीं है। ऑर्डर आपको खुद लगाने हैं।')

UNIVERSE = {
    'Reliance Industries': 'RELIANCE.NS',
    'HDFC Bank': 'HDFCBANK.NS',
    'ICICI Bank': 'ICICIBANK.NS',
    'State Bank of India': 'SBIN.NS',
    'Infosys': 'INFY.NS',
    'TCS': 'TCS.NS',
    'Bharti Airtel': 'BHARTIARTL.NS',
    'Larsen & Toubro': 'LT.NS',
    'ITC': 'ITC.NS',
    'Nifty BeES ETF': 'NIFTYBEES.NS',
}

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker):
    data = yf.download(ticker, period='6mo', interval='1d', auto_adjust=True, progress=False, threads=False)
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna()

def analyze(name, ticker):
    d = get_history(ticker)
    if d.empty or len(d) < 55 or 'Close' not in d:
        return {'Name': name, 'Ticker': ticker, 'Status': 'DATA नहीं मिला', 'Last Close (₹)': np.nan,
                'Trend': 'अज्ञात', 'RSI': np.nan, 'Volume vs 20D': np.nan, 'Entry condition': 'कोई सुझाव नहीं',
                'Stop (₹)': np.nan, 'Target (₹)': np.nan, 'Qty (risk-based)': 0, 'Risk (₹)': 0, 'Reason': 'पर्याप्त डेटा उपलब्ध नहीं'}
    close = d['Close'].astype(float)
    high = d['High'].astype(float)
    low = d['Low'].astype(float)
    vol = d['Volume'].astype(float) if 'Volume' in d else pd.Series(index=d.index, dtype=float)
    last = float(close.iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1])
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    rsi = float((100 - 100 / (1 + gain / loss)).iloc[-1])
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    v20 = float(vol.rolling(20).mean().iloc[-1]) if len(vol.dropna()) >= 20 else np.nan
    vratio = float(vol.iloc[-1] / v20) if v20 and not np.isnan(v20) and v20 > 0 else np.nan
    trend = 'UPTREND' if last > ma20 > ma50 else ('DOWNTREND' if last < ma20 < ma50 else 'MIXED')
    stop = max(0.01, last - 1.5 * atr)
    target = last + 2.0 * (last - stop)
    risk_rupees = capital * risk_pct / 100
    qty = int(risk_rupees / max(last-stop, 0.01))
    qty = min(qty, int(capital / last))
    status = 'WATCH' if trend == 'UPTREND' and 45 <= rsi <= 70 else 'NO TRADE'
    reason = f'Close {last:.2f}; MA20 {ma20:.2f}; MA50 {ma50:.2f}; RSI {rsi:.1f}.'
    if status == 'WATCH':
        reason += ' Trend अनुकूल है, लेकिन खरीदने से पहले लाइव कीमत, खबर और बाजार खुलने के बाद पुष्टि जरूरी है।'
    else:
        reason += ' ट्रेंड/RSI शर्त पूरी नहीं; अभी खरीदने का संकेत नहीं।'
    return {'Name': name, 'Ticker': ticker, 'Status': status, 'Last Close (₹)': round(last,2), 'Trend': trend,
            'RSI': round(rsi,1), 'Volume vs 20D': round(vratio,2) if not np.isnan(vratio) else np.nan,
            'Entry condition': 'केवल पुष्टि के बाद' if status == 'WATCH' else 'नहीं',
            'Stop (₹)': round(stop,2), 'Target (₹)': round(target,2), 'Qty (risk-based)': qty if status == 'WATCH' else 0,
            'Risk (₹)': round(qty*(last-stop),2) if status == 'WATCH' else 0, 'Reason': reason}

st.warning('महत्वपूर्ण: डेटा Yahoo Finance से आता है और देरी/गलती हो सकती है। यह लाइव NSE फीड नहीं है। नीचे की कीमतें पिछले उपलब्ध दैनिक डेटा की हैं—इन्हें आज की लाइव एंट्री न मानें। FII/DII, वैश्विक बाजार, रुपये, कच्चे तेल और ताज़ा कंपनी खबरों की पुष्टि इस शुरुआती संस्करण में शामिल नहीं है।')

if st.button('🔎 आज का स्कैन चलाएँ', type='primary', use_container_width=True):
    with st.spinner('शेयरों का दैनिक डेटा लाया जा रहा है…'):
        market = get_history('^NSEI')
        if market.empty or len(market) < 50:
            market_trend = 'DATA नहीं मिला'
        else:
            mc = market['Close'].astype(float)
            mlast, m20, m50 = float(mc.iloc[-1]), float(mc.rolling(20).mean().iloc[-1]), float(mc.rolling(50).mean().iloc[-1])
            market_trend = 'UPTREND' if mlast > m20 > m50 else ('DOWNTREND' if mlast < m20 < m50 else 'MIXED')
        results = [analyze(n, t) for n,t in UNIVERSE.items()]
        df = pd.DataFrame(results)
        st.subheader('बाजार की स्थिति')
        st.metric('Nifty 50 Trend', market_trend)
        if market_trend != 'UPTREND':
            st.error('Nifty का ट्रेंड साफ़ UPTREND नहीं है। सावधानी: आज का सिस्टम-निष्कर्ष NO TRADE है।')
            df['Status'] = 'NO TRADE — MARKET FILTER'
            df['Qty (risk-based)'] = 0
        else:
            st.info('Nifty trend filter पास है। फिर भी WATCH का मतलब तुरंत खरीदना नहीं है।')
        st.subheader('स्टॉक स्कैन परिणाम')
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button('परिणाम CSV डाउनलोड करें', df.to_csv(index=False).encode('utf-8-sig'), 'stock_scan.csv', 'text/csv')
        st.caption('स्कैन समय: ' + datetime.now().strftime('%d-%m-%Y %H:%M:%S') + ' (ऐप सर्वर का समय)')
        st.subheader('ट्रेड से पहले चेकलिस्ट')
        st.markdown('- [ ] NSE/ब्रोकर्स ऐप में लाइव कीमत और स्प्रेड जाँचें\n- [ ] आज की कंपनी खबर, नतीजे और कॉर्पोरेट एक्शन जाँचें\n- [ ] Nifty और सेक्टर की दिशा दोबारा जाँचें\n- [ ] स्टॉप-लॉस ऑर्डर लगाने की क्षमता सुनिश्चित करें\n- [ ] अगर एंट्री स्टॉप के बहुत पास हो, गैप हो, या बात साफ़ न हो: **NO TRADE**')
else:
    st.info('शुरू करने के लिए “आज का स्कैन चलाएँ” दबाएँ। ऐप को चलाने के बाद भी खरीद/बिक्री का फैसला खुद पुष्टि करके करें।')

st.divider()
st.caption('शैक्षिक टूल, निवेश सलाह नहीं। कोई निश्चित accuracy या मुनाफ़ा गारंटीड नहीं। पहले paper trading और historical backtesting करें।')
