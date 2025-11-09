# crosspromo_bot.py
# Fully Fixed Advanced Cross-Promo Telegram Bot
# Works on python-telegram-bot v21+
# Compatible with Termux and Linux
# ----------------------------------------------

import asyncio
import sqlite3
import html
import random
import logging
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    JobQueue,
    ChatMemberHandler,
)
import re

# --------- CONFIG ----------
BOT_TOKEN = "8202116916:AAEexk7394fP6mPzpbWmTEzEqDZkSzF3fXw"  # Replace with your bot token
OWNER_USERNAME = "@SharkXOFC"       # Replace with your Telegram username
DB = "crosspromo.db"
KEYWORDS = ["download", "username", "password"]
PROMO_TEMPLATE = (
    "🔥 Partner Channel of the Day:\n👉 {link}\n"
    "Join Now For Exclusive Antiban Hacks\n\n{extra}"
)
# ---------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            username TEXT,
            password TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            username TEXT,
            invite_link TEXT,
            added_by INTEGER,
            added_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            from_chat INTEGER,
            to_chat INTEGER,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(tg_id, username, password):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (tg_id, username, password, created_at) VALUES (?, ?, ?, ?)",
        (tg_id, username, password, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def count_users():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count

def add_channel(chat_id, title, username, added_by=None):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO channels (chat_id, title, username, invite_link, added_by, added_at)
        VALUES (?, ?, ?, COALESCE((SELECT invite_link FROM channels WHERE chat_id = ?), ''), ?, ?)
    """, (chat_id, title, username or "", chat_id, added_by, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def remove_channel(chat_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def list_channels():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT chat_id, title, username, invite_link FROM channels")
    rows = cur.fetchall()
    conn.close()
    return rows

def set_invite_link(chat_id, link):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE channels SET invite_link = ? WHERE chat_id = ?", (link, chat_id))
    conn.commit()
    conn.close()

def log_promo(from_chat, to_chat, msg):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (ts, from_chat, to_chat, message) VALUES (?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), from_chat, to_chat, msg)
    )
    conn.commit()
    conn.close()

# ---------- UTILITIES ----------
def is_owner(update: Update):
    return update.effective_user and update.effective_user.username and ("@" + update.effective_user.username) == OWNER_USERNAME

def build_channel_link(chat_id, username, invite):
    if username:
        return f"https://t.me/{username}"
    if invite:
        return invite
    if str(chat_id).startswith("-100"):
        return f"https://t.me/c/{str(chat_id).replace('-100', '')}"
    return f"https://t.me/c/{chat_id}"

# ---------- COMMAND HANDLERS ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"👋 Welcome to CrossPromo Bot\n\n"
        f"👑 Owner: {OWNER_USERNAME}\n\n"
        "🧩 Commands:\n"
        "/register <username> <password>\n"
        "/login <username> <password>\n\n"
        "📢 Owner-only commands:\n"
        "/stats, /channels, /addInvite <chat_id> <link>\n"
        "/sendPostAll <text>, /broadcastUsers <text>, /postNow\n\n"
        "To register a channel, add this bot as ADMIN with 'Post Messages' permission."
    )
    await update.message.reply_text(msg)

async def register_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /register <username> <password>")
    add_user(update.effective_user.id, context.args[0], context.args[1])
    await update.message.reply_text("✅ Account created successfully!")

async def login_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /login <username> <password>")
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (context.args[0], context.args[1]))
    r = cur.fetchone()
    conn.close()
    if r:
        await update.message.reply_text("✅ Login successful!")
    else:
        await update.message.reply_text("❌ Invalid credentials.")

# ✅ FIXED HANDLER FOR BOT ADMIN ADDITION
async def my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        m = update.my_chat_member
        chat = m.chat
        new_status = m.new_chat_member
        if chat.type == "channel" and new_status.status == "administrator":
            add_channel(chat.id, chat.title or "", chat.username or "", update.effective_user.id if update.effective_user else None)
            await context.bot.send_message(chat.id, "✅ This channel is now registered for cross-promotion.")
            logger.info("Added channel: %s (%s)", chat.title, chat.id)
        elif new_status.status in ("left", "kicked"):
            remove_channel(chat.id)
            logger.info("Removed channel: %s", chat.id)
    except Exception as e:
        logger.exception("Error in my_chat_member: %s", e)

async def channels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Owner only.")
    chs = list_channels()
    if not chs:
        return await update.message.reply_text("No channels registered.")
    txt = "📋 Registered Channels:\n\n"
    for cid, title, uname, inv in chs:
        txt += f"{title} | @{uname or 'no_username'} | ID: {cid}\n"
    await update.message.reply_text(txt)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Owner only.")
    await update.message.reply_text(f"📊 Total Channels: {len(list_channels())}\n👥 Total Users: {count_users()}")

async def add_invite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Owner only.")
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /addInvite <chat_id> <invite_link>")
    set_invite_link(int(context.args[0]), context.args[1])
    await update.message.reply_text("✅ Invite link added.")

async def send_post_all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Owner only.")
    if not context.args:
        return await update.message.reply_text("Usage: /sendPostAll <text>")
    text = " ".join(context.args)
    chs = list_channels()
    if not chs:
        return await update.message.reply_text("No channels registered.")
    for i, src in enumerate(chs):
        tgt = chs[(i + 1) % len(chs)]
        link = build_channel_link(tgt[0], tgt[2], tgt[3])
        msg = text
        for kw in KEYWORDS:
            msg = re.sub(rf"(?i){kw}", f'<a href="{html.escape(link)}">{kw}</a>', msg)
        try:
            await context.bot.send_message(src[0], msg, parse_mode=ParseMode.HTML)
            log_promo(src[0], tgt[0], text)
        except Exception as e:
            logger.warning("Failed send to %s: %s", src[0], e)
    await update.message.reply_text("✅ Sent to all channels with link replacements.")

async def broadcast_users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await update.message.reply_text("❌ Owner only.")
    if not context.args:
        return await update.message.reply_text("Usage: /broadcastUsers <text>")
    text = " ".join(context.args)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT tg_id FROM users")
    users = cur.fetchall()
    conn.close()
    for u in users:
        try:
            await context.bot.send_message(u[0], text)
        except:
            pass
    await update.message.reply_text("✅ Broadcast complete.")

async def cross_promo_once(context: ContextTypes.DEFAULT_TYPE):
    chs = list_channels()
    if len(chs) < 2:
        return
    for i, src in enumerate(chs):
        tgt = chs[(i + 1) % len(chs)]
        link = build_channel_link(tgt[0], tgt[2], tgt[3])
        extra = f"Promoting: {tgt[1]}"
        promo = PROMO_TEMPLATE.format(link=link, extra=extra)
        try:
            await context.bot.send_message(src[0], promo, parse_mode=ParseMode.HTML)
            log_promo(src[0], tgt[0], promo)
        except Exception as e:
            logger.warning("Cross-promo failed: %s", e)

# ---------- MAIN ----------
def main():
    init_db()

    job_queue = JobQueue()
    app = ApplicationBuilder().token(BOT_TOKEN).job_queue(job_queue).build()
    job_queue.set_application(app)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("register", register_cmd))
    app.add_handler(CommandHandler("login", login_cmd))
    app.add_handler(CommandHandler("channels", channels_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("addInvite", add_invite_cmd))
    app.add_handler(CommandHandler("sendPostAll", send_post_all_cmd))
    app.add_handler(CommandHandler("broadcastUsers", broadcast_users_cmd))

    # ✅ FIXED: Proper handler for bot being added/removed as admin
    app.add_handler(ChatMemberHandler(my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    job_queue.run_repeating(cross_promo_once, interval=21600, first=10)  # every 6h

    logger.info("🤖 Bot started successfully!")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
