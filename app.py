import os
from datetime import datetime
import threading
import time
import requests

import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request

# ======================================================
# CẤU HÌNH
# ======================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

REG_LINK = "https://u888x8m.buzz/Register?f=4781047"
WEBAPP_LINK = "https://m.u8882m.com/mobile/Register?f=4781047"
CSKH_LINK = "https://t.me/my_oanh_u888"
LIVE_LINK = "https://live.u88899.com/"
CODE_LIVESTREAM_LINK = "https://u888code.com/"

# Các biến để giữ bot "thức"
ENABLE_KEEP_ALIVE = os.getenv("ENABLE_KEEP_ALIVE", "false").lower() == "true"
PING_URL = os.getenv("PING_URL")  # URL public của service render
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "300"))  # default 5 phút

# ======================================================
# KHỞI TẠO BOT & SERVER
# ======================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
server = Flask(__name__)

user_state = {}  # {chat_id: "WAITING_USERNAME"}


# ======================================================
# HÀM KEEP ALIVE – TỰ PING SERVER
# ======================================================
def keep_alive():
    """
    Tự động ping chính server Render để giữ bot không ngủ
    """
    if not PING_URL:
        print("[KEEP ALIVE] Không có PING_URL, bỏ qua.")
        return

    print(f"[KEEP ALIVE] Bắt đầu ping {PING_URL} mỗi {PING_INTERVAL}s")

    while True:
        try:
            r = requests.get(PING_URL, timeout=10)
            print(f"[KEEP ALIVE] Ping {PING_URL} → {r.status_code}")
        except Exception as e:
            print("[KEEP ALIVE] Lỗi ping:", e)
        time.sleep(PING_INTERVAL)


# ======================================================
# HỎI TRẠNG THÁI TÀI KHOẢN
# ======================================================
def ask_account_status(chat_id):
    text = (
        "👋 Chào anh/chị!\n"
        "Em là Bot hỗ trợ nhận CODE ưu đãi U888.\n\n"
        "👉 Anh/chị đã có tài khoản chơi U888 chưa ạ?\n"
        "(Bấm ĐÃ CÓ hoặc CHƯA CÓ bên dưới giúp em nhé ❤️)"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ ĐÃ CÓ TÀI KHOẢN", callback_data="have_account"),
    )
    markup.add(
        types.InlineKeyboardButton("🆕 CHƯA CÓ – ĐĂNG KÝ NGAY", callback_data="no_account")
    )

    try:
        bot.send_photo(
            chat_id,
            "AgACAgUAAxkBAAIBfWklq1MKg2XIBK3tqH32rSgo4IXcAAICDWsbpw8pVRJBh47k56QWAQADAgADeQADNgQ",
            caption=text,
            reply_markup=markup
        )
    except:
        bot.send_message(chat_id, text, reply_markup=markup)

    user_state[chat_id] = None


# ======================================================
# MENU 4 NÚT
# ======================================================
def send_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Đăng Ký Nhận 88K 🧧", "Chia Sẻ Bạn Bè 👥")
    markup.row("🎁 NHẬP CODE Ở LIVESTREAM", "📺 Săn Code lúc 20h hàng ngày")

    bot.send_message(chat_id, "Anh/chị chọn 1 mục dưới đây nhé 👇", reply_markup=markup)


# ======================================================
# /START
# ======================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    ask_account_status(message.chat.id)


# ======================================================
# CALLBACK
# ======================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "no_account":
        text = (
            "Tuyệt vời! Đây là link đăng ký của anh/chị 👇\n\n"
            f"🔗 {REG_LINK}\n\n"
            "Đăng ký xong bấm *Mình đã đăng ký xong* giúp em nhé ❤️"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ MÌNH ĐĂNG KÝ XONG RỒI", callback_data="registered_done"))

        bot.send_message(chat_id, text, reply_markup=markup)

    elif data in ("have_account", "registered_done"):
        ask_for_username(chat_id)


# ======================================================
# HỎI TÊN USER GAME
# ======================================================
def ask_for_username(chat_id):
    text = (
        "Dạ ok anh/chị ❤️\n\n"
        "Vui lòng gửi đúng *tên tài khoản chơi U888* giúp em.\n\n"
        "Ví dụ: `abc123`"
    )

    bot.send_message(chat_id, text, parse_mode="Markdown")
    user_state[chat_id] = "WAITING_USERNAME"


# ======================================================
# XỬ LÝ TEXT
# ======================================================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # đang chờ tên tài khoản
    if user_state.get(chat_id) == "WAITING_USERNAME":
        username_game = text
        tg_username = f"@{message.from_user.username}" if message.from_user.username else "Không có"
        time_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

        admin_text = (
            "🔔 KHÁCH MỚI NHẬN CODE\n\n"
            f"👤 Telegram: {tg_username}\n"
            f"🧾 Tài khoản game: {username_game}\n"
            f"⏰ Thời gian: {time_str}\n"
            f"🆔 Chat ID: {chat_id}"
        )
        bot.send_message(ADMIN_CHAT_ID, admin_text)

        bot.send_message(
            chat_id,
            f"Em đã nhận được tài khoản: *{username_game}* ❤️\n"
            "Em chuyển qua bộ phận kiểm tra nhé!\n"
            "Trong lúc chờ anh/chị bấm menu bên dưới ạ 👇",
            parse_mode="Markdown"
        )

        user_state[chat_id] = None
        send_main_menu(chat_id)
        return

    # ===================== MENU ========================
    if text == "Đăng Ký Nhận 88K 🧧":
        msg = (
            "📱 *Hướng dẫn nhận 88K trải nghiệm:*\n\n"
            "1️⃣ Tải App U888\n"
            "2️⃣ Nhập tên tài khoản\n"
            "3️⃣ Gửi SMS xác minh\n\n"
            "👉 Link nhận 88K: https://88u888.club/"
        )
        bot.send_message(chat_id, msg, parse_mode="Markdown")
        return

    if text == "Chia Sẻ Bạn Bè 👥":
        msg = (
            "🔗 Mỗi lượt giới thiệu thành công nhận thưởng ngay!\n"
            "Link chia sẻ: https://t.me/my_oanh_u888"
        )
        bot.send_message(chat_id, msg)
        return

    if text == "🎁 NHẬP CODE Ở LIVESTREAM":
        bot.send_message(chat_id, f"Link nhập code livestream đây ạ 👇\n{CODE_LIVESTREAM_LINK}")
        return

    if text == "📺 Săn Code lúc 20h hàng ngày":
        bot.send_message(chat_id, f"Xem livestream săn code lúc 20h hàng ngày 👇\n{LIVE_LINK}")
        return

    bot.send_message(chat_id, "Dạ để nhận code anh/chị bấm /start giúp em nhé ❤️")


# ======================================================
# WEBHOOK SERVER
# ======================================================
@server.route("/webhook", methods=['POST'])
def telegram_webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@server.route("/", methods=['GET'])
def home():
    return "Bot is running!", 200


# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))

    # bật self-ping nếu ENABLE_KEEP_ALIVE = true
    if ENABLE_KEEP_ALIVE:
        threading.Thread(target=keep_alive, daemon=True).start()

    print("Running on port", port)
    server.run(host="0.0.0.0", port=port)
