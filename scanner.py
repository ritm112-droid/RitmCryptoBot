import requests
import pandas as pd
import time
import json

BOT_TOKEN = "8775014015:AAHdDIZ6O868NMGrS3_8uHBnafwihe29LnA"
CHAT_ID = "6815963349"

INTERVAL = "1"
KLINE_LIMIT = 250
VOLUME_MULTIPLIER = 1.3
MIN_24H_VOLUME = 5_000_000
DUPLICATE_TIMEOUT = 1800
SCAN_SLEEP = 60

sent_signals = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 RitmCryptoBot/1.0",
    "Accept": "application/json",
}

BASE_URL = "https://api.bybit.com"


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                json={"chat_id": CHAT_ID, "text": text},
                timeout=20
            )
            print("Telegram:", response.status_code)

            if response.status_code == 200:
                return True

        except Exception as e:
            print(f"Ошибка Telegram попытка {attempt + 1}: {e}")
            time.sleep(3)

    return False


def bybit_get(endpoint, params=None):
    url = BASE_URL + endpoint

    for attempt in range(3):
        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=20
            )

            text = response.text.strip()

            if response.status_code != 200:
                print(f"Bybit HTTP {response.status_code}: {text[:200]}")
                time.sleep(3)
                continue

            try:
                data = response.json()
            except json.JSONDecodeError:
                print("Bybit вернул не JSON:")
                print(text[:300])
                time.sleep(3)
                continue

            if data.get("retCode") not in (0, "0"):
                print("Bybit API error:", data)
                time.sleep(3)
                continue

            return data

        except Exception as e:
            print(f"Ошибка Bybit попытка {attempt + 1}: {e}")
            time.sleep(3)

    return None


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

        data = bybit_get("/v5/market/instruments-info", params)

        if not data:
            print("Не удалось получить список монет Bybit")
            return []

        result = data.get("result", {})
        items = result.get("list", [])

        for item in items:
            if item.get("status") == "Trading" and item.get("quoteCoin") == "USDT":
                symbols.append(item.get("symbol"))

        cursor = result.get("nextPageCursor")

        if not cursor:
            break

    return symbols


def get_24h_volume_map():
    volume_map = {}

    data = bybit_get(
        "/v5/market/tickers",
        {"category": "linear"}
    )

    if not data:
        return volume_map

    items = data.get("result", {}).get("list", [])

    for item in items:
        symbol = item.get("symbol")

        try:
            volume_map[symbol] = float(item.get("turnover24h", 0))
        except Exception:
            volume_map[symbol] = 0

    return volume_map


def check_signal(symbol, volume_24h):
    try:
        if volume_24h < MIN_24H_VOLUME:
            return

        data = bybit_get(
            "/v5/market/kline",
            {
                "category": "linear",
                "symbol": symbol,
                "interval": INTERVAL,
                "limit": KLINE_LIMIT
            }
        )

        if not data:
            return

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
            send_signal(symbol, "LONG", last["close"], volume_24h)

        if short_signal:
            send_signal(symbol, "SHORT", last["close"], volume_24h)

    except Exception as e:
        print(f"Ошибка {symbol}: {e}")


def send_signal(symbol, side, price, volume_24h):
    signal_key = f"{symbol}_{side}"

    if signal_key in sent_signals:
        return

    emoji = "🚀" if side == "LONG" else "🔻"

    message = f"""
{emoji} {side}

Биржа: Bybit Futures
Монета: {symbol}
Цена: {round(float(price), 6)}

24h Volume: ${volume_24h:,.0f}

EMA200: ✅
Volume Spike: ✅
Liquidity Sweep: ✅
"""

    print(message)
    send_telegram(message)

    sent_signals[signal_key] = time.time()


def clean_old_signals():
    now = time.time()

    expired = [
        key for key, timestamp in sent_signals.items()
        if now - timestamp > DUPLICATE_TIMEOUT
    ]

    for key in expired:
        del sent_signals[key]


while True:
    print()
    print("Получаю список монет Bybit...")

    symbols = get_symbols()

    if not symbols:
        print("Список монет пустой. Повтор через 60 секунд.")
        time.sleep(60)
        continue

    print("Найдено Bybit USDT Futures:", len(symbols))

    print()
    print("Начинаю новое сканирование Bybit...")
    print()

    volume_map = get_24h_volume_map()

    if not volume_map:
        print("Не удалось получить volume_map. Повтор через 60 секунд.")
        time.sleep(60)
        continue

    for symbol in symbols:
        check_signal(symbol, volume_map.get(symbol, 0))

    clean_old_signals()

    print()
    print("Сканирование завершено")
    print("Ожидание 60 секунд...")
    print()

    time.sleep(SCAN_SLEEP)