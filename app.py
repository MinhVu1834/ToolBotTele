import os
from datetime import datetime
import threading
import time

import requests
import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request

# ============ CẤU HÌNH ============

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

REG_LINK = "https://u888h8.com?f=5059840"
WEBAPP_LINK = "https://u888h8.com?f=5059840"  # hiện chưa dùng, để sẵn
CSKH_LINK = "https://t.me/my_oanh_u888"

LIVE_LINK = "https://live.u88899.com/"
CODE_LIVESTREAM_LINK = "https://u888code.com/"

# Cấu hình giữ bot "thức"
ENABLE_KEEP_ALIVE = os.getenv("ENABLE_KEEP_ALIVE", "false").lower() == "true"
PING_URL = os.getenv("PING_URL")
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "300"))  # 300 giây = 5 phút

# ================== KHỞI TẠO BOT & FLASK ==================

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
server = Flask(__name__)

# Lưu trạng thái user
user_state = {}  # {chat_id: "WAITING_USERNAME"}


# ================== HÀM KEEP ALIVE ==================
def keep_alive():
    """
    Tự ping chính service trên Render để hạn chế bị sleep.
    Chỉ chạy khi ENABLE_KEEP_ALIVE = true và PING_URL có giá trị.
    """
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


# bật thread keep-alive NGAY KHI file được import (phù hợp cả khi chạy gunicorn)
if ENABLE_KEEP_ALIVE:
    threading.Thread(target=keep_alive, daemon=True).start()


# ================== HỎI TRẠNG THÁI TÀI KHOẢN ==================
def ask_account_status(chat_id):
    """
    Gửi 1 ảnh + đoạn hỏi:
    - Anh/chị đã có tài khoản chơi U888 chưa?
    """
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
            "AgACAgUAAxkBAAIBfWklq1MKg2XIBK3tqH32rSgo4IXcAAICDWsbpw8pVRJBh47k56QWAQADAgADeQADNgQ",
            caption=text,
            reply_markup=markup
        )
    except Exception as e:
        print("Lỗi gửi ảnh ask_account_status:", e)
        # fallback: gửi text nếu ảnh lỗi
        bot.send_message(chat_id, text, reply_markup=markup)

    user_state[chat_id] = None


# ================== /start ==================
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    print(">>> /start from:", chat_id)

    # Vào thẳng hỏi trạng thái tài khoản (ảnh + text)
    ask_account_status(chat_id)


# ================== CALLBACK INLINE ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data
    print(">>> callback:", data, "from", chat_id)

    if data == "no_account":
        # Nhánh CHƯA CÓ – ĐĂNG KÝ NGAY

        text = (
            "Tuyệt vời, em gửi anh/chị link đăng ký nè 👇\n\n"
            f"🔗 Link đăng ký: {REG_LINK}\n\n"
            "Anh/chị đăng ký xong bấm nút bên dưới để em hỗ trợ nhận code nhé."
        )

        markup = types.InlineKeyboardMarkup()
        btn_done = types.InlineKeyboardButton("✅ MÌNH ĐĂNG KÝ XONG RỒI", callback_data="registered_done")
        markup.row(btn_done)

        # Xoá inline cũ (nếu muốn) rồi gửi tin mới
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
        # Nhánh ĐÃ CÓ TÀI KHOẢN hoặc MÌNH ĐĂNG KÝ XONG RỒI
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
        game_type = text

        try:
            tg_username = f"@{message.from_user.username}" if message.from_user.username else "Không có"

            # Gửi ảnh chuyển khoản cho admin
            bot.send_photo(
                ADMIN_CHAT_ID,
                state["receipt_file_id"],
                caption=(
                    "📩 KHÁCH GỬI CHUYỂN KHOẢN + CHỌN TRÒ CHƠI\n\n"
                    f"👤 Telegram: {tg_username}\n"
                    f"🆔 Chat ID: {chat_id}\n"
                    f"🎯 Trò chơi: {game_type}"
                )
            )

            bot.send_message(chat_id, "✅ Em đã nhận đủ thông tin, em xử lý và cộng điểm cho mình ngay nhé ạ ❤️")
        except Exception as e:
            print("Lỗi gửi admin:", e)
            bot.send_message(chat_id, "⚠️ Em gửi thông tin bị lỗi, mình đợi em 1 chút hoặc nhắn CSKH giúp em nhé ạ.")

        except Exception as e:
            print("Lỗi gửi admin:", e)

        user_state[chat_id] = None
        return
    

    # --- Nếu đang chờ user gửi tên tài khoản ---
    if user_state.get(chat_id) == "WAITING_USERNAME":
        username_game = text
        tg_username = f"@{message.from_user.username}" if message.from_user.username else "Không có"
        time_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

        # Gửi cho admin
        admin_text = (
            "🔔 Có khách mới gửi thông tin nhận code\n\n"
            f"👤 Telegram: {tg_username}\n"
            f"🧾 Tên tài khoản: {username_game}\n"
            f"⏰ Thời gian: {time_str}\n"
            f"🆔 Chat ID: {chat_id}"
        )
        try:
            bot.send_message(ADMIN_CHAT_ID, admin_text)
            # 👉 Forward tin nhắn gốc của khách
            bot.forward_message(ADMIN_CHAT_ID, chat_id, message.message_id)
        except Exception as e:
            print("Lỗi gửi tin cho admin:", e)

        # Ảnh + text xác nhận tài khoản
        reply_text = (
            f"Em đã nhận được tên tài khoản: <b>{username_game}</b> ✅<br><br>"
            "Mình vào U888 lên vốn theo mốc để nhận khuyến mãi giúp em nhé.<br>"
            "Lên thành công mình gửi <b>ảnh chuyển khoản</b> để em cộng điểm trực tiếp vào tài khoản cho mình ạ.<br><br>"
            'Có bất cứ thắc mắc gì nhắn tin trực tiếp cho CSKH U888 → '
            '<a href="https://t.me/my_oanh_u888">t.me/my_oanh_u888</a>'
        )

         # ✅ Gửi ảnh kèm caption (fallback sang text nếu lỗi)
        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAIBbWkln42l0QufAXVKVmH_Qa6oeFhZAALxDGsbpw8pVY05zyDcJpCbAQADAgADeQADNgQ",  # 👈 THAY bằng file_id ảnh thật (AgACAgU....)
                caption=reply_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi ảnh reply_text:", e)
            bot.send_message(chat_id, reply_text, parse_mode="Markdown")

        # 👉 chờ ảnh chuyển khoản
        user_state[chat_id] = "WAITING_RECEIPT"
        return

  


# ================== LẤY FILE_ID ẢNH (TẠM DÙNG ĐỂ LẤY ID) ==================
@bot.message_handler(content_types=['photo', 'document'])
def handle_receipt_media(message):
    chat_id = message.chat.id

    if user_state.get(chat_id) != "WAITING_RECEIPT":
        return

    # Lấy file_id đúng theo loại media
    if message.content_type == "photo":
        receipt_file_id = message.photo[-1].file_id
    else:  # document
        receipt_file_id = message.document.file_id

    # Lưu lại để lát khách chọn game xong gửi cho admin
    user_state[chat_id] = {
        "state": "WAITING_GAME",
        "receipt_file_id": receipt_file_id
    }

    bot.send_message(
        chat_id,
        "Mình muốn chơi *BCR - Thể Thao*, *Nổ hũ - Bắn Cá* hay *Game bài* ạ?",
        parse_mode="Markdown"
    )


# ================== WEBHOOK FLASK ==================

@server.route("/webhook", methods=['POST'])
def telegram_webhook():
    print(">>> Got update from Telegram")
    json_str = request.get_data().decode("utf-8")
    # HÀM ĐÚNG: Update.de_json (có dấu chấm, không phải Update_de_json)
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@server.route("/", methods=['GET'])
def home():
    return "Bot is running!", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("Running on port", port)
    server.run(host="0.0.0.0", port=port)
