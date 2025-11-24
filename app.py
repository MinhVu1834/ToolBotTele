import os
from datetime import datetime

import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request

# ============ CẤU HÌNH ============

BOT_TOKEN = os.getenv("7983478536:AAHjPiGNCKEFDeEAHNjUV7PtRRE0dHT_WUo")
ADMIN_CHAT_ID = int(os.getenv("7943735641", "0"))

REG_LINK = "https://u888x8m.buzz/Register?f=4781047"
WEBAPP_LINK = "https://m.u8882m.com/mobile/Register?f=4781047"
CSKH_LINK = "https://t.me/my_oanh_u888"

# ================== KHỞI TẠO BOT & FLASK ==================

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
server = Flask(__name__)

# Lưu trạng thái user
user_state = {}  # {chat_id: "WAITING_USERNAME"}


# ================== NÚT 💥 THAM GIA NGAY ==================
def send_play_button(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn = KeyboardButton("💥 Tham gia ngay")
    markup.add(btn)
    bot.send_message(
        chat_id,
        "Bấm nút 💥 Tham gia ngay bên dưới để vào link đăng ký:",
        reply_markup=markup
    )


# ================== HỎI TRẠNG THÁI TÀI KHOẢN ==================
def ask_account_status(chat_id):
    text = (
        "Chào anh/chị 👋\n"
        "Em là Bot hỗ trợ nhận CODE ưu đãi.\n\n"
        "Để nhận code, anh/chị cho em hỏi:\n"
        "👉 Anh/chị đã có tài khoản chơi chưa ạ?"
    )

    markup = types.InlineKeyboardMarkup()
    btn_have = types.InlineKeyboardButton("✅ ĐÃ CÓ TÀI KHOẢN", callback_data="have_account")
    btn_no = types.InlineKeyboardButton("🆕 CHƯA CÓ – ĐĂNG KÝ NGAY", callback_data="no_account")
    markup.row(btn_have)
    markup.row(btn_no)

    bot.send_message(chat_id, text, reply_markup=markup)
    user_state[chat_id] = None


# ================== /start ==================
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    print(">>> /start from:", chat_id)
    ask_account_status(chat_id)
    send_play_button(chat_id)


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

        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        bot.send_message(chat_id, text, reply_markup=markup)

    elif data in ("have_account", "registered_done", "back_to_username"):
        ask_for_username(chat_id)

    elif data == "back_to_account_status":
        ask_account_status(chat_id)

    elif data == "bhv_2tay_100":
        text = (
            "🛡 BẢO HIỂM VỐN 2 TAY ĐẦU – THUA HOÀN 100%\n\n"
            "- Áp dụng cho 2 tay đầu theo đúng thể lệ.\n"
            "- Nếu thua sẽ được hoàn 100% vốn theo quy định.\n\n"
            "Chi tiết thể lệ anh/chị có thể hỏi trực tiếp CSKH để được tư vấn rõ hơn nhé."
        )
        bot.send_message(chat_id, text)

    elif data == "win5_bcr_200":
        text = (
            "🏆 NHẬN 200K – THẮNG CHUỖI 5 BCR\n\n"
            "- Nếu anh/chị thắng liên tiếp 5 tay BCR theo thể lệ chương trình,\n"
            "- Sẽ được tặng thưởng 200K.\n\n"
            "Vui lòng giữ lịch sử cược để bên em kiểm tra khi nhận thưởng."
        )
        bot.send_message(chat_id, text)

    elif data == "lose5_bcr_200":
        text = (
            "💸 NHẬN 200K – THUA CHUỖI 5 BCR\n\n"
            "- Nếu anh/chị thua liên tiếp 5 tay BCR theo thể lệ chương trình,\n"
            "- Sẽ được hỗ trợ 200K theo quy định.\n\n"
            "Vui lòng giữ lịch sử cược để bên em kiểm tra nhé."
        )
        bot.send_message(chat_id, text)


# ================== HỎI TÊN TÀI KHOẢN ==================
def ask_for_username(chat_id):
    text = (
        "Dạ ok anh/chị ❤️\n\n"
        "Anh/chị vui lòng gửi đúng *tên tài khoản* để em kiểm tra và duyệt code.\n\n"
        "Ví dụ:\n"
        "`Tên tài khoản: abc123`"
    )

    bot.send_message(chat_id, text, parse_mode="Markdown")

    markup_back = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⏪ Quay lại bước trước", callback_data="back_to_account_status")
    markup_back.row(btn_back)
    bot.send_message(chat_id, "Nếu cần, anh/chị có thể quay lại bước trước:", reply_markup=markup_back)

    user_state[chat_id] = "WAITING_USERNAME"


# ================== XỬ LÝ TIN NHẮN TEXT ==================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()
    print(">>> text:", text, "from", chat_id)

    if text == "💥 Tham gia ngay":
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("👉 Nhấn để đăng ký ngay", url=REG_LINK)
        markup.add(btn)
        bot.send_message(chat_id, "Link tham gia của anh/chị đây ạ 👇", reply_markup=markup)
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
            bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception as e:
            print("Lỗi gửi tin cho admin:", e)

        reply_text = (
            f"Em đã nhận được tên tài khoản: *{username_game}* ✅\n\n"
            "Hiện tại em đang gửi cho bộ phận kiểm tra để duyệt code cho anh/chị.\n"
            "Trong lúc chờ, anh/chị chọn 1 trong các ưu đãi bên dưới giúp em 👇"
        )

        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(
            "🛡 BH vốn 2 tay đầu – Thua hoàn 100%", callback_data="bhv_2tay_100"
        )
        btn2 = types.InlineKeyboardButton(
            "🏆 Nhận 200K – Thắng chuỗi 5 BCR", callback_data="win5_bcr_200"
        )
        btn3 = types.InlineKeyboardButton(
            "💸 Nhận 200K – Thua chuỗi 5 BCR", callback_data="lose5_bcr_200"
        )
        btn4 = types.InlineKeyboardButton(
            "⏪ Quay lại sửa tài khoản", callback_data="back_to_username"
        )
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)

        bot.send_message(chat_id, reply_text, parse_mode="Markdown", reply_markup=markup)

        user_state[chat_id] = None
        send_play_button(chat_id)
    else:
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
