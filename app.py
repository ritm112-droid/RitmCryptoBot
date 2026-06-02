from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = "8775014015:AAHdDIZ6O868NMGrS3_8uHBnafwihe29LnA"
CHAT_ID = "6815963349"


def send_telegram(text):

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text
        }
    )

    print("TELEGRAM RESPONSE:")
    print(response.text)


@app.route("/")
def home():
    return "Server Online"


@app.route("/test")
def test():
    send_telegram("🚀 Тест от Flask")
    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():

    print("WEBHOOK СРАБОТАЛ")

    data = request.json or {}

    print(data)

    symbol = data.get("symbol", "UNKNOWN")
    price = data.get("price", "0")
    side = data.get("side", "SIGNAL")

    message = f"{side}\n\nМонета: {symbol}\nЦена: {price}"

    send_telegram(message)

    return {"status": "ok"}

@app.route("/test_webhook")
def test_webhook():

    message = "🚀 LONG\n\nМонета: BTCUSDT\nЦена: 105000"

    send_telegram(message)

    return "Webhook Test OK"    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)