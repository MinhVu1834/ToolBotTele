import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request
from datetime import datetime
import os

# ============ CẤU HÌNH ============

BOT_TOKEN = os.getenv("7983478536:AAHjPiGNCKEFDeEAHNjUV7PtRRE0dHT_WUo")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

REG_LINK = "https://u888x8m.buzz/Register?f=4781047"
WEBAPP_LINK = "https://m.u8882m.com/mobile/Register?f=4781047"
CSKH_LINK = "https://t.me/my_oanh_u888"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
server = Flask(__name__)

user_state = {}

# ================== NÚT 💥 THAM GIA NGAY ==================
def send_play_button(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn = KeyboardButton("💥 Tham gia ngay")
    markup.add(btn)
    bot.send_message(chat_id,
                     "Bấm nút 💥 Tham gia ngay bên dưới để vào link đăng ký:",
                     reply_markup=markup)


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
    ask_account_status(chat_id)
    send_play_button(chat_id)


# ================== CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data

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
        bot.send_message(chat_id, "🛡 Bảo hiểm vốn 2 tay đầu – thua hoàn 100%...")
    elif data == "win5_bcr_200":
        bot.send_message(chat_id, "🏆 Nhận 200K – thắng chuỗi 5 BCR...")
    elif data == "lose5_bcr_200":
        bot.send_message(chat_id, "💸 Nhận 200K – thua chuỗi 5 BCR...")


# ================== HỎI TÊN TÀI KHOẢN ==================
def ask_for_username(chat_id):
    text = (
        "Dạ ok anh/chị ❤️\n\n"
        "Anh/chị vui lòng gửi đúng *tên tài khoản* để em kiểm tra.\n"
        "Ví dụ:\n"
        "`Tên tài khoản: abc123`"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown")

    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⏪ Quay lại bước trước", callback_data="back_to_account_status")
    markup.row(btn_back)
    bot.send_message(chat_id, "Nếu cần, anh/chị có thể quay lại:", reply_markup=markup)

    user_state[chat_id] = "WAITING_USERNAME"


# ================== XỬ LÝ NHẬP TEXT ==================
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

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
            "🔔 Có khách mới gửi thông tin\n\n"
            f"👤 Telegram: {tg_username}\n"
            f"🧾 Tài khoản: {username_game}\n"
            f"⏰ Thời gian: {time_str}\n"
            f"🆔 Chat ID: {chat_id}"
        )
        bot.send_message(ADMIN_CHAT_ID, admin_text)

        reply_text = (
            f"Em đã nhận: *{username_game}* ✅\n\n"
            "Trong lúc chờ kiểm tra, anh/chị chọn ưu đãi 👇"
        )

        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("🛡 BH vốn 2 tay đầu", callback_data="bhv_2tay_100"))
        markup.row(types.InlineKeyboardButton("🏆 Thắng 5 BCR – 200K", callback_data="win5_bcr_200"))
        markup.row(types.InlineKeyboardButton("💸 Thua 5 BCR – 200K", callback_data="lose5_bcr_200"))
        markup.row(types.InlineKeyboardButton("⏪ Sửa tài khoản", callback_data="back_to_username"))

        bot.send_message(chat_id, reply_text, parse_mode="Markdown", reply_markup=markup)

        user_state[chat_id] = None
        send_play_button(chat_id)
        return

    bot.send_message(chat_id, "Dạ để nhận code anh/chị bấm /start giúp em nhé ❤️")


# ================== WEBHOOK FLASK ==================
@server.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@server.route("/", methods=['GET'])
def home():
    return "Bot is running!", 200


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
