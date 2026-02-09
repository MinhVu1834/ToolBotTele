# app.py (updated: Supabase/Postgres logging for telegram_users + leads)

import os
from datetime import datetime
import threading
import time

import requests
import telebot
from telebot import types
from flask import Flask, request

import psycopg2
from psycopg2.extras import RealDictCursor

# ============ CẤU HÌNH ============

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN")

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

REG_LINK = "https://u888h8.com/?f=5051634"
WEBAPP_LINK = "https://u888h8.com/?f=5051634"  # hiện chưa dùng, để sẵn

# Webhook URL (Render env) - BẮT BUỘC khi chạy webhook trên Render
# Ví dụ: https://toolbottele-n0cs.onrender.com/webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Cấu hình giữ bot "thức" (nếu đã dùng UptimeRobot thì nên tắt ENABLE_KEEP_ALIVE)
ENABLE_KEEP_ALIVE = os.getenv("ENABLE_KEEP_ALIVE", "false").lower() == "true"
PING_URL = os.getenv("PING_URL")  # ví dụ: https://toolbottele-n0cs.onrender.com/
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "300"))  # 300 giây = 5 phút

# ================== DATABASE (Supabase Postgres) ==================

DATABASE_URL = os.getenv("DATABASE_URL")  # set trên Render env
_db_conn = None


def get_db():
    """
    Lazy connect + auto-reconnect if dropped.
    """
    global _db_conn
    if not DATABASE_URL:
        raise RuntimeError("Missing DATABASE_URL")
    try:
        if _db_conn is None or _db_conn.closed != 0:
            _db_conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            _db_conn.autocommit = True
        return _db_conn
    except Exception:
        _db_conn = None
        raise


def init_db():
    """
    Create minimal tables if not exist.
    """
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
        create table if not exists telegram_users (
          id bigserial primary key,
          tg_chat_id bigint unique not null,
          tg_username text,
          first_name text,
          last_name text,
          phone text,
          created_at timestamptz default now(),
          updated_at timestamptz default now()
        );
        """)
        cur.execute("""
        create table if not exists leads (
          id bigserial primary key,
          tg_chat_id bigint,
          username_game text,
          game_type text,
          receipt_file_id text,
          status text default 'new',
          note text,
          created_at timestamptz default now()
        );
        """)
        cur.execute("create index if not exists idx_leads_chat on leads(tg_chat_id);")


def upsert_telegram_user(message):
    """
    Upsert basic Telegram profile.
    """
    conn = get_db()
    chat_id = message.chat.id
    tg_username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    with conn.cursor() as cur:
        cur.execute("""
        insert into telegram_users (tg_chat_id, tg_username, first_name, last_name, updated_at)
        values (%s, %s, %s, %s, now())
        on conflict (tg_chat_id)
        do update set
          tg_username = excluded.tg_username,
          first_name = excluded.first_name,
          last_name = excluded.last_name,
          updated_at = now()
        """, (chat_id, tg_username, first_name, last_name))


def create_lead(chat_id, status="new", username_game=None, game_type=None, receipt_file_id=None, note=None):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
        insert into leads (tg_chat_id, status, username_game, game_type, receipt_file_id, note)
        values (%s, %s, %s, %s, %s, %s)
        returning id
        """, (chat_id, status, username_game, game_type, receipt_file_id, note))
        row = cur.fetchone()
        return row["id"] if row else None


def update_latest_lead(chat_id, **fields):
    """
    Update the most recent lead of this chat_id.
    """
    if not fields:
        return
    conn = get_db()
    sets = []
    vals = []
    for k, v in fields.items():
        sets.append(f"{k} = %s")
        vals.append(v)
    vals.append(chat_id)

    with conn.cursor() as cur:
        cur.execute(f"""
        update leads
        set {", ".join(sets)}
        where id = (
          select id from leads
          where tg_chat_id = %s
          order by created_at desc
          limit 1
        )
        """, vals)


# ================== KHỞI TẠO BOT & FLASK ==================

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)  # giữ nguyên như kịch bản cũ
server = Flask(__name__)

# Lưu trạng thái user
user_state = {}  # {chat_id: "WAITING_USERNAME" or "WAITING_RECEIPT" or {"state": "WAITING_GAME", ...}}

# Chế độ debug lấy file_id tạm thời
debug_get_id_mode = set()  # chứa chat_id đang bật chế độ lấy file_id


# ================== HÀM KEEP ALIVE ==================
def keep_alive():
    """
    Tự ping chính service trên Render để hạn chế bị sleep.
    Chỉ chạy khi ENABLE_KEEP_ALIVE = true và PING_URL có giá trị.
    (Khuyến nghị: nếu đã dùng UptimeRobot thì tắt ENABLE_KEEP_ALIVE)
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


if ENABLE_KEEP_ALIVE:
    threading.Thread(target=keep_alive, daemon=True).start()


# ================== SETUP WEBHOOK (quan trọng cho Render) ==================
def setup_webhook():
    """
    Đảm bảo webhook luôn được set lại sau mỗi lần Render restart/deploy.
    """
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


# Gọi luôn khi app start (đúng cho gunicorn/Render)
setup_webhook()

# Init DB at startup (log only, do not crash bot if DB temporarily unreachable)
try:
    init_db()
    print("[DB] init ok")
except Exception as e:
    print("[DB] init error:", e)


# ================== DEBUG GET FILE_ID ==================
@bot.message_handler(commands=['getid'])
def enable_getid(message):
    chat_id = message.chat.id
    debug_get_id_mode.add(chat_id)
    bot.send_message(
        chat_id,
        "✅ Đã bật chế độ lấy FILE_ID.\n"
        "Bây giờ bạn gửi *ảnh / video / file* vào đây, bot sẽ trả lại FILE_ID.\n\n"
        "Tắt bằng lệnh: /stopgetid",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['stopgetid'])
def disable_getid(message):
    chat_id = message.chat.id
    debug_get_id_mode.discard(chat_id)
    bot.send_message(chat_id, "🛑 Đã tắt chế độ lấy FILE_ID.")


# ================== HỎI TRẠNG THÁI TÀI KHOẢN ==================
def ask_account_status(chat_id):
    text = (
        "👋 Chào anh/chị!\n"
        "Em là Bot hỗ trợ nhận CODE ưu đãi U888.\n\n"
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
            "AgACAgUAAxkBAAMZaU1pAuTN06GIa8io6JALwM33V3IAAqMNaxvcyWhWkP8QbtjGmXUBAAMCAAN5AAM2BA",
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

    # DB log
    try:
        upsert_telegram_user(message)
        create_lead(chat_id, status="started", note="start")
    except Exception as e:
        print("[DB] /start error:", e)

    ask_account_status(chat_id)


# ================== CALLBACK INLINE ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data
    print(">>> callback:", data, "from", chat_id)

    if data == "no_account":
        # DB log (optional)
        try:
            update_latest_lead(chat_id, status="no_account_clicked", note="clicked no_account")
        except Exception as e:
            print("[DB] no_account click error:", e)

        text = (
            "Tuyệt vời, em gửi anh/chị link đăng ký nè 👇\n\n"
            f"🔗 Link đăng ký: {REG_LINK}\n\n"
            "Anh/chị đăng ký xong bấm nút bên dưới để em hỗ trợ tiếp nhé."
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
                "AgACAgUAAxkBAAMbaU1pwn4xF66fqQMYuUFcG62Rr6IAAqQNaxvcyWhWMu0TBXYgatUBAAMCAAN5AAM2BA",
                caption=text,
                reply_markup=markup
            )
        except Exception as e:
            print("Lỗi gửi ảnh no_account:", e)
            bot.send_message(chat_id, text, reply_markup=markup)

    elif data in ("have_account", "registered_done"):
        # DB log
        try:
            update_latest_lead(chat_id, status="ready_for_username", note=data)
        except Exception as e:
            print("[DB] have_account/registered_done error:", e)

        ask_for_username(chat_id)


# ================== HỎI TÊN TÀI KHOẢN ==================
def ask_for_username(chat_id):
    text = (
        "Dạ ok anh/chị ❤️\n\n"
        "Anh/chị vui lòng gửi đúng *tên tài khoản* để em kiểm tra.\n\n"
        "Ví dụ:\n"
        "`abc123`"
    )

    try:
        bot.send_photo(
            chat_id,
            "AgACAgUAAxkBAAMfaU1p72JgG8kbtE8XhdakAAEi_Nw0AAKnDWsb3MloVm-htifVgTWdAQADAgADeQADNgQ",
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

    # --- Nếu đang chờ khách chọn game (sau khi đã gửi ảnh chuyển khoản) ---
    if isinstance(state, dict) and state.get("state") == "WAITING_GAME":
        game_type = text

        # DB log
        try:
            update_latest_lead(chat_id, status="done", game_type=game_type, note="game selected")
        except Exception as e:
            print("[DB] save game_type error:", e)

        try:
            tg_username = f"@{message.from_user.username}" if message.from_user.username else "Không có"
            time_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

            bot.send_photo(
                ADMIN_CHAT_ID,
                state["receipt_file_id"],
                caption=(
                    "📩 KHÁCH GỬI CHUYỂN KHOẢN + CHỌN TRÒ CHƠI\n\n"
                    f"👤 Telegram: {tg_username}\n"
                    f"🧾 Tên tài khoản: {state.get('username_game', '(không rõ)')}\n"
                    f"🆔 Chat ID: {chat_id}\n"
                    f"🎯 Trò chơi: {game_type}\n"
                    f"⏰ Thời gian: {time_str}"
                )
            )

            bot.send_message(chat_id, "✅ Em đã nhận đủ thông tin, em xử lý và cộng điểm cho mình ngay nhé ạ ❤️")
        except Exception as e:
            print("Lỗi gửi admin:", e)
            bot.send_message(chat_id, "⚠️ Em gửi thông tin bị lỗi, mình đợi em 1 chút hoặc nhắn CSKH giúp em nhé ạ.")

        user_state[chat_id] = None
        return

    # --- Nếu đang chờ user gửi tên tài khoản ---
    if state == "WAITING_USERNAME":
        username_game = text

        # DB log (create a new lead for this username)
        try:
            create_lead(chat_id, status="got_username", username_game=username_game, note="username received")
        except Exception as e:
            print("[DB] save username_game error:", e)

        tg_username = f"@{message.from_user.username}" if message.from_user.username else "Không có"
        time_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

        admin_text = (
            "🔔 Có khách mới gửi tên tài khoản\n\n"
            f"👤 Telegram: {tg_username}\n"
            f"🧾 Tên tài khoản: {username_game}\n"
            f"⏰ Thời gian: {time_str}\n"
            f"🆔 Chat ID: {chat_id}"
        )
        try:
            bot.send_message(ADMIN_CHAT_ID, admin_text)
            bot.forward_message(ADMIN_CHAT_ID, chat_id, message.message_id)
        except Exception as e:
            print("Lỗi gửi tin cho admin:", e)

        reply_text = (
            f"Em đã nhận được tên tài khoản: *{username_game}* ✅\n\n"
            "Mình vào U888 lên vốn theo mốc để nhận khuyến mãi giúp em nhé.\n"
            "Lên thành công mình gửi *ảnh chuyển khoản* để em cộng điểm trực tiếp vào tài khoản cho mình ạ.\n\n"
            "Có bất cứ thắc mắc gì nhắn tin trực tiếp cho CSKH U888:\n"
            "👉 [Lan Lan CSKH U888](https://t.me/lanlan2468)\n"
        )

        try:
            bot.send_photo(
                chat_id,
                "AgACAgUAAxkBAAMdaU1p2EF1BAQTJz06A9DRQHFSAAHLAAKmDWsb3MloVuZGYlbmHBU-AQADAgADeQADNgQ",
                caption=reply_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi ảnh reply_text:", e)
            bot.send_message(chat_id, reply_text, parse_mode="Markdown")

        user_state[chat_id] = "WAITING_RECEIPT"
        return


# ================== ẢNH / FILE (CHUYỂN KHOẢN + DEBUG GET_ID) ==================
@bot.message_handler(content_types=['photo', 'document', 'video'])
def handle_media(message):
    chat_id = message.chat.id

    # --- Nếu đang bật chế độ lấy file_id ---
    if chat_id in debug_get_id_mode:
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            media_type = "ẢNH"
        elif message.content_type == 'video':
            file_id = message.video.file_id
            media_type = "VIDEO"
        else:
            file_id = message.document.file_id
            media_type = "FILE"

        bot.reply_to(
            message,
            f"✅ *{media_type} FILE_ID:*\n\n`{file_id}`",
            parse_mode="Markdown"
        )
        return

    # --- Flow nhận ảnh chuyển khoản ---
    if user_state.get(chat_id) != "WAITING_RECEIPT":
        return

    if message.content_type == "photo":
        receipt_file_id = message.photo[-1].file_id
    elif message.content_type == "document":
        receipt_file_id = message.document.file_id
    else:
        bot.send_message(chat_id, "Mình gửi *ảnh chuyển khoản* giúp em nhé ạ.", parse_mode="Markdown")
        return

    # DB log
    try:
        update_latest_lead(chat_id, status="got_receipt", receipt_file_id=receipt_file_id, note="receipt received")
    except Exception as e:
        print("[DB] save receipt error:", e)

    user_state[chat_id] = {
        "state": "WAITING_GAME",
        "receipt_file_id": receipt_file_id,
        "username_game": None
    }

    bot.send_message(
        chat_id,
        "Mình muốn chơi *BCR - Thể Thao*, *Nổ hũ - Bắn Cá* hay *Game bài* ạ?",
        parse_mode="Markdown"
    )


# ================== WEBHOOK FLASK ==================
@server.route("/webhook", methods=['POST'])
def telegram_webhook():
    try:
        json_str = request.get_data(as_text=True)
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        # chống 502 và để log ra Render
        print("WEBHOOK ERROR:", e)
        return "ERR", 500


@server.route("/", methods=['GET'])
def home():
    return "Bot is running!", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("Running on port", port)
    server.run(host="0.0.0.0", port=port)
