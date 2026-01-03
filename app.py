import os
from datetime import datetime
import threading
import time

import requests
import telebot
from telebot import types
from flask import Flask, request

# ============ CẤU HÌNH ============

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN")

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

REG_LINK = "https://u888u.online"
WEBAPP_LINK = "https://u888u.online"
CSKH_LINK = "https://t.me/my_oanh_u888"

LIVE_LINK = "https://live.u88899.com/"
CODE_LIVESTREAM_LINK = "https://u888code.com/"

# Webhook URL (Render env)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://toolbottele-n0cs.onrender.com/webhook

# Keep-alive nội bộ (không cần nếu đã dùng UptimeRobot)
ENABLE_KEEP_ALIVE = os.getenv("ENABLE_KEEP_ALIVE", "false").lower() == "true"
PING_URL = os.getenv("PING_URL")
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "300"))

# ================== KHỞI TẠO BOT & FLASK ==================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
server = Flask(__name__)

user_state = {}  # {chat_id: "WAITING_USERNAME" hoặc dict}


# ================== HÀM KEEP ALIVE ==================
def keep_alive():
    if not PING_URL:
        print("[KEEP_ALIVE] PING_URL chưa cấu hình, không bật keep-alive.")
        return

    print(f"[KEEP_ALIVE] Bắt đầu ping {PING_URL} mỗi {PING_INTERVAL}s")
    while True:
        try:
            r = requests.get(PING_URL, timeout=10)
            print(f"[KEEP_ALIVE] Ping {PING_URL} -> {r.status_code}")
        except Exception as e:
            print("[KEEP_ALIVE] Lỗi ping:", e)
        time.sleep(PING_INTERVAL)


if ENABLE_KEEP_ALIVE:
    threading.Thread(target=keep_alive, daemon=True).start()


# ================== SET WEBHOOK (quan trọng) ==================
def setup_webhook():
    if not WEBHOOK_URL:
        print("[WEBHOOK] WEBHOOK_URL chưa cấu hình -> bỏ qua set webhook.")
        return
    try:
        bot.remove_webhook()
        time.sleep(1)
        ok = bot.set_webhook(url=WEBHOOK_URL)
        print("[WEBHOOK] set_webhook:", WEBHOOK_URL, "->", ok)
    except Exception as e:
        print("[WEBHOOK] Lỗi set webhook:", e)


# Gọi luôn khi app start (quan trọng cho gunicorn/Render)
setup_webhook()


# ================== HỎI TRẠNG THÁI TÀI KHOẢN ==================
def ask_account_status(chat_id):
    text = (
        "👋 Chào anh/chị!\n"
        "Em là Bot hỗ trợ nhận CODE ưu đãi U888.\n\n"
        "Để em gửi đúng mã và ưu đãi phù hợp, cho em hỏi một chút ạ:\n\n"
        "👉 Anh/chị đã có tài khoản chơi U888 chưa ạ?\n\n"
        "(Chỉ cần bấm nút bên dưới: ĐÃ CÓ hoặc CHƯA CÓ, em hỗ trợ ngay! 😊)"
    )

    markup = types.InlineKeyboardMarkup()
    btn_have = types.InlineKeyboardButton("✅ ĐÃ CÓ TÀI KHOẢN", callback_data="have_account")
    btn_no = types.InlineKeyboardButton("🆕 CHƯA CÓ – ĐĂNG KÝ NGAY", callback_data="no_account")
    markup.row(btn_have)
    markup.row(btn_no)

    try:
        bot.send_photo(
            chat_id,
            "AgACAgUAAxkBAAIBbWkln42l0QufAXVKVmH_Qa6oeFhZAALxDGsbpw8pVY05zyDcJpCbAQADAgADeQADNgQ",
            caption=text,
            reply_markup=markup
        )
    except Exception as e:
        print("Lỗi gửi ảnh ask_account_status:", e)
        bot.send_message(chat_id, text, reply_markup=markup)

    user_state[chat_id] = None


# ================== /start ==================
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    print(">>> /start from:", chat_id)
    ask_account_status(chat_id)


# ================== CALLBACK INLINE ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data
    print(">>> callback:", data, "from", chat_id)

    if data == "no_account":
        text = (
            "Tuyệt vời, em gửi anh/chị link đăng ký nè 👇\n\n"
            f"🔗 Link đăng ký: {REG_LINK}\n\n"
            "Anh/chị đăng ký xong bấm nút bên dưới để em hỗ trợ nhận code nhé."
        )

        markup = types.InlineKeyboardMarkup()
        btn_done = types.InlineKeyboardButton("✅ MÌNH ĐĂNG KÝ XONG RỒI", callback_data="registered_done")
        markup.row(btn_done)

        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        except Exception as e:
            print("Lỗi edit_message_reply_markup:", e)

        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAIBl2klrFRo8Jc_nRjNC5lYhd6W2C7QAAIEDWsbpw8pVU1UjNopuH29AQADAgADeQADNgQ",
                caption=text,
                reply_markup=markup
            )
        except Exception as e:
            print("Lỗi gửi ảnh no_account:", e)
            bot.send_message(chat_id, text, reply_markup=markup)

    elif data in ("have_account", "registered_done"):
        ask_for_username(chat_id)


# ================== HỎI TÊN TÀI KHOẢN ==================
def ask_for_username(chat_id):
    text = (
        "Dạ ok anh/chị ❤️\n\n"
        "Anh/chị vui lòng gửi đúng *tên tài khoản* để em kiểm tra và duyệt code.\n\n"
        "Ví dụ:\n"
        "`Tên tài khoản: abc123`"
    )

    try:
        bot.send_photo(
            chat_id,
            "AgACAgUAAxkBAAIBa2kln2_x2fvUTdTJH7U4Kl2Z-AABUwAC8AxrG6cPKVVZLLurvibZGAEAAwIAA3kAAzYE",
            caption=text,
            parse_mode="Markdown"
        )
    except Exception as e:
        print("Lỗi gửi ảnh ask_for_username:", e)
        bot.send_message(chat_id, text, parse_mode="Markdown")

    user_state[chat_id] = "WAITING_USERNAME"


# ================== XỬ LÝ TIN NHẮN TEXT ==================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()
    print(">>> text:", text, "from", chat_id)

    state = user_state.get(chat_id)

    if isinstance(state, dict) and state.get("state") == "WAITING_GAME":
        four_last_digits = text
        try:
            tg_username = f"@{message.from_user.username}" if message.from_user.username else "Không có"

            bot.send_photo(
                ADMIN_CHAT_ID,
                state["receipt_file_id"],
                caption=(
                    "📩 KHÁCH GỬI CHUYỂN KHOẢN + 4 SỐ ĐUÔI\n\n"
                    f"👤 Telegram: {tg_username}\n"
                    f"🆔 Chat ID: {chat_id}\n"
                    f"🎯 4 số đuôi tknh : {four_last_digits}"
                )
            )
            bot.send_message(chat_id, "✅ Em đã nhận đủ thông tin, em xử lý và cộng điểm cho mình ngay nhé ạ ❤️")
        except Exception as e:
            print("Lỗi gửi admin:", e)
            bot.send_message(chat_id, "⚠️ Em gửi thông tin bị lỗi, mình đợi em 1 chút hoặc nhắn CSKH giúp em nhé ạ.")

        user_state[chat_id] = None
        return

    if user_state.get(chat_id) == "WAITING_USERNAME":
        username_game = text
        tg_username = f"@{message.from_user.username}" if message.from_user.username else "Không có"
        time_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

        admin_text = (
            "🔔 Có khách mới gửi thông tin nhận code\n\n"
            f"👤 Telegram: {tg_username}\n"
            f"🧾 Tên tài khoản: {username_game}\n"
            f"⏰ Thời gian: {time_str}\n"
            f"🆔 Chat ID: {chat_id}"
        )
        try:
            if ADMIN_CHAT_ID != 0:
                bot.send_message(ADMIN_CHAT_ID, admin_text)
                bot.forward_message(ADMIN_CHAT_ID, chat_id, message.message_id)
        except Exception as e:
            print("Lỗi gửi tin cho admin:", e)

        reply_text = (
            f"Em đã nhận được tên tài khoản: *{username_game}* ✅\n\n"
            "Mình vào U888 lên vốn theo mốc để nhận khuyến mãi giúp em nhé.\n"
            "Lên thành công mình gửi *ảnh chuyển khoản* để em cộng điểm trực tiếp vào tài khoản cho mình ạ.\n\n"
            "Có bất cứ thắc mắc gì nhắn tin trực tiếp cho CSKH U888:\n"
            f"👉 [Mỹ Oanh]({CSKH_LINK})\n\n"
        )

        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAIBbWkln42l0QufAXVKVmH_Qa6oeFhZAALxDGsbpw8pVY05zyDcJpCbAQADAgADeQADNgQ",
                caption=reply_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi ảnh reply_text:", e)
            bot.send_message(chat_id, reply_text, parse_mode="Markdown")

        user_state[chat_id] = "WAITING_RECEIPT"
        return


# ================== NHẬN ẢNH/FILE CHUYỂN KHOẢN ==================
@bot.message_handler(content_types=['photo', 'document'])
def handle_receipt_media(message):
    chat_id = message.chat.id
    if user_state.get(chat_id) != "WAITING_RECEIPT":
        return

    if message.content_type == "photo":
        receipt_file_id = message.photo[-1].file_id
    else:
        receipt_file_id = message.document.file_id

    user_state[chat_id] = {"state": "WAITING_GAME", "receipt_file_id": receipt_file_id}

    bot.send_message(
        chat_id,
        "Dạ mình vui lòng cho em xin *4 số đuôi* của tài khoản ngân hàng với ạ!",
        parse_mode="Markdown"
    )


# ================== WEBHOOK FLASK ==================
@server.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        raw = request.get_data(as_text=True)
        print(">>> WEBHOOK RAW:", raw[:500])  # in 500 ký tự đầu
        update = telebot.types.Update.de_json(raw)
        print(">>> UPDATE:", update)          # xem update có gì
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        print(">>> WEBHOOK ERROR:", e)
        return "ERR", 500


@server.route("/", methods=['GET'])
def home():
    return "Bot is running!", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("Running on port", port)
    server.run(host="0.0.0.0", port=port)
