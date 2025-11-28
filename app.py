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

REG_LINK = "https://u888x8m.buzz/Register?f=4781047"
WEBAPP_LINK = "https://m.u8882m.com/mobile/Register?f=4781047"  # hiện chưa dùng, để sẵn
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


# ================== MENU 4 NÚT XUẤT HIỆN XUYÊN SUỐT ==================
def send_main_menu(chat_id):
    """
    Menu 4 nút, 2 hàng x 2 cột:
    Hàng 1: Đăng Ký Nhận 88K 🧧 | Chia Sẻ Bạn Bè 👥
    Hàng 2: 🎁 NHẬP CODE Ở LIVESTREAM | 📺 Săn Code lúc 20h hàng ngày
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    btn_reg_88k = KeyboardButton("Đăng Ký Nhận 88K 🧧")
    btn_share = KeyboardButton("Chia Sẻ Bạn Bè 👥")
    btn_code_ls = KeyboardButton("🎁 NHẬP CODE Ở LIVESTREAM")
    btn_san_code = KeyboardButton("📺 Săn Code lúc 20h hàng ngày")

    markup.row(btn_reg_88k, btn_share)
    markup.row(btn_code_ls, btn_san_code)

    bot.send_message(
        chat_id,
        "Anh/chị chọn 1 trong các mục dưới đây giúp em nhé 👇",
        reply_markup=markup
    )


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
            f"Em đã nhận được tên tài khoản: *{username_game}* ✅\n\n"
            "Hiện tại em đang gửi cho bộ phận kiểm tra để duyệt code cho anh/chị.\n"
            "Trong lúc chờ, anh/chị có thể xem thêm các ưu đãi đặc biệt bên em ở menu dưới nhé 👇"
        )

        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAIBbWkln42l0QufAXVKVmH_Qa6oeFhZAALxDGsbpw8pVY05zyDcJpCbAQADAgADeQADNgQ",
                caption=reply_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi ảnh xác nhận username:", e)
            bot.send_message(chat_id, reply_text, parse_mode="Markdown")

        user_state[chat_id] = None
        send_main_menu(chat_id)
        return

    # ================== MENU 4 NÚT ==================

    # 1. Đăng ký nhận 88K
    if text == "Đăng Ký Nhận 88K 🧧":
        msg = (
            "📱 *Hướng Dẫn Nhận 88K Trải Nghiệm – Bản Sinh Động*\n\n"
            "1️⃣ *Tải App U888*\n"
            "⬇️ Tải app về điện thoại để bắt đầu nhận ưu đãi.\n\n"
            "2️⃣ *Nhập Tên Tài Khoản Hội Viên*\n"
            "📝 Mở app → điền tên tài khoản → nhấn *Kiểm tra*.\n\n"
            "3️⃣ *Gửi SMS Xác Minh*\n"
            "📤 Nhấn *Gửi SMS xác minh* → hệ thống tự chuyển sang SMS.\n"
            "📨 Gửi tin nhắn theo hướng dẫn → *copy nội dung SMS* và điền vào form nhận 88K.\n\n"
            "4️⃣ *Xác Nhận & Chờ Cộng Tiền*\n"
            "✅ Nhấn “Đã gửi tin nhắn”\n"
            "⏳ Chờ hệ thống khoảng 3–5 phút để cộng điểm vào tài khoản.\n\n"
            "👉 Link đăng ký nhận 88K của anh/chị đây ạ:\n"
            "🔗 https://88u888.club/"
        )

        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAIBb2kln7uPKrwbAvMH3fUNRQxlIHT6AALyDGsbpw8pVYILLMuU6vZ1AQADAgADeQADNgQ",
                caption=msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi ảnh hướng dẫn 88K:", e)
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        return

    # 2. Chia sẻ bạn bè
    if text == "Chia Sẻ Bạn Bè 👥":
        share_text = (
            "🔗 Mỗi lượt giới thiệu thành công, bạn nhận 1500 đ\n"
            "- 20K khi bạn bè đăng ký & xác nhận tài khoản.\n"
            "- 50K khi bạn bè nạp tiền lần đầu!\n\n"
            "👉 Cách tham gia:\n"
            "1️⃣ Sao chép link này: https://t.me/my_oanh_u888\n"
            "2️⃣ Gửi bạn bè của bạn.  ( Đủ 30k để quy đổi )\n\n"
            "📌 Nhận thưởng ngay khi bạn bè tham gia!\n\n"
            "⚡️ Giới thiệu càng nhiều, nhận càng lớn!"
        )

        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAIBn2klsGZWE4iS3UO7E9Kj7OzMHd3NAAIODWsbpw8pVRI3ucG9-ZOaAQADAgADeQADNgQ",
                caption=share_text
            )
        except Exception as e:
            print("Lỗi gửi ảnh chia sẻ bạn bè:", e)
            bot.send_message(chat_id, share_text)
        return

    # 3. Nhập code ở livestream
    if text == "🎁 NHẬP CODE Ở LIVESTREAM":
        msg = (
            "Anh/chị có thể nhập CODE nhận thưởng trực tiếp tại đây giúp em nhé 👇\n\n"
            f"🔗 {CODE_LIVESTREAM_LINK}"
        )

        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAIBjGklq-uqdpW4yy25J-HRxqGIHAnKAAIDDWsbpw8pVaRLsaHOvgTEAQADAgADeQADNgQ",
                caption=msg
            )
        except Exception as e:
            print("Lỗi gửi ảnh nhập code livestream:", e)
            bot.send_message(chat_id, msg)
        return

    # 4. Săn code 20h
    if text == "📺 Săn Code lúc 20h hàng ngày":
        msg = (
            "⏰ 20H hằng ngày anh/chị vào đây xem livestream để săn CODE 38K – 888K siêu khủng nhé 👇\n\n"
            f"🔗 {LIVE_LINK}"
        )

        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAIBnWklsA7Sn1RR4VhqIvQjylGEs_1-AAINDWsbpw8pVX-SihjRXRoFAQADAgADeQADNgQ",
                caption=msg
            )
        except Exception as e:
            print("Lỗi gửi ảnh săn code 20h:", e)
            bot.send_message(chat_id, msg)
        return

    # --- Mặc định: nếu chat linh tinh ngoài flow ---
    bot.send_message(chat_id, "Dạ để nhận code anh/chị bấm /start giúp em nhé ❤️")


# ================== LẤY FILE_ID ẢNH (TẠM DÙNG ĐỂ LẤY ID) ==================
@bot.message_handler(content_types=['photo', 'document'])
def handle_photo_get_file_id(message):
    # Kiểu dữ liệu thực tế Telegram gửi
    print(">>> CONTENT TYPE:", message.content_type)

    if message.content_type == 'photo':
        # Ảnh gửi kiểu “Photo”
        file_id = message.photo[-1].file_id
    elif message.content_type == 'document':
        # Ảnh gửi kiểu “File/Tài liệu”
        file_id = message.document.file_id
    else:
        return  # Không phải ảnh thì bỏ qua

    print(">>> FILE_ID ẢNH:", file_id)

    bot.reply_to(
        message,
        f"file_id của ảnh/file này là:\n{file_id}"
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
