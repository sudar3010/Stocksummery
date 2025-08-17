import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests, urllib.parse, time, pytz

from datetime import datetime, timedelta, timezone
import google.generativeai as genai
import urllib.parse
import pytz
from config.settings import (
    PRICE_API_HEADERS,
    NEWS_API_URL,
    NEWS_API_PARAMS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,GNEWS_API_KEY, NEWSAPI_KEY
)
from dateutil import parser

genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAolmRW2NKcmqd83Z-lnLp2oyNiocSm3c8"))

SYMBOLS = ["TCS", "KTKBANK","tata steel","ITC","ICICI Bank"]
STOCK_KEYWORDS = [
    "stock",
    "share",
    "market",
    "nse",
    "bse",
    "sensex",
    "nifty",
    "results",
    "earnings",
    "profit",
    "revenue",
    "quarter",
    "q1",
    "q2",
    "q3",
    "q4",
    "dividend",
    "buyback",
    "ipo",
    "contract",
    "deal",
    "acquisition",
    "merger",
]


# === Utility ===
def is_stock_related(title, desc):
    text = f"{title} {desc}".lower()
    return any(keyword in text for keyword in STOCK_KEYWORDS)


# === Fetch News ===
def fetch_from_gnews(symbol, days=5):
    url = f"https://gnews.io/api/v4/search?q={symbol}&lang=en&country=in&max=10&token={GNEWS_API_KEY}"
    resp = requests.get(url).json()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    articles = []
    for a in resp.get("articles", []):
        try:
            pub_date = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
        except:
            continue
        if pub_date >= cutoff and is_stock_related(
            a.get("title", ""), a.get("description", "")
        ):
            articles.append(
                {
                    "title": a.get("title", ""),
                    "desc": a.get("description", ""),
                    "url": a.get("url", ""),
                    "date": pub_date.strftime("%Y-%m-%d"),
                }
            )
    return articles


def fetch_from_newsapi(symbol, days=2):
    base = "https://newsapi.org/v2/everything"
    to_date = datetime.now(timezone.utc)
    params = {
        "q": f'"{symbol}" OR "{symbol} company India"',
        "from": (to_date - timedelta(days=days)).strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": NEWSAPI_KEY,
    }
    resp = requests.get(base, params=params).json()

    articles = []
    for a in resp.get("articles", []):
        if is_stock_related(a.get("title", ""), a.get("description", "")):
            articles.append(
                {
                    "title": a.get("title", ""),
                    "desc": a.get("description", ""),
                    "url": a.get("url", ""),
                    "date": a["publishedAt"][:10],
                }
            )
    return articles


# === Price Data ===
def fetch_price(symbol):
    url = f"https://indian-stock-exchange-api2.p.rapidapi.com/stock?name={symbol}"
    resp = requests.get(url, headers=PRICE_API_HEADERS)
    data = resp.json()

    # === Special symbol-to-company mapping ===
    SYMBOL_NAME_MAP = {
        "KTKBANK": "Karnataka Bank",
        "TCS": "Tata Consultancy Services",
        # Add more special cases if needed
    }

    if "peerCompanyList" in data:
        peer_companies = data["peerCompanyList"]
    elif "companyProfile" in data and "peerCompanyList" in data["companyProfile"]:
        peer_companies = data["companyProfile"]["peerCompanyList"]
    elif (
        "stockDetailsReusableData" in data
        and "peerCompanyList" in data["stockDetailsReusableData"]
    ):
        peer_companies = data["stockDetailsReusableData"]["peerCompanyList"]
    else:
        peer_companies = []

    company_info = None
    for c in peer_companies:
        company_name = c.get("companyName", "").lower()

        # If symbol has a special mapping, check by mapped name
        if symbol.upper() in SYMBOL_NAME_MAP:
            if SYMBOL_NAME_MAP[symbol.upper()].lower() in company_name:
                company_info = c
                break
        else:
            # Normal case: check if symbol itself is part of the name
            if symbol.lower() in company_name:
                company_info = c
                break

    # Fallback if still not found → direct stock details
    if not company_info and "stockDetails" in data:
        company_info = data["stockDetails"]

    if not company_info:
        return None
    try:
        investor_notes = []
        score = 50  # Start from neutral
        max_score = 100
        min_score = 0

        # === BASIC DATA EXTRACTION ===
        price = float(company_info.get("price", 0))
        yhigh = float(company_info.get("yhigh", 0))
        ylow = float(company_info.get("ylow", 0))
        pe = float(company_info.get("priceToEarningsValueRatio", 0))
        pb = float(company_info.get("priceToBookValueRatio", 0))
        roe = float(company_info.get("returnOnAverageEquityTrailing12Month", 0))
        net_margin = float(company_info.get("netProfitMarginPercentTrailing12Month", 0))
        dividend_yield = float(
            company_info.get("dividendYieldIndicatedAnnualDividend", 0)
        )
        debt_to_equity = float(
            company_info.get("ltDebtPerEquityMostRecentFiscalYear", 0)
        )
        rating = company_info.get("overallRating", "").capitalize()
        percent_change = float(company_info.get("percentChange", 0))

        # === LONG-TERM FUNDAMENTAL METRICS ===
        eps_growth_5yr = 0.0
        growth_data = data.get("keyMetrics", {}).get("growth", [])
        for item in growth_data:
            if item.get("key") == "ePSGrowthRate5Year":
                eps_growth_5yr = float(item.get("value", 0))
                break
        print("EPS Growth Rate (5Y):", eps_growth_5yr)

        # === Revenue Growth Rate (5 Year) ===
        revenue_growth = 0.0
        for item in growth_data:
            if item.get("key") == "revenueGrowthRate5Year":
                revenue_growth = float(item.get("value", 0))
                break

        # === PEG Ratio (inside keyMetrics -> valuation) ===
        peg_ratio = 0.0
        valuation_data = data.get("keyMetrics", {}).get("valuation", [])
        for item in valuation_data:
            if item.get("key") == "pegRatio":
                peg_ratio = float(item.get("value", 0))
                break

        # === Dividend Growth (3 Year) (inside keyMetrics -> growth) ===
        dividend_growth_5y = 0.0
        for item in growth_data:
            if item.get("key") == "growthRatePercentDividend3Year":
                dividend_growth_5y = float(item.get("value", 0))
                break

        # === Free Cash Flow TTM (inside keyMetrics -> financialstrength) ===
        fcf_yield = 0.0
        financial_strength_data = data.get("keyMetrics", {}).get(
            "financialstrength", []
        )
        for item in financial_strength_data:
            if item.get("key") == "freeCashFlowtrailing12Month":
                fcf_yield = float(item.get("value", 0))
                break

        # === Beta (inside keyMetrics -> priceandvolume) ===
        beta = 0.0
        price_volume_data = data.get("keyMetrics", {}).get("priceandVolume", [])
        for item in price_volume_data:
            if item.get("key") == "beta":
                try:
                    beta_str = str(item.get("value", "0")).replace(",", ".")
                    beta = float(beta_str)
                except ValueError:
                    beta = 0.0
                break

        # === VALUATION SIGNALS ===
        if pe < 8 and pb < 1:
            investor_notes.append(
                "💰 Potential Value Buy — Low P/E & P/B suggest undervaluation"
            )
            score += 6
        elif pe > 25 and pb > 4:
            investor_notes.append("⚠️ Overvalued — High P/E & P/B")
            score -= 6

        if 0 < peg_ratio < 1:
            investor_notes.append("📉 Undervalued vs. Growth — PEG < 1")
            score += 5

        # === PROFITABILITY ===
        if roe > 10 and net_margin > 20:
            investor_notes.append("📈 Strong Profitability — High ROE & Net Margin")
            score += 6
        elif roe < 5:
            investor_notes.append("⚠️ Weak Profitability — Low ROE")
            score -= 4

        # === DIVIDEND ===
        if dividend_yield > 2:
            investor_notes.append(f"💵 Good Dividend Yield ({dividend_yield:.2f}%)")
            score += 4
        if dividend_growth_5y > 5:
            investor_notes.append(
                f"💵 Consistent Dividend Growth ({dividend_growth_5y:.2f}% CAGR)"
            )
            score += 3

        # === FINANCIAL HEALTH ===
        if (
            debt_to_equity > 2
            and "bank" not in company_info.get("companyName", "").lower()
        ):
            investor_notes.append(
                f"⚠️ High Leverage Risk — Debt/Equity: {debt_to_equity:.2f}"
            )
            score -= 6
        elif debt_to_equity < 0.5:
            investor_notes.append(
                f"🛡️ Strong Balance Sheet — Low Debt/Equity ({debt_to_equity:.2f})"
            )
            score += 3

        if fcf_yield > 5:
            investor_notes.append(
                f"💡 High Free Cash Flow Yield ({fcf_yield:.2f}%) — Strong Liquidity"
            )
            score += 4

        # === GROWTH ===
        if eps_growth_5yr > 10:
            investor_notes.append(
                f"🚀 Strong Earnings Growth ({eps_growth_5yr:.2f}% CAGR over 5Y)"
            )
            score += 5
        elif eps_growth_5yr < 0:
            investor_notes.append(f"⚠️ Negative Earnings Growth ({eps_growth_5yr:.2f}%)")
            score -= 6

        if revenue_growth > 8:
            investor_notes.append(f"📊 Healthy Revenue Growth ({revenue_growth:.2f}%)")
            score += 4

        # === VOLATILITY ===
        if beta < 0.8:
            investor_notes.append(
                f"🛡️ Low Volatility (Beta: {beta:.2f}) — Defensive Play"
            )
            score += 3
        elif beta > 1.5:
            investor_notes.append(f"⚡ High Volatility Risk (Beta: {beta:.2f})")
            score -= 3

        # === PRICE POSITION ===
        if ylow > 0 and ((price - ylow) / ylow) * 100 < 5:
            investor_notes.append("📉 Near 52-Week Low — Possible Value Entry")
            score += 2
        if price > 0 and ((yhigh - price) / price) * 100 < 5:
            investor_notes.append("📊 Near 52-Week High — Consider Profit Booking")
            score -= 2

        # === SENTIMENT ===
        if rating:
            sentiment_emoji = (
                "📈"
                if rating.lower() == "bullish"
                else "📉" if rating.lower() == "bearish" else "⚖️"
            )
            investor_notes.append(f"{sentiment_emoji} Market Sentiment: {rating}")
            score += (
                2
                if rating.lower() == "bullish"
                else -2 if rating.lower() == "bearish" else 0
            )

        if percent_change <= -3:
            investor_notes.append(
                f"🔻 Significant Drop Today ({percent_change:.2f}%) — Review Position"
            )
            score -= 1

        # === FINAL SCORE RANGE ===
        # score = max(min_score, min(max_score, score))
        # investor_notes.append(f"📊 **Long-Term Attractiveness Score:** {score}/100")

    except Exception as e:
        print(f"⚠️ Error generating investor notes: {e}")
    return {
        "name": company_info.get("companyName", symbol),
        "price": company_info.get("price", "N/A"),
        "yhigh": company_info.get("yhigh", "N/A"),
        "ylow": company_info.get("ylow", "N/A"),
        "change": company_info.get("percentChange", "N/A"),
        "investor_notes": investor_notes,
    }


# === Generate Summary ===
STYLE_CONFIG = {
    "minimalist_pro": {
        "header": "*{symbol} — {timestamp}*",
        "price_block": "**Price**",
        "notes_block": "**Key Insights**",
        "divider": "— — — — —",
        "closing": "*End of Brief*"
    },
    "impact_pulse": {
        "header": "🚨 *{symbol} Snapshot — {timestamp}*",
        "price_block": "💥 **Market Pulse**",
        "notes_block": "🎯 **Investor Focus**",
        "divider": "⚡⚡⚡⚡⚡",
        "closing": "📌 *Review. React. Reassess.*"
    },
    "zen_flow": {
        "header": "🌿 *{symbol} Morning Flow — {timestamp}*",
        "price_block": "🌞 **Price Overview**",
        "notes_block": "🧘 **Thesis Signals**",
        "divider": "🌊🌊🌊🌊🌊",
        "closing": "🪷 *Stay patient. Stay informed.*"
    }
}

def generate_summary(symbol, style="minimalist_pro"):
    # Load style config
    config = STYLE_CONFIG.get(style, STYLE_CONFIG["minimalist_pro"])

    # Price
    price_info = fetch_price(symbol)

    # News
    articles = fetch_from_gnews(symbol)
    if not articles:
        articles = fetch_from_newsapi(symbol)

    if not articles:
        news_summary = """
**Stock Update** (⚖️ Neutral)
- No latest news
**Sector Trend** (⚖️ Neutral)
- No latest news
**Reasons/Drivers** (⚖️ Neutral)
- No latest news
**Result** (⚖️ Neutral)
- No latest news
**Promoter / Big Sell / Acquisition** (⚖️ Neutral)
- No latest news
"""
    else:
        article = articles[0]
        raw = f"- {article['title']}\n  {article['desc']}\n  🔗 {article['url']}"
        prompt = f"""
Summarize this news about {symbol} in the following fixed format, simple layman language:

**Stock Update** (📈/📉/⚖️)
- ...
**Sector Trend** (📈/📉/⚖️)
- ...
**Reasons/Drivers** (📈/📉/⚖️)
- ...
**Result** (📈/📉/⚖️)
- ...
**Promoter / Big Sell / Acquisition** (📈/📉/⚖️)
- ...

News:
{raw}

📅 Date Published: {article['date']}
"""
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        news_summary = response.text

    # Final Message
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist).strftime("%d-%b-%Y %H:%M")

    final_msg = config["header"].format(symbol=symbol, timestamp=now_ist) + "\n\n"

    if price_info:
        final_msg += (
            f"{config['price_block']}\n"
            f"- Current Price: ₹{price_info['price']}\n"
            f"- Change: {price_info['change']}%\n"
            f"- 52W High: ₹{price_info['yhigh']}\n"
            f"- 52W Low: ₹{price_info['ylow']}\n\n"
            f"{config['notes_block']}\n- "
            + "\n- ".join(price_info["investor_notes"])
            + "\n\n"
        )

    final_msg += config["divider"] + "\n\n"
    final_msg += news_summary + "\n\n"
    final_msg += config["closing"]

    return final_msg


def send_to_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram config missing.")
        return
    send_text = (
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        f"?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(message)}"
    )
    resp = requests.get(send_text)
    if resp.status_code == 200:
        print(f"Summary for {symbol} sent to Telegram successfully!")
    else:
        print(f"Failed to send summary for {symbol}:", resp.text)


# === Main Loop for all stocks ===
# === Main Loop ===
for symbol in SYMBOLS:
    print(f"🔄 Processing {symbol}")
    summary = generate_summary(symbol, style="zen_flow")
    print(summary)
    send_to_telegram(summary)
    time.sleep(20)
