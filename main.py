import requests
import json
import os

# --- НАСТРОЙКИ (ВПИШИ СВОИ ЗНАЧЕНИЯ) ---
TARGET_MODEL = "z-ai/glm-5.2"   # ID модели
TARGET_PROVIDER = "Baidu"          # Имя провайдера (например, Together, Fireworks, DeepInfra)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PRICE_FILE = "last_price.json"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    print(f"ОТВЕТ TELEGRAM: {response.status_code} - {response.text}")

def get_price():
    # Прямой запрос к эндпоинтам конкретной модели
    url = f"https://openrouter.ai/api/v1/models/{TARGET_MODEL}/endpoints"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            print(f"Ошибка API: {res.status_code} - {res.text}")
            return None
            
        data = res.json().get("data", {})
        endpoints = data.get("endpoints", [])
        
        if not endpoints:
            print("❌ Список провайдеров для этой модели пуст (возможно, модель недоступна).")
            return None
            
        print(f"✅ Модель {TARGET_MODEL} найдена. Доступные провайдеры:")
        for endpoint in endpoints:
            prov_name = endpoint.get("provider_name")
            print(f"  🔍 '{prov_name}'")  # Печатаем имя каждого провайдера
            
            if prov_name == TARGET_PROVIDER:
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
