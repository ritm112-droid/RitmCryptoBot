import pandas as pd
import requests
import time

BOT_TOKEN = "8775014015:AAHdDIZ6O868NMGrS3_8uHBnafwihe29LnA"
CHAT_ID = "6815963349"

INTERVAL = "1"
KLINE_LIMIT = 250
VOLUME_MULTIPLIER = 1.3
MIN_24H_VOLUME = 5_000_000
DUPLICATE_TIMEOUT = 1800

session = HTTP(testnet=False)
sent_signals = {}


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                json={"chat_id": CHAT_ID, "text": text},
                timeout=20
            )
            print("Telegram response:", response.status_code, response.text)

            if response.status_code == 200:
                return True

        except Exception as e:
            print(f"Ошибка Telegram, попытка {attempt + 1}: {e}")
            time.sleep(3)

    return False


def get_symbols():
    symbols = []
    cursor = None

    while True:
        params = {
            "category": "linear",
            "limit": 1000
        }

        if cursor:
            params["cursor"] = cursor

        data = session.get_instruments_info(**params)
        result = data.get("result", {})
        items = result.get("list", [])

        for item in items:
            symbol = item.get("symbol")
            status = item.get("status")
            quote_coin = item.get("quoteCoin")

            if status == "Trading" and quote_coin == "USDT":
                symbols.append(symbol)

        cursor = result.get("nextPageCursor")

        if not cursor:
            break

    return symbols


def get_24h_volume_map():
    volume_map = {}

    data = session.get_tickers(category="linear")
    items = data.get("result", {}).get("list", [])

    for item in items:
        symbol = item.get("symbol")

        try:
            turnover_24h = float(item.get("turnover24h", 0))
        except Exception:
            turnover_24h = 0

        volume_map[symbol] = turnover_24h

    return volume_map


def check_signal(symbol, volume_24h):
    try:
        if volume_24h < MIN_24H_VOLUME:
            return

        data = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=INTERVAL,
            limit=KLINE_LIMIT
        )

        candles = data.get("result", {}).get("list", [])

        if len(candles) < 220:
            return

        df = pd.DataFrame(
            candles,
            columns=[
                "startTime",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "turnover"
            ]
        )

        df = df.iloc[::-1].reset_index(drop=True)

        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        df["ema200"] = df["close"].ewm(span=200).mean()

        last = df.iloc[-1]

        bull_trend = last["close"] > last["ema200"]
        bear_trend = last["close"] < last["ema200"]

        avg_volume = df["volume"].tail(20).mean()
        volume_spike = last["volume"] > avg_volume * VOLUME_MULTIPLIER

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

Биржа: Bybit Futures
Монета: {symbol}
Цена: {round(last["close"], 6)}

24h Volume: ${volume_24h:,.0f}

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

Биржа: Bybit Futures
Монета: {symbol}
Цена: {round(last["close"], 6)}

24h Volume: ${volume_24h:,.0f}

EMA200: ✅
Volume Spike: ✅
Liquidity Sweep: ✅
"""
                print(message)
                send_telegram(message)
                sent_signals[signal_key] = time.time()

    except Exception as e:
        print(f"Ошибка {symbol}: {e}")


def clean_old_signals():
    now = time.time()
    expired = []

    for key, timestamp in sent_signals.items():
        if now - timestamp > DUPLICATE_TIMEOUT:
            expired.append(key)

    for key in expired:
        del sent_signals[key]


symbols = get_symbols()
print("Найдено Bybit USDT Futures:", len(symbols))

while True:
    print()
    print("Начинаю новое сканирование Bybit...")
    print()

    volume_map = get_24h_volume_map()

    for symbol in symbols:
        check_signal(symbol, volume_map.get(symbol, 0))

    clean_old_signals()

    print()
    print("Сканирование завершено")
    print("Ожидание 60 секунд...")
    print()

    time.sleep(60)