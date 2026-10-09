import requests
import json
import os

# --- НАСТРОЙКИ ---
TARGET_MODEL = "z-ai/glm-5.2"
TARGET_PROVIDER = "Baidu"
TARGET_QUANTS = ["fp4", "fp8"]   # отслеживаем оба квантования
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "price_state.json"


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    print(f"ОТВЕТ TELEGRAM: {response.status_code}")


def get_prices():
    """Возвращает {квантование: цена} для всех интересующих нас вариантов."""
    url = f"https://openrouter.ai/api/v1/models/{TARGET_MODEL}/endpoints"
    result = {}
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            print(f"Ошибка API: {res.status_code}")
            return result

        data = res.json().get("data", {})
        endpoints = data.get("endpoints", [])

        for endpoint in endpoints:
            if endpoint.get("provider_name") != TARGET_PROVIDER:
                continue
            quant = (endpoint.get("quantization") or "").lower()
            if quant in TARGET_QUANTS:
                price = float(endpoint["pricing"]["prompt"])
                # Если по одному квантованию несколько вариантов — берем самый дешевый
                if quant not in result or price < result[quant]:
                    result[quant] = price
                    print(f"  🔍 {quant}: цена={price}")
    except Exception as e:
        print("Ошибка:", e)
    return result


def main():
    prices = get_prices()
    if not prices:
        print("Ничего не найдено.")
        return

    # Загружаем состояние
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            state = {}

    for quant in TARGET_QUANTS:
        if quant not in prices:
            print(f"⚠️ Квантование {quant} не найдено у {TARGET_PROVIDER}.")
            continue

        current = prices[quant]
        key = f"{TARGET_MODEL}_{TARGET_PROVIDER}_{quant}"
        entry = state.get(key, {})
        last_price = entry.get("price")
        discount_active = entry.get("discount_active", False)

        # Логика уведомлений
        if last_price is not None:
            if current < last_price and not discount_active:
                send_telegram(
                    f"🔥 Скидка! {TARGET_MODEL} ({quant})\n"
                    f"Было: {last_price}\nСтало: {current}"
                )
                discount_active = True
            elif current > last_price and discount_active:
                send_telegram(
                    f"😢 Скидка закончилась. {TARGET_MODEL} ({quant})\n"
                    f"Было: {last_price}\nСтало: {current}"
                )
                discount_active = False
            else:
                print(f"{quant}: цена не изменилась ({current}).")
        else:
            print(f"{quant}: первое сохранение цены ({current}).")

        # Обновляем состояние
        state[key] = {"price": current, "discount_active": discount_active}

    # Сохраняем
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()
