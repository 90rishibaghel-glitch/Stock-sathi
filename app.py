if sorted_trades:
    top_trade = sorted_trades[0]
    
    st.success("🔥 लाइव एनएसई (NSE) डेटा के आधार पर आज का टॉप प्रायोरिटी स्टॉक मिल गया है!")
    st.markdown(f"## 🏆 Priority #1: आज का जैकपॉट इंट्राडे पिक")
    
    # वैल्यूज को सुरक्षित तरीके से निकालना और टाइप कास्ट करना
    try:
        price_val = float(top_trade.get('price', 0.0))
    except:
        price_val = 0.0

    try:
        change_val = float(top_trade.get('change', 0.0))
    except:
        change_val = 0.0

    try:
        target_val = float(top_trade.get('target', 0.0))
    except:
        target_val = 0.0

    try:
        sl_val = float(top_trade.get('sl', 0.0))
    except:
        sl_val = 0.0

    try:
        qty_val = int(top_trade.get('qty', 0))
    except:
        qty_val = 0

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label=f"{top_trade.get('name', 'Stock')}", value=f"₹{price_val}", delta=f"{change_val}%")
            st.markdown(f"**📍 सेक्टर:** {top_trade.get('sector', 'N/A')}")
            st.markdown(f"**⚡ एक्शन सिग्नल:** `{top_trade.get('signal', 'NO SIGNAL')}`")
        
        with col2:
            st.markdown(f"### 🎯 ट्रेडिंग टारगेट्स और सही गणना:")
            st.markdown(f"* **लक्ष्य (Target Price):** <span style='color:#2ecc71; font-size:20px; font-weight:bold;'>₹{target_val:.2f}</span>", unsafe_allowed_html=True)
            st.markdown(f"* **सुरक्षा स्टॉपलॉस (Stoploss):** <span style='color:#e74c3c; font-size:18px; font-weight:bold;'>₹{sl_val:.2f}</span>", unsafe_allowed_html=True)
            st.markdown(f"* **सटीक ट्रेड क्वांटिटी:** **{qty_val} शेयर्स** (आपके द्वारा तय किए गए ₹{risk_per_trade} रिस्क के अनुसार)")
            
            with st.spinner("जेमिनी एआई लाइव सिचुएशन का विश्लेषण कर रहा है..."):
                ai_verdict = get_ai_intraday_verdict(top_trade.get('sym', ''), gemini_api_key)
            st.info(f"🤖 **एआई (AI) एक्सपर्ट राय:** {ai_verdict}")

else:
    st.info("💡 अभी मार्केट में किसी भी बड़े स्टॉक में कोई मजबूत ब्रेकआउट या विश्वसनीय सिग्नल नहीं बना है। लाइव मार्केट (9:15 AM - 3:30 PM) के दौरान 'लाइव मार्केट डेटा रिफ्रेश करें' बटन दबाएं।")
