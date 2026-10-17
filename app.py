
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import urllib.request
import xml.etree.ElementTree as ET

from urllib.parse import quote
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="Stock Saathi",
    page_icon="📈",
    layout="centered"
)

st.title("📈 Stock Saathi")
st.caption("Indian Cash Market • Paper Trading First")

st.warning(
    "Yahoo Finance ka daily closing data live market price nahi hai. "
    "Entry, Target aur Stop-Loss sirf analysis reference hain. "
    "Order se pehle broker par current price khud verify karein."
)

STOCKS = {
    "Reliance Industries": {
        "ticker": "RELIANCE.NS",
        "aliases": ["reliance industries", "reliance"]
    },
    "HDFC Bank": {
        "ticker": "HDFCBANK.NS",
        "aliases": ["hdfc bank"]
    },
    "ICICI Bank": {
        "ticker": "ICICIBANK.NS",
        "aliases": ["icici bank"]
    },
    "State Bank of India": {
        "ticker": "SBIN.NS",
        "aliases": ["state bank of india", "sbi"]
    },
    "Infosys": {
        "ticker": "INFY.NS",
        "aliases": ["infosys"]
    },
    "TCS": {
        "ticker": "TCS.NS",
        "aliases": ["tata consultancy services", "tcs"]
    },
    "Bharti Airtel": {
        "ticker": "BHARTIARTL.NS",
        "aliases": ["bharti airtel", "airtel"]
    },
    "Larsen & Toubro": {
        "ticker": "LT.NS",
        "aliases": ["larsen and toubro", "larsen & toubro", "l&t"]
    },
    "ITC": {
        "ticker": "ITC.NS",
        "aliases": ["itc limited", "itc"]
    },
    "Nifty BeES": {
        "ticker": "NIFTYBEES.NS",
        "aliases": ["nifty bees", "niftybees"]
    }
}

NEGATIVE_WORDS = [
    "fraud", "default", "investigation", "penalty",
    "probe", "resignation", "downgrade", "loss",
    "decline", "ban", "sebi action", "insolvency",
    "गिरावट", "जांच", "जुर्माना", "धोखाधड़ी",
    "डिफॉल्ट", "नुकसान", "कार्रवाई"
]

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker):
    try:
        df = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=15
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            if ticker in df.columns.get_level_values(-1):
                df = df.xs(ticker, axis=1, level=-1)
            else:
                df.columns = df.columns.get_level_values(0)

        required = ["Close", "High", "Low"]
        if not all(c in df.columns for c in required):
            return None

        df = df.dropna(subset=required).copy()

        if len(df) < 55:
            return None

        return df

    except Exception:
        return None


def fetch_rss(url):
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 StockSaathi/1.0"}
        )

        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read()

        root = ET.fromstring(raw)
        items = []

        for item in root.findall(".//item"):
            title = item.findtext("title", default="").strip()
            link = item.findtext("link", default="").strip()
            pubdate = item.findtext("pubDate", default="").strip()
            source = item.findtext("source", default="").strip()

            if not title:
                continue

            try:
                published = parsedate_to_datetime(pubdate)
                if published.tzinfo:
                    published = published.astimezone(
                        ZoneInfo("Asia/Kolkata")
                    )
                published_date = published.date()
            except Exception:
                published_date = None

            items.append({
                "title": title,
                "link": link,
                "source": source,
                "date": published_date
            })

        return items

    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def get_news():
    company_query = (
        '("Reliance Industries" OR "HDFC Bank" OR "ICICI Bank" '
        'OR "State Bank of India" OR Infosys OR TCS OR '
        '"Bharti Airtel" OR "Larsen and Toubro" OR '
        '"ITC Limited" OR "Nifty BeES") when:7d'
    )

    official_query = (
        '(site:nseindia.com OR site:bseindia.com) '
        '("Reliance Industries" OR "HDFC Bank" OR "ICICI Bank" '
        'OR Infosys OR TCS OR "Bharti Airtel" OR ITC) when:7d'
    )

    general_url = (
        "https://news.google.com/rss/search?q="
        + quote(company_query)
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )

    official_url = (
        "https://news.google.com/rss/search?q="
        + quote(official_query)
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )

    general_news = fetch_rss(general_url)
    official_news = fetch_rss(official_url)

    combined = {}
    for item in general_news + official_news:
        combined[item["title"].lower()] = item

    return list(combined.values()), bool(general_news), bool(official_news)


def news_for_stock(stock_name, aliases, headlines):
    matched = []

    for item in headlines:
        title = item["title"].lower()

        if any(alias.lower() in title for alias in aliases):
            matched.append(item)

    return matched


def analyse_stock(stock_name, details, capital, risk_pct, nifty_up, headlines):
    df = get_history(details["ticker"])

    if df is None:
        return None, "Price data unavailable"

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)

    last_close = float(close.iloc[-1])
    last_date = pd.Timestamp(df.index[-1]).date()

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    age_days = (today - last_date).days

    if age_days > 4:
        return None, f"Old price data: {last_date}"

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    rsi = float(rsi_series.iloc[-1])

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = float(tr.rolling(14).mean().iloc[-1])
    ma20 = float(sma20.iloc[-1])
    ma50 = float(sma50.iloc[-1])

    if not all(np.isfinite(v) for v in [rsi, atr, ma20, ma50]):
        return None, "Indicators unavailable"

    trend_up = last_close > ma20 > ma50

    score = 0
    if trend_up:
        score += 40
    if last_close > ma20:
        score += 15
    if 50 <= rsi <= 65:
        score += 25
    elif 45 <= rsi < 50 or 65 < rsi <= 70:
        score += 15

    if close.iloc[-1] > close.iloc[-5]:
        score += 10
    if nifty_up:
        score += 10

    news = news_for_stock(
        stock_name, details["aliases"], headlines
    )

    recent_news = []
    for item in news:
        if item["date"] is None or (today - item["date"]).days <= 7:
            recent_news.append(item)

    negative_hits = [
        item for item in recent_news
        if any(word in item["title"].lower() for word in NEGATIVE_WORDS)
    ]

    entry = last_close
    stop = entry - (1.5 * atr)
    target = entry + (2 * (entry - stop))

    risk_amount = capital * risk_pct / 100
    per_share_risk = entry - stop

    if per_share_risk <= 0 or entry <= 0:
        return None, "Risk calculation failed"

    qty_by_risk = int(risk_amount / per_share_risk)
    qty_by_budget = int(capital / entry)
    quantity = min(qty_by_risk, qty_by_budget)

    eligible = (
        trend_up
        and 45 <= rsi <= 70
        and nifty_up
        and quantity > 0
        and len(negative_hits) == 0
    )

    result = {
        "name": stock_name,
        "score": score,
        "entry": entry,
        "target": target,
        "stop": stop,
        "quantity": quantity,
        "risk": quantity * per_share_risk,
        "date": last_date,
        "rsi": rsi,
        "news_count": len(recent_news),
        "negative_hits": negative_hits,
        "eligible": eligible
    }

    return result, "OK"


with st.sidebar:
    st.header("Risk Settings")
    capital = st.number_input(
        "Total capital (₹)",
        min_value=1000,
        max_value=10000000,
        value=50000,
        step=5000
    )
    risk_pct = st.select_slider(
        "Risk per trade (%)",
        options=[0.25, 0.5, 0.75, 1.0],
        value=0.5
    )
    st.caption("Cash market only • No F&O")

if st.button("🔄 Refresh Analysis", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Price data aur available headlines check ho rahe hain..."):
    nifty_df = get_history("^NSEI")
    nifty_up = False

    if nifty_df is not None:
        nifty_close = nifty_df["Close"].astype(float)
        nifty_sma20 = nifty_close.rolling(20).mean()
        nifty_sma50 = nifty_close.rolling(50).mean()

        nifty_up = (
            len(nifty_close) >= 50
            and float(nifty_close.iloc[-1]) >
            float(nifty_sma20.iloc[-1]) >
            float(nifty_sma50.iloc[-1])
        )

    headlines, general_ok, official_ok = get_news()

    results = []
    errors = []

    for stock_name, details in STOCKS.items():
        result, status = analyse_stock(
            stock_name, details, capital, risk_pct,
            nifty_up, headlines
        )

        if result is not None:
            if result["eligible"]:
                results.append(result)
        else:
            errors.append(f"{stock_name}: {status}")

results.sort(key=lambda x: x["score"], reverse=True)

st.subheader("Aaj ke Setups")
st.caption(
    "Score ek rule-based technical score hai, "
    "profit hone ki probability nahi."
)

if not nifty_up:
    st.warning(
        "Nifty trend filter UPTREND confirm nahi kar raha. "
        "Isliye naye setups rok diye gaye hain."
    )
elif not general_ok:
    st.warning(
        "News feed access nahi hua. News scan adhura hai; "
        "kisi bhi trade se pehle khud news verify karein."
    )

if not results:
    st.info(
        "Abhi koi setup saare filters pass nahi kar raha. "
        "Trade zabardasti mat lein."
    )
else:
    for item in results[:3]:
        with st.container(border=True):
            st.subheader(item["name"])
            st.metric("Setup Score", f'{item["score"]}/100')

            c1, c2 = st.columns(2)
            c1.metric("Entry reference", f'₹{item["entry"]:.2f}')
            c2.metric("Target reference", f'₹{item["target"]:.2f}')

            c3, c4 = st.columns(2)
            c3.metric("Stop-Loss reference", f'₹{item["stop"]:.2f}')
            c4.metric("Quantity", str(item["quantity"]))

            st.caption(
                f'Price date: {item["date"]} | '
                f'RSI: {item["rsi"]:.1f} | '
                f'Planned risk approx: ₹{item["risk"]:.2f}'
            )

            if item["news_count"] == 0:
                st.warning(
                    "Is stock ki recent headline match nahi mili. "
                    "Iska matlab yeh nahi ki koi negative news nahi hai."
                )
            else:
                st.caption(
                    f'Recent matched headlines: {item["news_count"]}. '
                    "Headline matching independent fact-check nahi hai."
                )

            st.warning(
                "Order se pehle live price, official announcement, "
                "liquidity aur Stop-Loss khud verify karein."
            )

with st.expander("Data status aur limitations"):
    st.write("Yahoo Finance daily price data: historical/reference only.")
    st.write(f"General news feed accessible: {'Yes' if general_ok else 'No'}")
    st.write(f"NSE/BSE domain search accessible: {'Yes' if official_ok else 'No'}")
    st.write(f"Nifty technical trend up: {'Yes' if nifty_up else 'No'}")
    st.write(
        "Yeh app full annual/quarterly reports nahi padhta aur "
        "alag-alag sources se news ki sachchai verify nahi karta."
    )
    st.write(
        "News feed mein headline na milna, negative news na hone ka proof nahi."
    )
    if errors:
        st.write("Unavailable price/indicator data:")
        for error in errors:
            st.write("- " + error)

st.caption(
    "Paper trading ke liye pehle test karein. "
    "Yeh financial advice ya profit guarantee nahi hai."
)
