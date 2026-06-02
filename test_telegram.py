import requests

BOT_TOKEN = "8775014015:AAHWE6UyW75wzvYHKzOOB18XzzySFFASWtc"
CHAT_ID = "6815963349"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

response = requests.post(
    url,
    json={
        "chat_id": CHAT_ID,
        "text": "🚀 Тестовое сообщение от RitmCryptoBot"
    }
)

print(response.text)