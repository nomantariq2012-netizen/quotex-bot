import os
import threading
import time
from flask import Flask
from google import genai
import requests

# --- CONFIGURATIONS ---
TELEGRAM_TOKEN = "7573199859:AAEzX123456789abcdefghijklmnopqrstuv"  apna token yahan dalein
ALLOWED_CHAT_ID = "623456789"  # apni chat id yahan dalein
GEMINI_API_KEY = "AQ.Ab8RN6LHzyt7K8q2MqGYP7g3FDee5a5-sqIN0pnvtQpx23c-XQ"

client = genai.Client(api_key=GEMINI_API_KEY)

# Flask app taake Render free tier active rakhe
app = Flask(__name__)


@app.route("/")
def home():
  return "Quotex Trading Bot is Live and Running!"


SYMBOLS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "USD/CHF": "USDCHF=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "EUR/GBP": "EURGBP=X",
    "AUD/JPY": "AUDJPY=X",
    "GOLD": "GC=X",
    "SILVER": "SI=X",
    "CRUDE OIL": "CL=X",
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
    "SOL/USD": "SOL-USD",
}


def send_telegram(text):
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": ALLOWED_CHAT_ID, "text": text}
  try:
    requests.post(url, json=payload, timeout=5)
  except Exception as e:
    print("Telegram send error:", e)


def get_rsi(prices, period=14):
  if len(prices) < period + 1:
    return None
  gains, losses = 0.0, 0.0
  for i in range(1, period + 1):
    change = prices[i] - prices[i - 1]
    if change > 0:
      gains += change
    else:
      losses += abs(change)
  avg_gain = gains / period
  avg_loss = losses / period

  for i in range(period + 1, len(prices)):
    change = prices[i] - prices[i - 1]
    g = change if change > 0 else 0.0
    l = abs(change) if change < 0 else 0.0
    avg_gain = (avg_gain * (period - 1) + g) / period
    avg_loss = (avg_loss * (period - 1) + l) / period

  if avg_loss == 0:
    return 100.0
  rs = avg_gain / avg_loss
  return 100 - (100 / (1 + rs))


def get_ema(prices, period=50):
  if len(prices) < period:
    return prices[-1] if prices else None
  multiplier = 2 / (period + 1)
  ema = sum(prices[:period]) / period
  for price in prices[period:]:
    ema = (price - ema) * multiplier + ema
  return ema


def fetch_data(symbol):
  url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
  try:
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
    data = res.json()
    result = data["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]

    valid_data = [
        (timestamps[i], closes[i])
        for i in range(len(closes))
        if closes[i] is not None
    ]
    if not valid_data:
      return None, None

    times, prices = zip(*valid_data)
    return list(times), list(prices)
  except:
    return None, None


def analyze_image_bytes(image_bytes):
  try:
    prompt = (
        "Aap aik expert binary options trader hain. Is 1-minute chart screenshot"
        " ko ghaur se dekhein. RSI, Japanese candlestick pattern,"
        " support/resistance levels, aur trend ko dekhte hue batayein: Agli"
        " 1-minute candle BUY (CALL) hogi ya SELL (PUT)? Mujhe clear decision"
        " aur 2 main points mein reason batayein."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, {"mime_type": "image/jpeg", "data": image_bytes}],
    )
    return response.text
  except Exception as e:
    return f"AI Analysis Error: {e}"


def background_auto_scanner():
  print("[+] Background Auto-Scanner Thread Started...")
  last_sig = {}
  active_trades = []

  while True:
    try:
      current_time = time.time()
      for trade in active_trades[:]:
        if current_time >= trade["target_timestamp"]:
          times, prices = fetch_data(SYMBOLS[trade["name"]])
          if prices:
            exit_price = prices[-1]
            entry_price = trade["entry_price"]
            signal_type = trade["type"]
            name = trade["name"]

            is_win = (signal_type == "BUY" and exit_price > entry_price) or (
                signal_type == "SELL" and exit_price < entry_price
            )

            if is_win:
              msg = (
                  f"🟢 [WIN] {name}\nEntry: {entry_price:.4f}\nExit:"
                  f" {exit_price:.4f}"
              )
              send_telegram(msg)
            else:
              mtg_action = (
                  "UP (CALL)" if signal_type == "BUY" else "DOWN (PUT)"
              )
              msg = f"🔴 [LOSS / MTG] {name}\n👉 TAKE MTG NOW: {mtg_action}"
              send_telegram(msg)

          active_trades.remove(trade)

      for name, sym in SYMBOLS.items():
        times, prices = fetch_data(sym)
        if prices and times and len(prices) > 50:
          rsi_1m = get_rsi(prices, 14)
          ema_50 = get_ema(prices, 50)
          price = prices[-1]
          latest_candle_time = times[-1]

          if rsi_1m is not None and ema_50 is not None:
            if name not in last_sig:
              last_sig[name] = None

            if (
                rsi_1m <= 20
                and price >= ema_50
                and last_sig[name] != latest_candle_time
            ):
              msg = (
                  f"🚀 [STRONG BUY SIGNAL]\nAsset: {name}\nPrice:"
                  f" {price:.4f}\nRSI: {rsi_1m:.2f}"
              )
              send_telegram(msg)
              last_sig[name] = latest_candle_time
              active_trades.append({
                  "name": name,
                  "type": "BUY",
                  "entry_price": price,
                  "target_timestamp": latest_candle_time + 60,
              })

            elif (
                rsi_1m >= 80
                and price <= ema_50
                and last_sig[name] != latest_candle_time
            ):
              msg = (
                  f"🔻 [STRONG SELL SIGNAL]\nAsset: {name}\nPrice:"
                  f" {price:.4f}\nRSI: {rsi_1m:.2f}"
              )
              send_telegram(msg)
              last_sig[name] = latest_candle_time
              active_trades.append({
                  "name": name,
                  "type": "SELL",
                  "entry_price": price,
                  "target_timestamp": latest_candle_time + 60,
              })

            elif 40 < rsi_1m < 60:
              last_sig[name] = None
        time.sleep(0.1)
      time.sleep(3)
    except Exception as e:
      print("Scanner error:", e)
      time.sleep(5)


def telegram_listener():
  print("[+] Telegram Listener Thread Started...")
  send_telegram(
      "🤖 Cloud Trading Bot is Online!\n- Auto Scanner Active\n- Send"
      " screenshots anytime for AI analysis."
  )

  last_update_id = 0
  while True:
    try:
      url = (
          f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id"
          " + 1}&timeout=30"
      )
      res = requests.get(url, timeout=35).json()

      if "result" in res:
        for update in res["result"]:
          last_update_id = update["update_id"]

          if "message" in update:
            msg = update["message"]
            chat_id = str(msg["chat"]["id"])

            if chat_id == str(ALLOWED_CHAT_ID):
              if "photo" in msg:
                send_telegram("⏳ Screenshot mil gaya, AI analyze kar raha hai...")

                photo_file_id = msg["photo"][-1]["file_id"]
                file_info_url = (
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={photo_file_id}"
                )
                file_path = requests.get(file_info_url).json()["result"][
                    "file_path"
                ]

                download_url = (
                    f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
                )
                img_data = requests.get(download_url).content

                ai_result = analyze_image_bytes(img_data)
                send_telegram(f"📊 AI CHART ANALYSIS:\n\n{ai_result}")
              elif "text" in msg:
                send_telegram(
                    "Bot cloud par active hai! Market scan ho rahi hai, ya aap"
                    " chart ka screenshot bhej sakte hain."
                )
    except Exception as e:
      print("Telegram listener error:", e)
      time.sleep(2)


if __name__ == "__main__":
  # Background threads start karna
  t1 = threading.Thread(target=background_auto_scanner)
  t2 = threading.Thread(target=telegram_listener)

  t1.daemon = True
  t2.daemon = True

  t1.start()
  t2.start()

  # Flask web server start karna taake Render service active rahe
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
