import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime
import google.generativeai as genai
import urllib.parse
import pytz
from config.settings import  PRICE_API_HEADERS, NEWS_API_URL, NEWS_API_PARAMS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from dateutil import parser

# Multiple Stock Symbols
SYMBOLS = ["TCS","ITC","ICICI","tata steel","KTKBANK"]

ist = pytz.timezone('Asia/Kolkata')
current_dt = datetime.now(ist).strftime("%d-%b-%Y %H:%M")

print(f"Total symbols to process: {len(SYMBOLS)}")
# === GEMINI CONFIG ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAolmRW2NKcmqd83Z-lnLp2oyNiocSm3c8"))

prompt_instruction = f"""
You are a financial news summarizer. Create a concise 'Morning Brief' report for the given stock, using clear layman-friendly language. Follow this structure:

1. **Header**  
    Format: === {{STOCK_SYMBOL}} Morning Brief — {current_dt} ===

2. **Price Block**  
   - Show current price in ₹ (2 decimals)
   - If available, show price change from previous close with absolute ₹ difference and % in parentheses (e.g., +₹15.20 (+0.5%))
   - 52-week high and low values

3. **Summary Section**  
   Title: 📌 Summary:  
   Use 3–5 bullet points. Each bullet should:
   - Present one key news item or market move
   - Keep sentences short and plain
   - Explain any financial term in brackets if it's not obvious
   - Preserve important numbers, % changes, dates, and names
   - Add a relevant emoji at the start (e.g., 📉, 📈, 💼, 📰)

Make sure:
- Avoid jargon; if you must use it, explain briefly in brackets.
- Output must be clear and easy to scan for a non-finance person.
- Keep overall length compact while retaining all critical facts.
- keep Date of each statement in the summary.
Now use the above rules to summarize this data:
"""

# Get current IST time
ist = pytz.timezone('Asia/Kolkata')
now_ist = datetime.now(ist)
date_str = now_ist.strftime('%a, %d %b %Y %I:%M %p IST')
print("---->",date_str)

def process_stock(symbol):
    print(f"\nProcessing {symbol}...")
    
    # === PRICE API CALL ===
    price_api_url = f"https://indian-stock-exchange-api2.p.rapidapi.com/stock?name={symbol}"
    price_resp = requests.get(price_api_url, headers=PRICE_API_HEADERS)
    price_data = price_resp.json()
    
    # === Extract company info ===
    company_info = None
    peer_companies = []
    if "peerCompanyList" in price_data:
        peer_companies = price_data["peerCompanyList"]
    elif "companyProfile" in price_data and "peerCompanyList" in price_data["companyProfile"]:
        peer_companies = price_data["companyProfile"]["peerCompanyList"]
    elif "stockDetailsReusableData" in price_data and "peerCompanyList" in price_data["stockDetailsReusableData"]:
        peer_companies = price_data["stockDetailsReusableData"]["peerCompanyList"]
    SYMBOL_NAME_MAP = {
    "KTKBANK": "Karnataka Bank",
    "TCS": "Tata Consultancy Services",
    # Add more special cases if needed
}
    for company in peer_companies:
     company_name = company.get("companyName", "").lower()
    
    # If symbol is in special mapping, match by mapped name
     if symbol.upper() in SYMBOL_NAME_MAP:
        if SYMBOL_NAME_MAP[symbol.upper()].lower() in company_name:
            company_info = company
            break
     else:
        # Normal case: match by symbol in name
        if symbol.lower() in company_name:
            company_info = company
            break

    # === Extract news content ===
    news_content = ""
    if company_info:
        news_content += (
            f"{company_info['companyName']}:\n"
            f"Current Price: ₹{company_info['price']}\n"
            f"52 Week High: ₹{company_info['yhigh']}\n"
            f"52 Week Low: ₹{company_info['ylow']}\n\n"
        )
    investor_notes = []
    try:
            price = float(company_info.get("price", 0))
            yhigh = float(company_info.get("yhigh", 0))
            ylow = float(company_info.get("ylow", 0))
            pe = float(company_info.get("priceToEarningsValueRatio", 0))
            pb = float(company_info.get("priceToBookValueRatio", 0))
            roe = float(company_info.get("returnOnAverageEquityTrailing12Month", 0))
            net_margin = float(company_info.get("netProfitMarginPercentTrailing12Month", 0))
            dividend_yield = float(company_info.get("dividendYieldIndicatedAnnualDividend", 0))
            debt_to_equity = float(company_info.get("ltDebtPerEquityMostRecentFiscalYear", 0))
            rating = company_info.get("overallRating", "").capitalize()
            percent_change = float(company_info.get("percentChange", 0))

            if pe < 8 and pb < 1:
                investor_notes.append("💰 Potential Value Buy (Low P/E & P/B)")

            if roe > 10 and net_margin > 20:
                investor_notes.append("📈 Strong Profitability (High ROE & Net Margin)")

            if dividend_yield > 2:
                investor_notes.append(f"💵 Good Dividend Yield ({dividend_yield:.2f}%)")

            if debt_to_equity > 15 and "bank" not in company_info.get("companyName", "").lower():
                investor_notes.append(f"⚠️ High Leverage Risk (Debt/Equity: {debt_to_equity:.2f})")

            if ylow > 0 and ((price - ylow) / ylow) * 100 < 5:
                investor_notes.append("📉 Near 52-Week Low (Possible Buy Opportunity)")
            if price > 0 and ((yhigh - price) / price) * 100 < 5:
                investor_notes.append("📊 Near 52-Week High (Consider Profit Booking)")

            if rating:
                sentiment_emoji = "📈" if rating.lower() == "bullish" else "📉" if rating.lower() == "bearish" else "⚖️"
                investor_notes.append(f"{sentiment_emoji} Market Sentiment: {rating}")

            # Price drop alert
            if percent_change <= -3:
                investor_notes.append(f"🔻 Significant Drop Today ({percent_change:.2f}%) — Review Position")

    except Exception as e:
            print(f"⚠️ Error generating investor notes: {e}")
    

    recent_news = price_data.get("recentNews", [])
    ist = pytz.timezone('Asia/Kolkata')
    if recent_news:
     news_content += "Top 3 Recent News from Price API:\n"

    # Get today's date in IST without time
    today_ist = datetime.now(ist).date()

    count = 0
    for news in recent_news:
        try:
            date_str = news['date']

            # Remove duplicated " IST IST"
            if date_str.endswith("IST IST"):
                date_str = date_str.replace("IST IST", "IST")

            # Fix invalid times like "15:04 PM" or "06:00 AM AM"
            date_str = date_str.replace(" AM AM", " AM").replace(" PM PM", " PM")
            parts = date_str.split()
            for i, p in enumerate(parts):
                if p in ("AM", "PM") and ":" in parts[i-1]:
                    hour = int(parts[i-1].split(":")[0])
                    if hour > 12:  # 24-hour + AM/PM is wrong
                        parts[i] = ""  # remove AM/PM
            date_str = " ".join([p for p in parts if p])

            # Parse with tzinfos for IST
            tzinfos = {"IST": ist}
            news_datetime = parser.parse(date_str, tzinfos=tzinfos).astimezone(ist)
            news_date = news_datetime.date()

            # Keep only if within past 2 days
            if (today_ist - news_date).days <= 2:
                news_content += f"- {news['headline']} ({news['date']})\n"
                news_content += f"  {news['intro']}\n"
                news_content += f"  {news['url']}\n"
                count += 1

            if count >= 3:
                break

        except Exception as e:
            print(f"⚠️ Could not parse date '{news.get('date')}': {e}")



    # === Summarization with Gemini ===
    full_prompt = f"{prompt_instruction}\n{news_content}"
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(full_prompt)

    #=== Send to Telegram ===
        # === Build Telegram Message ===
    telegram_message = f"**📌 Summary:**\n{response.text}\n\n"
    if investor_notes:
        telegram_message += "**💡 Investor Notes:**\n" + "\n".join(investor_notes)
    print("Telegram Message:", telegram_message)
    send_text = (
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        f"?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(telegram_message)}"
    )
    resp = requests.get(send_text)
    if resp.status_code == 200:
        print(f"Summary for {symbol} sent to Telegram successfully!")
    else:
        print(f"Failed to send summary for {symbol}:", resp.text)


# === Main Loop for all stocks ===
for symbol in SYMBOLS:
    print(f"🔄 Starting {symbol}")
    try:
        process_stock(symbol)
        print(f"✅ Finished {symbol}, waiting before next request...")
        time.sleep(20)
    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
