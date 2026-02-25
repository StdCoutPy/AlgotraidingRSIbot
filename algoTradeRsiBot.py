import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# ================= НАСТРОЙКИ =================
API_TOKEN = 'YourToken'
CHAT_ID = 'YourChatTgId'
PAIRS = ['EURUSD=X', 'CHFJPY=X', 'CADJPY=X', 'EURGBP=X', 'GBPCHF=X', 'EURCAD=X', 'USDJPY=X']
TIMEFRAME = '15m'
RSI_PERIOD = 14
RSI_OVERBOUGHT = 72
RSI_OVERSOLD = 29
CHECK_INTERVAL = 60
# =============================================

# Используем IP прокси напрямую для обхода ошибок DNS
PROXY_URL = "http://10.0.0.1:3128"
PROXIES = {'http': PROXY_URL, 'https': PROXY_URL}


def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        # Пробуем через прокси по IP
        r = requests.post(url, json=payload, proxies=PROXIES, timeout=10)
        return r.status_code == 200
    except:
        try:
            # Пробуем напрямую (на случай если прокси не нужен)
            r = requests.post(url, json=payload, timeout=10)
            return r.status_code == 200
        except:
            return False


def calculate_rsi(series, period=14):
    if series is None or len(series) < period: return None
    delta = series.diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period - 1, adjust=False).mean()
    ma_down = down.ewm(com=period - 1, adjust=False).mean()
    rsi = 100 - (100 / (1 + ma_up / ma_down.replace(0, 1e-10)))
    return rsi


def run_bot():
    print(f"[{datetime.now()}] Бот запускается...")

    if send_telegram_msg("🚀 Бот запущен! DNS-фикс применен."):
        print("Успех: Тестовое сообщение отправлено.")
    else:
        print("Внимание: Сообщение в TG не ушло, проверьте токен.")

    last_candle_time = {pair: None for pair in PAIRS}

    while True:
        # Пропуск выходных
        if datetime.now().weekday() >= 5:
            print("Рынок закрыт. Спим...")
            time.sleep(3600);
            continue

        for pair in PAIRS:
            try:
                # Качаем данные БЕЗ передачи сессии (yfinance сам разберется)
                ticker = yf.Ticker(pair)
                # Передаем прокси через аргумент (если версия поддерживает)
                # или полагаемся на автонастройку
                df = ticker.history(period="3d", interval=TIMEFRAME)

                if df is None or df.empty:
                    continue

                rsi_values = calculate_rsi(df['Close'], RSI_PERIOD)
                if rsi_values is None: continue

                current_rsi = rsi_values.iloc[-1]
                current_time = df.index[-1]

                if last_candle_time.get(pair) != current_time:
                    last_candle_time[pair] = current_time
                    print(f"{datetime.now().strftime('%H:%M')} | {pair} | RSI: {current_rsi:.2f}")

                    if current_rsi > RSI_OVERBOUGHT:
                        send_telegram_msg(f"⚠️ {pair} Перекупленность: {current_rsi:.2f}")
                    elif current_rsi < RSI_OVERSOLD:
                        send_telegram_msg(f"✅ {pair} Перепроданность: {current_rsi:.2f}")

            except Exception as e:
                print(f"Ошибка пары {pair}: {e}")
                continue

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_bot()
