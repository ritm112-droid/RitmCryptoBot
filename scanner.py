from binance.client import Client
import pandas as pd
import requests
import time

# ================= TELEGRAM =================

BOT_TOKEN = "8775014015:AAHdDIZ6O868NMGrS3_8uHBnafwihe29LnA"
CHAT_ID = "6815963349"


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=20
            )

            print("Telegram response:", response.status_code, response.text)

            if response.status_code == 200:
                return True

        except Exception as e:
            print(f"Ошибка Telegram, попытка {attempt + 1}: {e}")
            time.sleep(3)

    return False


# ================= BINANCE =================

client = Client()

# Защита от дублей
sent_signals = {}

exchange_info = client.futures_exchange_info()
tickers = client.futures_ticker()

symbols = []

for s in exchange_info["symbols"]:

    if (
        s["status"] == "TRADING"
        and s["quoteAsset"] == "USDT"
    ):

        symbol = s["symbol"]

        ticker = next(
            (t for t in tickers if t["symbol"] == symbol),
            None
        )

        if ticker:

            quote_volume = float(ticker["quoteVolume"])

            if quote_volume >= 5_000_000:
                symbols.append(symbol)

def check_signal(symbol):
    try:
        klines = client.futures_klines(
            symbol=symbol,
            interval="1m",
            limit=250
        )

        df = pd.DataFrame(klines)

        df["close"] = df[4].astype(float)
        df["high"] = df[2].astype(float)
        df["low"] = df[3].astype(float)
        df["volume"] = df[5].astype(float)

        df["ema200"] = df["close"].ewm(span=200).mean()

        last = df.iloc[-1]

        bull_trend = last["close"] > last["ema200"]
        bear_trend = last["close"] < last["ema200"]

        avg_volume = df["volume"].tail(20).mean()
        volume_spike = last["volume"] > avg_volume * 1.3

        highest_high = df["high"].tail(20).max()
        lowest_low = df["low"].tail(20).min()

        sweep_high = last["high"] >= highest_high
        sweep_low = last["low"] <= lowest_low

        long_signal = sweep_low and volume_spike and bull_trend
        short_signal = sweep_high and volume_spike and bear_trend

        if long_signal:
            signal_key = f"{symbol}_LONG"

            if signal_key not in sent_signals:
                message = f"""
🚀 LONG

Монета: {symbol}
Цена: {round(last['close'], 6)}

EMA200: ✅
Volume Spike: ✅
Liquidity Sweep: ✅
"""
                print(message)
                send_telegram(message)
                sent_signals[signal_key] = time.time()

        if short_signal:
            signal_key = f"{symbol}_SHORT"

            if signal_key not in sent_signals:
                message = f"""
🔻 SHORT

Монета: {symbol}
Цена: {round(last['close'], 6)}

EMA200: ✅
Volume Spike: ✅
Liquidity Sweep: ✅
"""
                print(message)
                send_telegram(message)
                sent_signals[signal_key] = time.time()

    except Exception as e:
        print(f"Ошибка {symbol}: {e}")


while True:
    print()
    print("Начинаю новое сканирование...")
    print()

    for symbol in symbols:
        check_signal(symbol)

    now = time.time()
    expired = []

    for key, timestamp in sent_signals.items():
        if now - timestamp > 1800:
            expired.append(key)

    for key in expired:
        del sent_signals[key]

    print()
    print("Сканирование завершено")
    print("Ожидание 60 секунд...")
    print()

    time.sleep(60)