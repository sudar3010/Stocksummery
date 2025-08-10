import os

# Stock Configuration
SYMBOL = "TCS"   # NSE/BSE symbol of your stock

# API Configuration
PRICE_API_URL = f"https://indian-stock-exchange-api2.p.rapidapi.com/stock?name={SYMBOL}"
PRICE_API_HEADERS = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY", "701d4da0e2msh9fb6b21538296c5p1e194fjsn9e4ee7a6c936"),
    "X-RapidAPI-Host": "indian-stock-exchange-api2.p.rapidapi.com"
}

NEWS_API_URL = "https://newsapi.org/v2/everything"
NEWS_API_PARAMS = {
    "q": "TCS",
    "language": "en",
    "sortBy": "publishedAt",
    "apiKey": os.getenv("NEWS_API_KEY", "3ae1e0aeff514f348eb78a8101af020c")
}

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8108841318:AAE8aoEPqOU6SrwzRvtAjOQAG9AjD2IT2NI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "583577008")
