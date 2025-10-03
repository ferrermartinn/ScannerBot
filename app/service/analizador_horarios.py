import os
import time
import hmac
import hashlib
import requests
import threading
from dotenv import load_dotenv
import telebot

# ======================
# CARGAR VARIABLES ENTORNO
# ======================
load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MIS_USUARIOS = [u.strip().lower() for u in os.getenv('MIS_USUARIOS', '').split(',') if u.strip()]

# ======================
# CONFIGURACIÓN SCANNER
# ======================
FIAT = "ARS"
POZO_REF_USD = 400
MIN_REF = 100000
COMISION_MAKER = 0.2
ROWS = 10
MONEDAS = ["USDT", "BTC", "ETH", "XRP"]

# ======================
# VARIABLES GLOBALES
# ======================
last_best_buy = {}
last_best_sell = {}
spot_cache = {}

# ======================
# ARCHIVO PARA GUARDAR ESTADO
# ======================
ESTADO_FILE = "estado_operacion.txt"

def cargar_estado():
    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, "r") as f:
            estado = f.read().strip()
            return estado.lower() == "true"
    return False

def guardar_estado(valor):
    with open(ESTADO_FILE, "w") as f:
        f.write("true" if valor else "false")

modo_operacion = cargar_estado()  # 🔇 Se carga el estado guardado

MAX_CALLS_PER_MIN = 120
calls_this_min = 0
start_time = time.time()

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ======================
# FUNCIONES BINANCE P2P
# ======================
def sign_payload(payload: dict) -> dict:
    query_string = "&".join([f"{k}={v}" for k, v in payload.items()])
    signature = hmac.new(
        BINANCE_API_SECRET.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()
    payload["signature"] = signature
    return payload

def get_spot_price(asset):
    if asset in spot_cache:
        return spot_cache[asset]
    if asset == "USDT":
        url_ars = "https://api.binance.com/api/v3/ticker/price?symbol=USDTARS"
        resp_ars = requests.get(url_ars).json()
        price = float(resp_ars["price"])
    else:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={asset}USDT"
        price_usd = float(requests.get(url).json()["price"])
        url_ars = "https://api.binance.com/api/v3/ticker/price?symbol=USDTARS"
        price = price_usd * float(requests.get(url_ars).json()["price"])
    spot_cache[asset] = price
    return price

def get_p2p_offers(asset="USDT", fiat="ARS", trade_type="SELL", rows=10):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://p2p.binance.com",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "asset": asset,
        "fiat": fiat,
        "merchantCheck": False,
        "page": 1,
        "rows": rows,
        "tradeType": trade_type,
        "payTypes": [],
        "publisherType": None
    }
    resp = requests.post(url, headers=headers, json=payload).json()
    data = resp.get("data", [])
    offers = []
    for item in data:
        adv = item["adv"]
        offers.append({
            "nickName": item["advertiser"]["nickName"],
            "price": float(adv["price"]),
            "minAmount": float(adv["minSingleTransAmount"]),
            "maxAmount": float(adv["maxSingleTransAmount"]),
            "totalAmount": float(adv["surplusAmount"]),
            "payTypes": adv["tradeMethods"]
        })
    return offers

# ======================
# FUNCIONES SCANNER
# ======================
def calculate_price(my_type, competitor_price):
    step = 0.01
    return competitor_price - step if my_type == "SELL" else competitor_price + step

def calculate_profit(price_buy, price_sell):
    bruto_percent = (price_sell - price_buy) / price_buy * 100
    neto_percent = bruto_percent - COMISION_MAKER
    return neto_percent

def main_scanner():
    global spot_cache
    while True:
        spot_cache = {}
        message_all = ""
        usdt_ars = get_spot_price("USDT")
        if usdt_ars is None:
            continue

        for asset in MONEDAS:
            asset_ars = get_spot_price(asset)
            if asset_ars is None:
                continue

            sellers = get_p2p_offers(asset, FIAT, "SELL", ROWS)
            buyers = get_p2p_offers(asset, FIAT, "BUY", ROWS)
            if not sellers or not buyers:
                continue

            best_competitor_buy = min(sellers, key=lambda x: x["price"])
            best_competitor_sell = max(buyers, key=lambda x: x["price"])

            my_price_buy = calculate_price("BUY", best_competitor_buy["price"])
            my_price_sell = calculate_price("SELL", best_competitor_sell["price"])

            profit = calculate_profit(my_price_buy, my_price_sell)

            message_all += f"💰 *{asset}*\n"
            message_all += f"💚 COMPRAR: {best_competitor_buy['nickName']} `{best_competitor_buy['price']:.2f}` → *{my_price_buy:.2f}*\n"
            message_all += f"🔴 VENDER: {best_competitor_sell['nickName']} `{best_competitor_sell['price']:.2f}` → *{my_price_sell:.2f}*\n"
            message_all += f"💹 Ganancia neta: *{profit:.2f}%*\n\n"

        # Solo envía si el modo_operacion está activo
        if modo_operacion and message_all:
            bot.send_message(TELEGRAM_CHAT_ID, message_all, parse_mode="Markdown")

        time.sleep(30)

# ======================
# HANDLERS TELEGRAM
# ======================
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "operar")
def activar_operacion(message):
    global modo_operacion
    modo_operacion = True
    guardar_estado(True)
    bot.reply_to(message, "✅ Modo operación ACTIVADO y guardado.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "parar")
def desactivar_operacion(message):
    global modo_operacion
    modo_operacion = False
    guardar_estado(False)
    bot.reply_to(message, "🛑 Modo operación DESACTIVADO y guardado.")

# ======================
# EJECUCIÓN EN PARALELO
# ======================
if __name__ == "__main__":
    import threading
    threading.Thread(target=main_scanner, daemon=True).start()
    bot.infinity_polling()
