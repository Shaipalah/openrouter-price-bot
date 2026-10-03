import requests
import json
import os

# --- НАСТРОЙКИ (ВПИШИ СВОИ ЗНАЧЕНИЯ) ---
TARGET_MODEL = "z-ai/glm-5.2"   # ID модели
TARGET_PROVIDER = "Baidu Qianfan"          # Имя провайдера (например, Together, Fireworks, DeepInfra)

TELEGRAM_TOKEN = os.environ.get("8732449791:AAGw1eh5RFGkrtxJcnbhmv_OMk6DWL_46Xs")
TELEGRAM_CHAT_ID = os.environ.get("6581546308")
PRICE_FILE = "last_price.json"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_price():
    try:
        res = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        res.raise_for_status()
        for model in res.json()["data"]:
            if model["id"] == TARGET_MODEL:
                # Ищем конкретного провайдера в списке endpoints
                for endpoint in model.get("endpoints", []):
                    if endpoint.get("provider_name") == TARGET_PROVIDER:
                        return float(endpoint["pricing"]["prompt"])
    except Exception as e:
        print("Ошибка при запросе:", e)
    return None

def main():
    current = get_price()
    if current is None:
        print(f"Модель {TARGET_MODEL} или провайдер {TARGET_PROVIDER} не найдены.")
        return

    last = None
    if os.path.exists(PRICE_FILE):
        with open(PRICE_FILE, "r") as f:
            data = json.load(f)
            last = data.get(f"{TARGET_MODEL}_{TARGET_PROVIDER}")

    if last is not None and current < last:
        msg = f"🔥 Скидка у {TARGET_PROVIDER}!\nМодель: {TARGET_MODEL}\nБыло: {last} USD\nСтало: {current} USD"
        send_telegram(msg)
        print(msg)
    else:
        print(f"Цена не изменилась. Текущая: {current}")

    with open(PRICE_FILE, "w") as f:
        json.dump({f"{TARGET_MODEL}_{TARGET_PROVIDER}": current}, f)

if __name__ == "__main__":
    main()
