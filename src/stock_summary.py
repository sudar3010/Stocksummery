import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime
import google.generativeai as genai
import urllib.parse
import pytz
from config.settings import SYMBOL, PRICE_API_URL, PRICE_API_HEADERS, NEWS_API_URL, NEWS_API_PARAMS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID




# === GEMINI CONFIG ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAolmRW2NKcmqd83Z-lnLp2oyNiocSm3c8"))

prompt_instruction = """
You are a financial news summarizer. Create a concise 'Morning Brief' report for the given stock, using clear layman-friendly language. Follow this structure:

1. **Header**  
   Format: === {STOCK_SYMBOL} Morning Brief — {DATE TIME} ===

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

Now use the above rules to summarize this data:
"""

# Get current IST time
ist = pytz.timezone('Asia/Kolkata')
now_ist = datetime.now(ist)
date_str = now_ist.strftime('%a, %d %b %Y %I:%M %p IST')
print("---->",date_str)

# === FETCH PRICE ===
price_resp = requests.get(PRICE_API_URL, headers=PRICE_API_HEADERS)
price_data = price_resp.json()
last_price = price_data.get("last_price") or price_data.get("price")

# === EXTRACT COMPANY PRICE INFO FROM peerCompanyList ===
peer_companies = []
if "peerCompanyList" in price_data:
    peer_companies = price_data["peerCompanyList"]
elif "companyProfile" in price_data and "peerCompanyList" in price_data["companyProfile"]:
    peer_companies = price_data["companyProfile"]["peerCompanyList"]
elif "stockDetailsReusableData" in price_data and "peerCompanyList" in price_data["stockDetailsReusableData"]:
    peer_companies = price_data["stockDetailsReusableData"]["peerCompanyList"]

company_info = None
for company in peer_companies:
    if company.get("companyName") == "Tata Consultancy Services":
        company_info = company
        break

# === EXTRACT TOP 3 RECENT NEWS FROM PRICE DATA ===
recent_news = price_data.get("recentNews", [])
news_content = ""
if company_info:
    news_content += (
        f"{company_info['companyName']}:\n"
        f"Current Price: ₹{company_info['price']}\n"
        f"52 Week High: ₹{company_info['yhigh']}\n"
        f"52 Week Low: ₹{company_info['ylow']}\n\n"
    )
if recent_news:
    news_content += "Top 3 Recent News from Price API:\n"
    for news in recent_news[:3]:
        news_content += f"- {news['headline']} ({news['date']})\n"
        news_content += f"  {news['intro']}\n"
        news_content += f"  {news['url']}\n"
else:
    news_content += "No recent news found in price data.\n"

# === GEMINI SUMMARIZATION ===
full_prompt = f"{prompt_instruction}\n{news_content}"
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(full_prompt)



# === DISPLAY ALL RESULTS ===
if company_info:
    print(f"\n=== {SYMBOL} Morning Brief — {date_str} ===")
    print(f"Price info for {company_info['companyName']}:")
    print(f"Current Price: ₹{company_info['price']}")
    print(f"52 Week High: ₹{company_info['yhigh']}")
    print(f"52 Week Low: ₹{company_info['ylow']}")
else:
    print(f"\n=== {SYMBOL} Morning Brief — {date_str} ===")
    print("No price info found for Tata Consultancy Services.")

print("\nSummary:\n" + response.text)


# === SEND SUMMARY TO TELEGRAM ===
telegram_message = response.text

send_text = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    f"?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(telegram_message)}"
)

resp = requests.get(send_text)
if resp.status_code == 200:
    print("Summary sent to Telegram successfully!")
else:
    print("Failed to send summary to Telegram:", resp.text)
