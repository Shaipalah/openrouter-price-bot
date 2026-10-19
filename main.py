import requests
import json
import os

# --- НАСТРОЙКИ ---
TARGET_MODEL = "z-ai/glm-5.2"
TARGET_PROVIDER = "Baidu"
TARGET_QUANTS = ["fp4", "fp8"]
MIN_DISCOUNT_PERCENT = 5  # Игнорировать изменения меньше 5% (шум)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "price_state.json"

def format_price(price_per_token):
    """Переводит цену за токен в доллары за 1 миллион токенов."""
    price_per_million = price_per_token * 1_000_000
    # Если цена совсем маленькая (например, 0.00189), показываем 3 знака после запятой
    if price_per_million < 0.01:
        return f"${price_per_million:.4f}"
    return f"${price_per_million:.2f}"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    print(f"ОТВЕТ TELEGRAM: {response.status_code}")

def get_prices():
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
                if quant not in result or price < result[quant]:
                    result[quant] = price
    except Exception as e:
        print("Ошибка:", e)
    return result

def main():
    prices = get_prices()
    if not prices:
        print("Ничего не найдено.")
        return

    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            state = {}

    for quant in TARGET_QUANTS:
        if quant not in prices:
            continue

        current = prices[quant]
        key = f"{TARGET_MODEL}_{TARGET_PROVIDER}_{quant}"
        entry = state.get(key, {})
        last_price = entry.get("price")
        discount_active = entry.get("discount_active", False)

        if last_price is not None:
            # Если цена упала
            if current < last_price:
                drop_percent = ((last_price - current) / last_price) * 100
                if drop_percent >= MIN_DISCOUNT_PERCENT:
                    msg = f"🔥 Скидка! {TARGET_MODEL} ({quant})\n"
                    msg += f"Было: {format_price(last_price)} за 1М токенов\n"
                    msg += f"Стало: {format_price(current)} за 1М токенов\n"
                    msg += f"Падение: -{drop_percent:.1f}%"
                    send_telegram(msg)
                    discount_active = True
            
            # Если цена выросла (скидка закончилась)
            elif current > last_price and discount_active:
                rise_percent = ((current - last_price) / last_price) * 100
                msg = f"😢 Скидка закончилась. {TARGET_MODEL} ({quant})\n"
                msg += f"Было: {format_price(last_price)}\n"
                msg += f"Стало: {format_price(current)}\n"
                msg += f"Подорожание: +{rise_percent:.1f}%"
                send_telegram(msg)
                discount_active = False
            
            # Если изменение незначительное (шум)
            else:
                print(f"{quant}: цена не изменилась или изменение слишком мелкое.")

        # Обновляем состояние для следующего раза
        state[key] = {"price": current, "discount_active": discount_active}

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    main()
