# Stock Summary Generator

This Python script generates a morning brief for stock (TCS) including current price, 52-week high/low, and relevant news summary using Gemini AI. The summary is then sent to a Telegram channel.

## Features

- Fetches real-time stock price data from Indian Stock Exchange API
- Generates AI-powered summaries of stock news using Google's Gemini AI
- Sends automated updates to Telegram
- Supports custom configuration through settings file

## Setup

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Configure settings in `config/settings.py`:
   - Update API keys
   - Configure stock symbol
   - Set Telegram bot token and chat ID

3. Run the script:
```bash
python src/stock_summary.py
```

## Configuration

All configuration settings are stored in `config/settings.py`:
- Stock symbol
- API credentials
- Telegram bot settings

## Dependencies

- requests: For making HTTP requests
- google-generativeai: For AI-powered news summarization
- pytz: For handling timezone conversions
