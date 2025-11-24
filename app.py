import os
from datetime import datetime

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

# ================== KHỞI TẠO BOT & FLASK ==================

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
server = Flask(__name__)

# Lưu trạng thái user
user_state = {}  # {chat_id: "WAITING_USERNAME"}


# ================== HỎI TRẠNG THÁI TÀI KHOẢN ==================
def ask_account_status(chat_id):
    """
    Gửi 1 ảnh + đoạn hỏi:
    - Anh/chị đã có tài khoản chơi U888 chưa?
    """

    # Ảnh banner đầu tiên
    bot.send_photo(
        chat_id,
        "https://km-abcvip.com/wp-content/uploads/2025/08/U88-nhan-thuong-ngay-vang.png"
    )

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

        # Ảnh minh hoạ cho bước đăng ký mới
        bot.send_photo(
            chat_id,
            "https://km-abcvip.com/wp-content/uploads/2025/09/Dieu-kien-va-luu-y-quan-trong-khi-nhan-thuong-nap-dau-U888.png"
        )

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

        bot.send_message(chat_id, text, reply_markup=markup)

    elif data in ("have_account", "registered_done"):
        # Nhánh ĐÃ CÓ TÀI KHOẢN hoặc MÌNH ĐĂNG KÝ XONG RỒI
        ask_for_username(chat_id)


# ================== HỎI TÊN TÀI KHOẢN ==================
def ask_for_username(chat_id):
    # Ảnh minh hoạ cho bước nhập tên tài khoản
    bot.send_photo(
        chat_id,
        "https://km-abcvip.com/wp-content/uploads/2025/09/Cach-tham-gia-va-nhan-thuong-chi-tiet-chuong-trinh-Thu-7-Vang-–-U888.png"
    )

    text = (
        "Dạ ok anh/chị ❤️\n\n"
        "Anh/chị vui lòng gửi đúng *tên tài khoản* để em kiểm tra và duyệt code.\n\n"
        "Ví dụ:\n"
        "`Tên tài khoản: abc123`"
    )

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
        except Exception as e:
            print("Lỗi gửi tin cho admin:", e)

        # Ảnh minh hoạ trước khi báo đã nhận tài khoản
        bot.send_photo(
            chat_id,
            "https://km-abcvip.com/wp-content/uploads/2025/09/Diem-noi-bat-khi-tham-gia-su-kien-thu-6-cua-U888.png"
        )

        # Trả lời khách + mở menu 4 nút
        reply_text = (
            f"Em đã nhận được tên tài khoản: *{username_game}* ✅\n\n"
            "Hiện tại em đang gửi cho bộ phận kiểm tra để duyệt code cho anh/chị.\n"
            "Trong lúc chờ, anh/chị có thể xem thêm các ưu đãi đặc biệt bên em ở menu dưới nhé 👇"
        )
        bot.send_message(chat_id, reply_text, parse_mode="Markdown")

        user_state[chat_id] = None
        send_main_menu(chat_id)
        return

    # --- Xử lý các nút trong menu 4 nút ---
    if text == "Đăng Ký Nhận 88K 🧧":
        # Gửi link đăng ký 88K
        msg = (
            "Để nhận 88K trải nghiệm, anh/chị đăng ký tài khoản tại link bên dưới giúp em nhé 👇\n\n"
            f"🔗 {REG_LINK}"
        )
        bot.send_message(chat_id, msg)
        return

    if text == "Chia Sẻ Bạn Bè 👥":
        # Gửi form giới thiệu bạn bè
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
        bot.send_message(chat_id, share_text)
        return

    if text == "🎁 NHẬP CODE Ở LIVESTREAM":
        # Gửi link nhập code
        msg = (
            "Anh/chị có thể nhập CODE nhận thưởng trực tiếp tại đây giúp em nhé 👇\n\n"
            f"🔗 {CODE_LIVESTREAM_LINK}"
        )
        bot.send_message(chat_id, msg)
        return

    if text == "📺 Săn Code lúc 20h hàng ngày":
        # Gửi link xem livestream săn code
        msg = (
            "⏰ 20H hằng ngày anh/chị vào đây xem livestream để săn CODE 38K – 888K siêu khủng nhé 👇\n\n"
            f"🔗 {LIVE_LINK}"
        )
        bot.send_message(chat_id, msg)
        return

    # --- Mặc định: nếu chat linh tinh ngoài flow ---
    bot.send_message(chat_id, "Dạ để nhận code anh/chị bấm /start giúp em nhé ❤️")


# ================== WEBHOOK FLASK ==================

@server.route("/webhook", methods=['POST'])
def telegram_webhook():
    print(">>> Got update from Telegram")
    json_str = request.get_data().decode("utf-8")
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
