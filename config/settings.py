import os

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

GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
