# Stock Saathi — शुरुआती वेबसाइट

यह Streamlit आधारित मोबाइल-फ्रेंडली स्टॉक स्कैनर है। यह Yahoo Finance से दैनिक ऐतिहासिक डेटा लेता है; लाइव NSE फीड नहीं है और मुनाफ़ा/accuracy की गारंटी नहीं देता।

## वेबसाइट मुफ्त में ऑनलाइन चलाने का तरीका

1. इस ZIP को डाउनलोड करके अपने फोन में extract करें।
2. GitHub पर एक नया repository बनाएँ (उदाहरण: `stock-saathi`)।
3. `app.py`, `requirements.txt`, और `README.md` repository में upload करें।
4. Streamlit Community Cloud पर जाएँ: https://share.streamlit.io/
5. GitHub से sign in करके **Create app** चुनें, repository और `app.py` चुनें, फिर Deploy दबाएँ।
6. Deployment पूरा होने पर मिलने वाला URL फोन में खोलें।

## लोकल चलाना

```bash
pip install -r requirements.txt
streamlit run app.py
```

## सीमाएँ

- Yahoo Finance डेटा में देरी/कमी हो सकती है।
- FII/DII flows, USD/INR, crude, global indices और ताज़ा खबरों की सत्यापित एकीकृत जाँच अभी नहीं है।
- Entry/stop/target केवल ATR-आधारित शैक्षिक गणना है, वास्तविक सिफ़ारिश नहीं।
- पहले paper trading, transaction costs/slippage और historical out-of-sample backtest करें।
