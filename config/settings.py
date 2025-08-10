import os

# Stock Configuration
SYMBOL = "TCS"   # NSE/BSE symbol of your stock

# API Configuration
PRICE_API_URL = f"https://indian-stock-exchange-api2.p.rapidapi.com/stock?name={SYMBOL}"
PRICE_API_HEADERS = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
    "X-RapidAPI-Host": "indian-stock-exchange-api2.p.rapidapi.com"
}

NEWS_API_URL = "https://newsapi.org/v2/everything"
NEWS_API_PARAMS = {
    "q": "TCS",
    "language": "en",
    "sortBy": "publishedAt",
    "apiKey": os.getenv("NEWS_API_KEY")
}

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")