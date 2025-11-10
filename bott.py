# crosspromo_bot_v7_ai_complete.py
# Advanced Cross-Promotion Bot with Templates, AI Timings, Analytics & Admin Alerts

import asyncio
import sqlite3
import random
import logging
from datetime import datetime, date
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ChatMemberHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ───────────────────────────────
BOT_TOKEN = "8346086880:AAGuxG4sQveDlPfBkefka01Isq5YFF0qbdw"
OWNER_ID = 8053084391
DB = "promo_ai_bot.db"
OWNER_CHANNEL = "https://t.me/SharkXPanels"
PROMO_INTERVAL = 4 * 3600  # every 4 hours
SEND_BATCH = 100
# ───────────────────────────────

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logger = logging.getLogger("CrossPromoBot")

REGISTER_NAME, REGISTER_PASS, LOGIN_NAME, LOGIN_PASS, TEMPLATE_TEXT = range(5)

# ───────────────────────────────
# Database Setup
# ───────────────────────────────
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        joined_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS channels (
        chat_id INTEGER PRIMARY KEY,
        title TEXT,
        username TEXT,
        invite_link TEXT,
        added_by INTEGER,
        added_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        from_chat INTEGER,
        to_chat INTEGER,
        message TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        promos_done INTEGER,
        total_channels INTEGER,
        status TEXT
    )""")
    conn.commit()
    conn.close()

# ───────────────────────────────
# DB Helpers
# ───────────────────────────────
def add_user(tg_id, name, password):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO users (tg_id, username, password, joined_at) VALUES (?, ?, ?, ?)",
        (tg_id, name, password, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT chat_id, title, username, invite_link FROM channels")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_channel(chat_id, title, username, added_by):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO channels (chat_id, title, username, added_by, added_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, title, username, added_by, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

def record_promo(from_chat, to_chat, message):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (ts, from_chat, to_chat, message) VALUES (?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), from_chat, to_chat, message),
    )
    conn.commit()
    conn.close()

def add_template(content):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO templates (content, created_at) VALUES (?, ?)", (content, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_random_template():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT content FROM templates")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    if rows:
        return random.choice(rows)
    else:
        return "🔥 Check out {channel_name} — join now 👉 {link}"

def add_analytics_record(promos_done, total_channels, status):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO analytics (date, promos_done, total_channels, status) VALUES (?, ?, ?, ?)",
        (date.today().isoformat(), promos_done, total_channels, status),
    )
    conn.commit()
    conn.close()

# ───────────────────────────────
def build_link(chat_id, username, invite):
    if invite:
        return invite
    if username:
        return f"https://t.me/{username}"
    if str(chat_id).startswith("-100"):
        return f"https://t.me/c/{str(chat_id).replace('-100','')}"
    return f"https://t.me/c/{chat_id}"

def is_owner(update):
    return update.effective_user and update.effective_user.id == OWNER_ID

# ───────────────────────────────
# Conversation: Register/Login
# ───────────────────────────────
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = "👋 Welcome to *Cross Promotion Network Bot*\n\nSelect an option:"
    keyboard = [
        [InlineKeyboardButton("📝 Register", callback_data="register")],
        [InlineKeyboardButton("🔐 Login", callback_data="login")],
        [InlineKeyboardButton("📣 Join Owner Channel", url=OWNER_CHANNEL)],
    ]
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_menu")])

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# Register Flow
async def reg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Enter your desired *username*:", parse_mode=ParseMode.MARKDOWN)
    return REGISTER_NAME

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_name"] = update.message.text
    await update.message.reply_text("Now enter a *password*:", parse_mode=ParseMode.MARKDOWN)
    return REGISTER_PASS

async def reg_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data["reg_name"]
    password = update.message.text
    add_user(update.effective_user.id, name, password)
    await update.message.reply_text("✅ Registration successful! Use /start again to open your menu.")
    return ConversationHandler.END

# Login Flow
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Enter your *username*:", parse_mode=ParseMode.MARKDOWN)
    return LOGIN_NAME

async def login_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login_name"] = update.message.text
    await update.message.reply_text("Enter your *password*:")
    return LOGIN_PASS

async def login_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data["login_name"]
    password = update.message.text
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (name, password))
    row = cur.fetchone()
    conn.close()
    if row:
        await update.message.reply_text("✅ Login successful! Use /start again to access your panel.")
    else:
        await update.message.reply_text("❌ Invalid credentials.")
    return ConversationHandler.END

# ───────────────────────────────
# AI Smart Promo System
# ───────────────────────────────
async def ai_promo_system(context: ContextTypes.DEFAULT_TYPE):
    channels = get_channels()
    total_channels = len(channels)
    if total_channels < 2:
        return

    now = datetime.utcnow().hour
    if 2 <= now <= 6:
        logger.info("🌙 Low activity hours, pausing promos...")
        return

    random.shuffle(channels)
    promos_done = 0
    groups = [channels[i:i + SEND_BATCH] for i in range(0, total_channels, SEND_BATCH)]

    for group in groups:
        for src in group:
            tgt = random.choice(channels)
            if src[0] == tgt[0]:
                continue
            link = build_link(tgt[0], tgt[2], tgt[3])
            template = get_random_template()
            msg = template.format(channel_name=tgt[1], link=link)
            try:
                await context.bot.send_message(src[0], msg, parse_mode=ParseMode.MARKDOWN)
                record_promo(src[0], tgt[0], msg)
                promos_done += 1
                await asyncio.sleep(random.uniform(3, 7))
            except Exception as e:
                logger.warning(f"Promo failed in {src[1]}: {e}")

    # After all promotions complete
    add_analytics_record(promos_done, total_channels, "Completed")
    await context.bot.send_message(
        OWNER_ID,
        f"✅ *Daily Promotions Completed*\n\n📊 Total Channels: {total_channels}\n📣 Promos Done: {promos_done}\n🕐 {datetime.now().strftime('%H:%M:%S')}",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("✅ All daily promotions done and admin notified.")

# ───────────────────────────────
# Admin Panel
# ───────────────────────────────
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.callback_query.answer()
    text = "⚙️ *Admin Control Panel*\nSelect an action:"
    buttons = [
        [InlineKeyboardButton("📊 Analytics", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Force Promotion Now", callback_data="admin_promo")],
        [InlineKeyboardButton("🧩 Add Template", callback_data="admin_addtemplate")],
        [InlineKeyboardButton("🗂 Channels List", callback_data="admin_channels")],
    ]
    await update.callback_query.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons)
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM channels")
    total_channels = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM logs")
    total_logs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM templates")
    total_templates = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM analytics")
    total_analytics = cur.fetchone()[0]
    conn.close()

    msg = (
        f"📊 *Bot Analytics:*\n"
        f"👥 Users: {total_users}\n"
        f"📣 Channels: {total_channels}\n"
        f"🧩 Templates: {total_templates}\n"
        f"📈 Analytics Records: {total_analytics}\n"
        f"🚀 Promotions Logged: {total_logs}\n"
        f"🕐 Updated: {datetime.now().strftime('%H:%M:%S')}"
    )
    await update.callback_query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def admin_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    chs = get_channels()
    msg = "🗂 *Registered Channels:*\n\n"
    for c in chs:
        msg += f"• {c[1]} (`{c[2] or 'No username'}`)\n"
    await update.callback_query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def admin_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Running promotion...")
    await ai_promo_system(context)
    await update.callback_query.message.reply_text("✅ Promotion batch executed successfully!")

async def admin_addtemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "🧩 Send your new template text.\n\nYou can use placeholders:\n"
        "`{channel_name}` → channel title\n`{link}` → channel link",
        parse_mode=ParseMode.MARKDOWN,
    )
    return TEMPLATE_TEXT

async def save_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = update.message.text
    add_template(content)
    await update.message.reply_text("✅ Template saved successfully! It will be used in future promotions.")
    return ConversationHandler.END

# ───────────────────────────────
# Channel Admin Handler
# ───────────────────────────────
async def my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.my_chat_member
    chat = m.chat
    if chat.type == "channel" and m.new_chat_member.status == "administrator":
        add_channel(chat.id, chat.title or "Unnamed", chat.username or None, update.effective_user.id)
        await context.bot.send_message(chat.id, "✅ Channel registered for cross-promotion!")

# ───────────────────────────────
# Main
# ───────────────────────────────
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    job_queue = app.job_queue

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(ChatMemberHandler(my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    app.add_handler(CallbackQueryHandler(admin_menu, pattern="admin_menu"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="admin_stats"))
    app.add_handler(CallbackQueryHandler(admin_channels, pattern="admin_channels"))
    app.add_handler(CallbackQueryHandler(admin_promo, pattern="admin_promo"))
    app.add_handler(CallbackQueryHandler(admin_addtemplate, pattern="admin_addtemplate"))

    app.add_handler(
        ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_addtemplate, pattern="admin_addtemplate")],
            states={TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_template)]},
            fallbacks=[],
        )
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[CallbackQueryHandler(reg_start, pattern="register")],
            states={
                REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
                REGISTER_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_pass)],
            },
            fallbacks=[],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CallbackQueryHandler(login_start, pattern="login")],
            states={
                LOGIN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_name)],
                LOGIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_pass)],
            },
            fallbacks=[],
        )
    )

    if job_queue:
        job_queue.run_repeating(ai_promo_system, interval=PROMO_INTERVAL, first=10)
        logger.info("🧠 JobQueue active. AI promo system scheduled.")
    else:
        logger.warning("⚠️ JobQueue not available.")

    logger.info("🤖 CrossPromo AI Bot v7 running...")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
