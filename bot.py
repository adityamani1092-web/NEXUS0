import os
import asyncio
import random
import time
import re
import html
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from waitress import serve
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatJoinRequestHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from db import (
    init_db, upsert_user, get_user_by_username, get_user_by_id, add_log,
    is_owner, get_owner_id, get_filters, add_filter, remove_filter,
    add_media_filter, get_media_filters, get_media_filter, remove_media_filter,
    list_users, list_logs, get_settings, set_setting, get_stats, upsert_group_user, list_group_users,
    mark_dm_started, has_dm_started, adjust_score, get_score, leaderboard, buy_aura_protection,
    get_name_history, remember_group, get_known_groups, get_broadcast_users,
    set_free_member, is_free_member
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
WEB_SECRET = os.getenv("WEB_SECRET", "").strip()
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
PORT = int(os.getenv("PORT", "8080"))
COUPLE_COOLDOWN_SECONDS = 6 * 60 * 60
ACTIVE_PUZZLES = {}
POSITIVE_WORDS = set("love lovely loved loving kind kindness nice good great awesome amazing excellent beautiful happy happiness smile smiling joy joyful positive helpful help thanks thank you welcome please respect respectful honest honesty brave courage confident calm peaceful peace friendly friend friendship support supportive care caring sweet wonderful fantastic perfect brilliant smart clever creative success successful win winner proud proudness hope hopeful trust trusted trustful safe secure fair fairness gentle generous generousity polite politey patient patience grateful gratitude appreciate appreciated admire admirable strong strength healthy healing comfort comforted relax relaxed relaxes laugh laughter funny hilarious cool cute adorable gorgeous pretty handsome delightful inspiring inspire inspired motivated motivate motivate dream dreamer dreamful bless blessed blessing lucky fortunate celebrate celebration congratulations congrats welcome yay yes agree correct true accurate reliable loyal loyalist dependable awesome superb splendid marvelous outstanding remarkable radiant sunshine cheerful cheerful bright warm warmth tender tenderly compassionate compassion empathy empathetic understanding thoughtful thoughtfulness considerate consideration generous-hearted uplifting encourage encouraged encouragement achieve achieved achievement improve improved progress progressful thrive thriving flourish flourishing freedom harmony harmony loveable lovable trustful truthful truth sincere sincerity integrity dignified dignity forgive forgiveness forgiven sorry apology apologize reconcile reconciliation calmness serenity tranquil tranquilize relief relieved relief soothing soothe comfort comforting safe safety secure security balance balanced mindful mindfulness wisdom wise intelligent insight insightful learn learning teach teacher educate education curious curiosity wonder wonderful valuable worthy worthiness capable capability talent talented skillful skill achievement patience resilient resilience persistent persistence determined determination focus focused clarity clear claritywise optimistic optimism faith faithfulness reliable dependable dependable cheer cheer up bravo kudos respectfulness unity together togetherness community teamwork team helpfulness".split())
NEGATIVE_WORDS = set("hate hateful hated hatred bad awful terrible horrible worst ugly stupid idiot dumb fool foolish useless worthless trash garbage disgusting annoying annoyingness angry anger mad furious rage rude impolite disrespect disrespectful cruel cruelty mean toxic toxicness evil wicked nasty dirty disgusting liar lying lie false fake fraud scam cheat cheating cheated betray betrayal traitor selfish selfishness greedy greed jealous jealousy envy envious sad sadness unhappy miserable depressed lonely loneliness hopeless despair despairing fear afraid scared panic anxious anxiety worry worried stress stressed tired exhausted weak weakness failure fail failed lose loser loss wrong incorrect mistake error broken damage harm harmful hurt hurting pain painful suffer suffering sick illness danger dangerous unsafe insecure unfair injustice unfairness guilty shame ashamed regret regretful blame blameworthy fault careless reckless lazy laziness boring bored dull boringness annoying irritating irritatingly irritating rude harsh harshly violent violence aggressive aggression threat threaten threatful curse cursed damn hell damnation pathetic coward cowardly cowardice stupidly clueless ignorant ignorance arrogant arrogance prideful conceited vain vanity boast boastful brag bragging complain complaint whining whiny pessimistic pessimism hopelessness uselessness failureful miserable misery grief grieving sorrow sorrowful weep crying cry tears tearful depressed depress depressing gloomy doom doomed failure shameful disgrace disgraceful insult insulting offensive offense abusive abuse bully bullying bullied harassment harass humiliation humiliate humiliating failure fail badly weakling incompetent incompetence unreliable untrustworthy dishonest dishonesty unkind cold-hearted heartless insensitive inconsiderate selfish rude hateful spite spiteful malicious malice resentment resentful bitter bitterness hostile hostility conflict fight fighting argument argue attack attacked dangerous risk risky panic stress tension tense frustrated frustration irritated irritation annoyed annoyance regret guilt guilty shame embarrassment embarrassing awkward awkwardness".split())


if not WEB_SECRET:
    raise RuntimeError("Set a long random WEB_SECRET in .env")
if not DASHBOARD_PASSWORD:
    raise RuntimeError("Set DASHBOARD_PASSWORD in .env")
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in .env")
if OWNER_ID <= 0:
    raise RuntimeError("Set numeric OWNER_ID in .env")

init_db(OWNER_ID)
app = Flask(__name__)
app.secret_key = WEB_SECRET

DASH = r"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexus Bot Control</title><style>
:root{--bg:#0b0b0e;--panel:#15151b;--line:#2a2930;--gold:#d9b45b;--muted:#aaa8b3}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#f5f2eb;font:15px/1.5 Inter,system-ui,Arial}
header{padding:24px max(20px,calc((100% - 1120px)/2));border-bottom:1px solid var(--line);background:#101014;display:flex;justify-content:space-between;align-items:center}
.brand{font-size:22px;font-weight:800;letter-spacing:.3px}.brand span{color:var(--gold)}main{max-width:1120px;margin:26px auto;padding:0 18px}
h2{font-size:19px;margin:0 0 14px}.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:16px}
.stat{font-size:30px;font-weight:800;color:var(--gold)}input,select,button{font:inherit;border-radius:9px;border:1px solid #3b3943;padding:10px 12px;background:#101015;color:#fff;max-width:100%}
button,.btn{background:var(--gold);color:#17130a;border:0;font-weight:750;cursor:pointer;text-decoration:none;display:inline-block}
form{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--gold)}
.notice{padding:10px 12px;border-radius:10px;background:#242016;color:#f1dca5;margin:12px 0}.danger{color:#ff9999}
@media(max-width:650px){header{padding:18px;align-items:flex-start;gap:12px}table{font-size:12px}td,th{padding:7px}}
</style></head><body>
<header><div class="brand">🌹 Nexus Bot <span>Control</span><div class="muted" style="font-size:12px;font-weight:400">Group Management Console</div></div>
{% if logged %}<a class="btn" href="/logout">Logout</a>{% endif %}</header><main>
{% with messages=get_flashed_messages() %}{% if messages %}{% for m in messages %}<div class="notice">{{m}}</div>{% endfor %}{% endif %}{% endwith %}
{% if not logged %}
<div class="card" style="max-width:440px;margin:60px auto"><h2>Admin sign in</h2><p class="muted">Only the configured dashboard account can access this console.</p>
<form method="post" action="/login" style="display:block"><p><input name="username" placeholder="Username" required style="width:100%"></p><p><input name="password" type="password" placeholder="Password" required style="width:100%"></p><button>Sign in</button></form></div>
{% else %}
<div class="grid">
<div class="card"><div class="muted">Tracked users</div><div class="stat">{{stats.users}}</div></div>
<div class="card"><div class="muted">Media filters</div><div class="stat">{{stats.media_filters}}</div></div>
<div class="card"><div class="muted">Saved filters</div><div class="stat">{{stats.filters}}</div></div>
<div class="card"><div class="muted">Moderation logs</div><div class="stat">{{stats.logs}}</div></div>
</div>
<div class="card"><h2>Keyword filters</h2><p class="muted">These filters apply in groups where this bot is an admin and can delete messages.</p>
<form method="post" action="/filter"><input name="keyword" placeholder="Keyword to match" required><input name="response" placeholder="Optional reply (can be blank)"><button>Add filter</button></form>
{% if filters %}<table><tr><th>Keyword</th><th>Response</th><th>Action</th></tr>{% for f in filters %}<tr><td>{{f.keyword}}</td><td>{{f.response or 'Delete only'}}</td><td><form method="post" action="/filter/delete"><input type="hidden" name="keyword" value="{{f.keyword}}"><button>Delete</button></form></td></tr>{% endfor %}</table>{% else %}<p class="muted">No text filters yet.</p>{% endif %}</div>
<div class="card"><h2>Sticker & media auto-replies</h2><p class="muted">Reply to any sticker/media in Telegram with <code>/filter your reply text</code> to save it.</p>
{% if media_filters %}<table><tr><th>Media type</th><th>Response</th><th>Action</th></tr>{% for f in media_filters %}<tr><td>{{f.media_type}}</td><td>{{f.response or 'No reply'}}</td><td><form method="post" action="/media-filter/delete"><input type="hidden" name="media_key" value="{{f.media_key}}"><button>Delete</button></form></td></tr>{% endfor %}</table>{% else %}<p class="muted">No media filters yet.</p>{% endif %}</div>
<div class="card"><h2>Recent users</h2><table><tr><th>User ID</th><th>Username</th></tr>
{% for u in users %}<tr><td>{{u.user_id}}</td><td>{{'@'+u.username if u.username else '—'}}</td></tr>{% endfor %}</table></div>
<div class="card"><h2>Recent audit log</h2><table><tr><th>Time (UTC)</th><th>Actor</th><th>Action</th><th>Target</th><th>Details</th></tr>
{% for l in logs %}<tr><td>{{l.created_at}}</td><td>{{l.actor_id}}</td><td>{{l.action}}</td><td>{{l.target_id or '—'}}</td><td>{{l.details}}</td></tr>{% endfor %}</table></div>
{% endif %}</main></body></html>
"""

def dashboard_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper

@app.get("/")
def home():
    logged = bool(session.get("logged_in"))
    return render_template_string(
        DASH, logged=logged,
        stats=get_stats() if logged else {},
        users=list_users(50) if logged else [],
        filters=get_filters() if logged else [],
        media_filters=get_media_filters() if logged else [],
        logs=list_logs(30) if logged else []
    )

@app.post("/login")
def login():
    if request.form.get("username") == DASHBOARD_USER and request.form.get("password") == DASHBOARD_PASSWORD:
        session.clear()
        session["logged_in"] = True
        return redirect(url_for("home"))
    flash("Invalid login.")
    return redirect(url_for("home"))

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

def resolve_dashboard_target(value):
    value = (value or "").strip()
    if value.startswith("@"):
        user = get_user_by_username(value[1:])
        return user["user_id"] if user else None
    if value.isdigit():
        return int(value)
    return None

@app.post("/filter")
@dashboard_login_required
def filter_add():
    keyword = (request.form.get("keyword") or "").strip().lower()
    response = (request.form.get("response") or "").strip()
    if not keyword or len(keyword) > 100:
        flash("Keyword must be 1–100 characters.")
    else:
        add_filter(keyword, response)
        add_log(OWNER_ID, "filter_add", None, f"keyword={keyword}")
        flash("Filter saved.")
    return redirect(url_for("home"))

@app.post("/filter/delete")
@dashboard_login_required
def filter_delete():
    keyword = (request.form.get("keyword") or "").strip().lower()
    remove_filter(keyword)
    add_log(OWNER_ID, "filter_delete", None, f"keyword={keyword}")
    flash("Filter deleted.")
    return redirect(url_for("home"))

@app.post("/media-filter/delete")
@dashboard_login_required
def media_filter_delete():
    key = (request.form.get("media_key") or "").strip()
    remove_media_filter(key)
    add_log(OWNER_ID, "media_filter_delete", None, f"key={key[:100]}")
    flash("Media filter deleted.")
    return redirect(url_for("home"))

async def safe_reply(update, text, **kwargs):
    if update.effective_message:
        await update.effective_message.reply_text(text, **kwargs)

def actor_is_owner(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == OWNER_ID)

async def tracked(update: Update):
    user = update.effective_user
    chat = update.effective_chat
    if user:
        upsert_user(user.id, user.username, user.first_name)
        if chat and chat.type in ("group", "supergroup"):
            upsert_group_user(chat.id, user.id, user.username, user.first_name)

async def command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    user = update.effective_user
    chat = update.effective_chat
    if user and chat and chat.type == "private":
        mark_dm_started(user.id)
    username = getattr(context.bot, "username", None)
    add_group_url = f"https://t.me/{username}?startgroup=true" if username else "https://t.me/"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ADD TO GROUP", url=add_group_url)],
        [InlineKeyboardButton("📚 HELP & COMMANDS", callback_data="start:help"), InlineKeyboardButton("🏓 PING", callback_data="start:ping")],
        [InlineKeyboardButton("🎮 GAMES", callback_data="start:games")],
        [InlineKeyboardButton("👑 OWNER: @Look_at_me60", url="https://t.me/Look_at_me60")],
    ])
    msg = update.effective_message
    if msg:
        private_note = "\n\n✅ DM activated — start me here before using group games." if chat and chat.type == "private" else "\n\n📩 To play, open my DM and press Start first."
        caption = (
            "🌌 <b>𝐍𝐄𝐗𝐔𝐒</b> — 𝐘𝐎𝐔𝐑 𝐓𝐄𝐋𝐄𝐆𝐑𝐀𝐌 𝐂𝐎𝐌𝐏𝐀𝐍𝐈𝐎𝐍\n\n"
            "✨ Aura & Leaderboards • 🎮 Games & Puzzles\n"
            "🛡️ Group Management • 🔎 Filters & Tools\n"
            "📢 Broadcasting • 💞 Social Features\n\n"
            "👑 <b>Developer:</b> Aditya Mani\n"
            "🔗 <b>Owner:</b> <a href=\"https://t.me/Look_at_me60\">@Look_at_me60</a>\n"
            "⚡ <i>One Bot. Infinite Possibilities.</i>" + private_note
        )
        banner = os.path.join(os.path.dirname(__file__), "nexus_banner.png")
        try:
            with open(banner, "rb") as photo:
                await msg.reply_photo(photo=photo, caption=caption, parse_mode="HTML", reply_markup=keyboard)
        except Exception:
            await msg.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.perf_counter()
    msg = update.effective_message
    if msg:
        sent = await msg.reply_text("🏓 Pinging Nexus Bot…")
        elapsed = round((time.perf_counter() - start) * 1000)
        await sent.edit_text(f"🏓 **Pong!**\n⚡ Response: `{elapsed} ms`\n🌹 Nexus Bot is online.", parse_mode="Markdown")

HELP_CATEGORIES = {
    "handbook": ("📖 HANDBOOK", """Welcome to NEXUS PREMIUM!

Use the buttons below to browse commands. Group moderation commands need admin permissions. DM broadcasting only reaches users who have pressed /start."""),
    "aura": ("✨ AURA", """/points — your points and Aura
/top — group points leaderboard
/auratop — Aura leaderboard
/giveaura — give Aura to a member
/protect 1d or /protect 2d — protect Aura using coins"""),
    "tools": ("❖ TOOLS", """/imagine <prompt> — generate an AI image in this chat
/image <prompt> — alias for /imagine
/ping — check bot response time
/id — show your ID and chat ID
/info [@username|ID] or reply — user info
/history [@username|ID] or reply — saved user history
/translate hi|en|off — translation setting"""),
    "social": ("℘ SOCIAL", """/couple — couple of the day / fresh pair
/report reason — report a replied-to message to admins
/adminlist — show group admins"""),
    "games": ("# GAMES", """/hidden — missing-letter word
/scramble — unscramble letters
/anagram — rearrange letters
/wordle — guess hidden word
/hangman — guess the word
/wordchain — word-chain prompt
/fasttype — typing challenge
/guessnumber — number guessing
/riddle — solve a riddle
/emojiquiz — emoji puzzle
/mathquiz — maths challenge
/truefalse — true/false quiz
/trivia — general knowledge
/puzzlehelp — game list"""),
    "core": ("⌘ CORE", """/start — start bot and open menu
/help — open this help menu
/ping — response timing
/filter keyword response — text auto-reply
Reply to media with /filter response text — media auto-reply
/filters — list filters"""),
    "admin": ("🛡 ADMIN", """For group admins:
/ban [target] or reply
/unban [target] or reply
/mute [target] [minutes] or reply
/unmute [target] or reply
/lock [type] — lock chat permissions
/unlock [type] — unlock permissions
/lockinfo — lock information
/antispam on|off — spam protection
/free and /unfree — manage exemptions
/approve USER_ID or /decline USER_ID — join requests"""),
    "misc": ("🌾 MISCELLANEOUS", """/broadcast message — owner: known groups + opted-in DMs
/broadcastdm message — owner: DM users who pressed Start
/broadcastgroups message — owner: groups
/broadcast_at YYYY-MM-DD HH:MM message — schedule broadcast
/setcoupleimage — owner: reply to a photo to set couple image

🔞 Adult sticker filter checks configured sticker-set names; it cannot reliably identify explicit pixels."""),
}

def help_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▦ Handbook", callback_data="help:handbook")],
        [InlineKeyboardButton("✿ Aura", callback_data="help:aura"), InlineKeyboardButton("❀ Auraboard", callback_data="help:aura")],
        [InlineKeyboardButton("❖ Tools", callback_data="help:tools"), InlineKeyboardButton("℘ Social", callback_data="help:social")],
        [InlineKeyboardButton("# Games", callback_data="help:games")],
        [InlineKeyboardButton("⌘ Core", callback_data="help:core"), InlineKeyboardButton("🛡 Admin", callback_data="help:admin")],
        [InlineKeyboardButton("🌾 Miscellaneous", callback_data="help:misc")],
    ])

async def show_help_menu(message):
    banner = os.path.join(os.path.dirname(__file__), "help_banner.jpg")
    caption = "<b>🌌 NEXUS — HELP CENTER</b>\n\nChoose a category below to explore commands.\n👑 Owner: <a href=\"https://t.me/Look_at_me60\">@Look_at_me60</a>"
    keyboard = help_keyboard()
    try:
        with open(banner, "rb") as photo:
            await message.reply_photo(photo=photo, caption=caption, parse_mode="HTML", reply_markup=keyboard)
    except (OSError, Exception):
        await message.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)

async def start_buttons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    if data == "start:help":
        await query.answer()
        await show_help_menu(query.message)
    elif data == "start:ping":
        await query.answer()
        await query.message.reply_text("🏓 Pong! NEXUS Bot is online. Use /ping for response timing.")
    elif data == "start:games":
        await query.answer()
        games_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧩 Puzzle Games", callback_data="games:puzzles")],
            [InlineKeyboardButton("📖 All Game Commands", callback_data="help:games")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="start:home")],
        ])
        await query.message.reply_text("🎮 <b>NEXUS GAMES</b>\n\nChoose a game category below. Games are played in groups.", parse_mode="HTML", reply_markup=games_keyboard)
    elif data == "games:puzzles":
        await query.answer()
        await query.message.reply_text(puzzle_help_text())
    elif data == "start:home":
        await query.answer("Use /start to reopen the main menu.")
    elif data.startswith("help:"):
        await query.answer()
        key = data.split(":", 1)[1]
        title, body = HELP_CATEGORIES.get(key, HELP_CATEGORIES["handbook"])
        back = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Help Menu", callback_data="help:home")]])
        await query.message.reply_text(f"<b>{title}</b>\n\n{body}", parse_mode="HTML", reply_markup=back)
    elif data == "help:home":
        await query.answer()
        await show_help_menu(query.message)
    else:
        await query.answer()

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    if update.effective_message:
        await show_help_menu(update.effective_message)

async def dm_game_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Games require each player to have pressed /start in the bot's private chat."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or chat.type not in ("group", "supergroup"):
        return True
    if has_dm_started(user.id):
        return True
    bot_username = getattr(context.bot, "username", None)
    dm_url = f"https://t.me/{bot_username}?start=play" if bot_username else "https://t.me/"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Start Nexus Bot in DM", url=dm_url)]])
    msg = update.effective_message
    if msg:
        await msg.reply_text(
            "🔒 To play games or use /couple, first open Nexus Bot in private chat and press Start. "
            "Then return here. Each player must do this once.", reply_markup=keyboard
        )
    return False

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show ID for yourself, or for the user whose message you replied to."""
    await tracked(update)
    msg = update.effective_message
    chat = update.effective_chat
    target_user = None
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
        upsert_user(target_user.id, target_user.username, target_user.first_name)
    else:
        target_user = update.effective_user
    user_id = target_user.id if target_user else None
    name = html.escape(target_user.full_name) if target_user else "Unknown"
    username = f"@{html.escape(target_user.username)}" if target_user and target_user.username else "Not set"
    profile = f"tg://user?id={user_id}" if user_id else "https://t.me/"
    text = (
        "╭━━━〔 🌌 <b>NEXUS</b> 〕━━━╮\n"
        "       🆔 <b>ID INFORMATION</b>\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"👤 <b>Name:</b> {name}\n"
        f"📛 <b>Username:</b> {username}\n"
        f"🆔 <b>User ID:</b> <code>{user_id if user_id else 'Unknown'}</code>\n"
        f"💬 <b>Chat ID:</b> <code>{chat.id if chat else 'Unknown'}</code>\n\n"
        f"👑 <b>Owner:</b> @Look_at_me60"
    )
    await safe_reply(update, text, parse_mode="HTML", disable_web_page_preview=True)

async def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reply target wins; otherwise accept numeric ID or previously seen @username.
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user
        upsert_user(target.id, target.username, target.first_name)
        return target.id
    if not context.args:
        return None
    token = context.args[0].strip()
    if token.isdigit():
        return int(token)
    if token.startswith("@"):
        found = get_user_by_username(token[1:])
        return found["user_id"] if found else None
    return None

async def caller_is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if actor_is_owner(update):
        return True
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or chat.type not in ("group", "supergroup"):
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False

async def moderation_target(update, context):
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can use this command.")
        return None
    if not update.effective_chat or update.effective_chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use this moderation command inside a group.")
        return None
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Target not found. Reply to a user's message, use numeric ID, or use a username already seen by the bot.")
        return None
    return target

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await moderation_target(update, context)
    if not target: return
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id, target)
        add_log(update.effective_user.id, "ban", target, f"chat={chat_id}")
        await safe_reply(update, f"✅ Banned user ID {target}.")
    except Exception as e:
        await safe_reply(update, f"Could not ban user {target}. Check bot admin permissions and target ID. ({type(e).__name__})")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await moderation_target(update, context)
    if not target: return
    chat_id = update.effective_chat.id
    try:
        await context.bot.unban_chat_member(chat_id, target, only_if_banned=True)
        add_log(update.effective_user.id, "unban", target, f"chat={chat_id}")
        await safe_reply(update, f"✅ Unbanned user ID {target}.")
    except Exception as e:
        await safe_reply(update, f"Could not unban user {target}. ({type(e).__name__})")

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await moderation_target(update, context)
    if not target: return
    try:
        minutes = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 60
        minutes = max(1, min(minutes, 10080))
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        perms = ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False,
            can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
            can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
            can_add_web_page_previews=False)
        await context.bot.restrict_chat_member(update.effective_chat.id, target, permissions=perms, until_date=until)
        add_log(update.effective_user.id, "mute", target, f"minutes={minutes}; chat={update.effective_chat.id}")
        await safe_reply(update, f"🔇 Muted user ID {target} for {minutes} minutes.")
    except Exception as e:
        await safe_reply(update, f"Could not mute user {target}. Check bot permissions. ({type(e).__name__})")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await moderation_target(update, context)
    if not target: return
    try:
        perms = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
            can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True)
        await context.bot.restrict_chat_member(update.effective_chat.id, target, permissions=perms)
        add_log(update.effective_user.id, "unmute", target, f"chat={update.effective_chat.id}")
        await safe_reply(update, f"🔊 Unmuted user ID {target}.")
    except Exception as e:
        await safe_reply(update, f"Could not unmute user {target}. ({type(e).__name__})")

async def free_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exempt a group member from anti-spam by reply, numeric ID, or known @username."""
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can use /free.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /free in a group. Reply to a member, or use /free USER_ID /free @username.")
        return
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Usage: reply to a member with /free, or use /free USER_ID /free @username (username must be known to the bot).")
        return
    set_free_member(chat.id, target, True)
    add_log(update.effective_user.id, "free_member", target, f"chat={chat.id}")
    await safe_reply(update, f"✅ User ID {target} is now free from anti-spam in this group. Use /unfree to remove the exemption.")

async def unfree_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can use /unfree.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /unfree in a group.")
        return
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Usage: reply to a member with /unfree, or /unfree USER_ID /unfree @username.")
        return
    set_free_member(chat.id, target, False)
    add_log(update.effective_user.id, "unfree_member", target, f"chat={chat.id}")
    await safe_reply(update, f"✅ Anti-spam exemption removed for user ID {target} in this group.")

async def antispam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle basic anti-flood and repeated-message protection for this group."""
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can control anti-spam.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /antispam on or /antispam off in a group.")
        return
    arg = context.args[0].lower() if context.args else "status"
    key = f"antispam:{chat.id}"
    if arg in ("on", "enable", "enabled"):
        set_setting(key, "1")
        await safe_reply(update, "🛡️ Anti-spam ON. Flood and repeated messages will be removed; repeated offenders may be muted briefly.")
    elif arg in ("off", "disable", "disabled"):
        set_setting(key, "0")
        await safe_reply(update, "⚠️ Anti-spam OFF for this group.")
    elif arg == "status":
        enabled = get_settings().get(key, "1") != "0"
        await safe_reply(update, f"🛡️ Anti-spam is {'ON' if enabled else 'OFF'}. Use /antispam on or /antispam off.")
    else:
        await safe_reply(update, "Usage: /antispam on | /antispam off | /antispam status")

async def check_antispam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not chat or not user or user.is_bot or chat.type not in ("group", "supergroup"):
        return False
    if get_settings().get(f"antispam:{chat.id}", "1") == "0":
        return False
    # /free exemptions are scoped to this group and survive bot restarts.
    if is_free_member(chat.id, user.id):
        return False
    # Never apply the anti-spam filter to admins/owner.
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if user.id == OWNER_ID or member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return False
    except Exception:
        pass
    now = time.time()
    bucket = context.application.bot_data.setdefault("spam_activity", {})
    key = (chat.id, user.id)
    state = bucket.setdefault(key, {"times": [], "texts": []})
    state["times"] = [t for t in state["times"] if now - t < 8]
    state["times"].append(now)
    body = (msg.text or msg.caption or "[media]").strip().casefold()
    if body:
        state["texts"] = [(t, text) for t, text in state["texts"] if now - t < 30]
        state["texts"].append((now, body[:300]))
    flood = len(state["times"]) >= 7
    repeats = sum(1 for _, text in state["texts"] if text == body) >= 4 and body != "[media]"
    if not (flood or repeats):
        return False
    try:
        await msg.delete()
    except Exception:
        # Bot needs Delete Messages permission to remove spam.
        pass
    add_log(0, "anti_spam_trigger", user.id, f"chat={chat.id}; flood={flood}; repeats={repeats}")
    if flood:
        try:
            until = datetime.now(timezone.utc) + timedelta(seconds=60)
            perms = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(chat.id, user.id, permissions=perms, until_date=until)
            await context.bot.send_message(chat.id, f"🛡️ Anti-spam: {user.full_name} muted for 60 seconds due to flooding.")
        except Exception:
            await context.bot.send_message(chat.id, f"🛡️ Anti-spam detected flooding from {user.full_name}. Bot needs Restrict Members permission to mute.")
    else:
        await context.bot.send_message(chat.id, f"⚠️ {user.full_name}, repeated messages are not allowed.")
    state["times"] = []
    state["texts"] = []
    return True

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Use /history USER_ID, /history @username, or reply to the user's message with /history.")
        return
    rows = get_name_history(target, 50)
    current = get_user_by_id(target)
    if not current:
        await safe_reply(update, f"No saved profile for user ID {target}. The bot can only show details it has observed.")
        return
    now_local = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z (local time)")
    current_name = current.get("first_name") or "(no name saved)"
    current_username = "@" + current["username"] if current.get("username") else "(no username)"
    lines = [f"🧾 USER HISTORY", f"Full name: {current_name}", f"Username: {current_username}", f"User ID: {target}", f"Profile last seen: {current.get('updated_at') or 'unknown'}", f"Checked at: {now_local}", "", "Previous saved names/usernames:"]
    if rows:
        lines.extend(f"• {r['changed_at']} — Name: {r['first_name'] or '(no name)'} | Username: {'@'+r['username'] if r['username'] else '(no username)'}" for r in rows)
    else:
        lines.append("• No changes recorded yet. History begins only after the bot starts tracking this user.")
    await safe_reply(update, "\n".join(lines))

async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update) and not await caller_is_admin(update, context):
        await safe_reply(update, "Only the owner or a group admin can change translation settings.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /translate hi, /translate en, or /translate off in a group.")
        return
    value = context.args[0].lower() if context.args else ""
    if value not in ("hi", "en", "off"):
        await safe_reply(update, "Usage: /translate hi | /translate en | /translate off")
        return
    set_setting(f"translate:{chat.id}", value)
    await safe_reply(update, f"🌐 Automatic translation: {'Hindi' if value == 'hi' else 'English' if value == 'en' else 'OFF'}")

async def adminlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "👑 /adminlist ko group mein use karo.")
        return
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        lines = [f"👑 <b>ADMIN LIST — {html.escape(chat.title or 'Group')}</b>"]
        for member in admins:
            user = member.user
            label = html.escape(("@" + user.username) if user.username else (user.full_name or str(user.id)))
            role = "👑 Owner" if member.status == ChatMemberStatus.OWNER else "🛡️ Admin"
            lines.append(f"{role} · {label} · <code>{user.id}</code>")
        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception:
        await safe_reply(update, "❌ Admin list nahi mil saki. Bot ki group access check karo.")

async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not msg or not user or not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "⚠️ /report ko group mein kisi message ka reply karke use karo.")
        return
    replied = msg.reply_to_message
    if not replied or not replied.from_user:
        await safe_reply(update, "📣 Jis message ko report karna hai us par reply karke /report reason likho.")
        return
    if replied.from_user.id == user.id:
        await safe_reply(update, "Apne hi message ko report nahi kar sakte.")
        return
    reason = " ".join(context.args).strip() or "No reason provided"
    target = replied.from_user
    report_text = (
        "🚨 <b>NEXUS USER REPORT</b>\n"
        f"<b>Group:</b> {html.escape(chat.title or 'Group')} (<code>{chat.id}</code>)\n"
        f"<b>Reported user:</b> {html.escape(target.full_name)} (@{html.escape(target.username or 'no_username')}) · <code>{target.id}</code>\n"
        f"<b>Reported by:</b> {html.escape(user.full_name)} (@{html.escape(user.username or 'no_username')}) · <code>{user.id}</code>\n"
        f"<b>Reason:</b> {html.escape(reason[:800])}\n"
        f"<b>Message:</b> {html.escape((replied.text or replied.caption or '[non-text message]')[:1200])}"
    )
    sent = 0
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        for admin in admins:
            if admin.user.is_bot:
                continue
            try:
                await context.bot.send_message(admin.user.id, report_text, parse_mode="HTML")
                sent += 1
            except Exception:
                pass
    except Exception:
        pass
    if OWNER_ID:
        try:
            await context.bot.send_message(OWNER_ID, report_text, parse_mode="HTML")
            sent += 1
        except Exception:
            pass
    await safe_reply(update, "✅ Report admins/owner ko bhej diya gaya." if sent else "⚠️ Report save/send nahi ho saka. Admins ko bot ka DM pehle start karna pad sakta hai.")

async def _broadcast_targets(update, context, target_kind):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Owner only.")
        return
    body = " ".join(context.args).strip()
    if not body:
        cmd = "broadcastdm" if target_kind == "dm" else "broadcastgroups"
        await safe_reply(update, f"Usage: /{cmd} your message")
        return
    targets = ([('dm', int(x)) for x in get_broadcast_users()] if target_kind == 'dm'
               else [('group', int(x)) for x in get_known_groups()])
    sent = failed = 0
    for kind, target_id in targets:
        try:
            await context.bot.send_message(chat_id=target_id, text=f"📣 NEXUS BROADCAST\n\n{body}")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await safe_reply(update, f"📣 <b>Broadcast complete</b>\nSent: {sent}\nFailed/unavailable: {failed}\nTargets: {len(targets)}")

async def broadcastdm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _broadcast_targets(update, context, "dm")

async def broadcastgroups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _broadcast_targets(update, context, "groups")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Owner only.")
        return
    text_body = " ".join(context.args).strip()
    if not text_body:
        await safe_reply(update, "Usage: /broadcast your message\nScheduled: /broadcast_at YYYY-MM-DD HH:MM your message")
        return
    dm_ids = get_broadcast_users()
    group_ids = get_known_groups()
    targets = [("dm", int(x)) for x in dm_ids] + [("group", int(x)) for x in group_ids]
    sent = failed = 0
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    for kind, target_id in targets:
        try:
            await context.bot.send_message(chat_id=target_id, text=f"📣 Nexus Bot Broadcast\n🕒 {stamp}\n\n{text_body}")
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1
    await safe_reply(update, f"📣 Broadcast finished.\nSent: {sent}\nFailed/unavailable: {failed}\nTargets: {len(targets)}")

async def broadcast_at_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Owner only.")
        return
    raw = update.effective_message.text.partition(" ")[2].strip()
    parts = raw.split(maxsplit=2)
    if len(parts) < 3:
        await safe_reply(update, "Usage: /broadcast_at YYYY-MM-DD HH:MM your message\nExample: /broadcast_at 2026-10-22 20:30 Hello group!")
        return
    try:
        when = datetime.strptime(parts[0] + " " + parts[1], "%Y-%m-%d %H:%M").astimezone()
    except ValueError:
        await safe_reply(update, "Date/time format galat hai. Use YYYY-MM-DD HH:MM (server local time).")
        return
    message_text = parts[2]
    seconds = (when - datetime.now().astimezone()).total_seconds()
    if seconds <= 0:
        await safe_reply(update, "Scheduled time future mein hona chahiye.")
        return
    async def deliver():
        await asyncio.sleep(seconds)
        dm_ids = get_broadcast_users()
        group_ids = get_known_groups()
        targets = [("dm", int(x)) for x in dm_ids] + [("group", int(x)) for x in group_ids]
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        sent = failed = 0
        for _, target_id in targets:
            try:
                await context.bot.send_message(chat_id=target_id, text=f"📣 Scheduled Nexus Bot Broadcast\n🕒 {stamp}\n\n{message_text}")
                sent += 1
                await asyncio.sleep(0.04)
            except Exception:
                failed += 1
        try:
            await context.bot.send_message(OWNER_ID, f"Scheduled broadcast completed. Sent: {sent}; failed: {failed}.")
        except Exception:
            pass
    context.application.create_task(deliver())
    await safe_reply(update, f"⏰ Broadcast scheduled for {when.strftime('%Y-%m-%d %H:%M %Z')}\nNote: scheduled task runs only while this bot process stays online.")

async def maybe_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not msg.text or not chat or chat.type not in ("group", "supergroup") or not user or user.is_bot or msg.text.startswith("/"):
        return
    target = get_settings().get(f"translate:{chat.id}", "off")
    if target not in ("hi", "en"):
        return
    try:
        from deep_translator import GoogleTranslator
        from langdetect import detect
        source = detect(msg.text)
        if source == target or len(msg.text.strip()) < 3:
            return
        translated = await asyncio.to_thread(GoogleTranslator(source="auto", target=target).translate, msg.text[:4000])
        if translated and translated.strip().casefold() != msg.text.strip().casefold():
            label = "Hindi" if target == "hi" else "English"
            await msg.reply_text(f"🌐 {label} translation:\n{translated}")
    except Exception:
        # Keep ordinary group chat working if translation service is unavailable.
        return

ADULT_STICKER_TERMS = ("adult", "18plus", "18_plus", "nsfw", "xxx", "sex", "nude", "nudes", "porn", "hentai")
async def remove_adult_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not msg.sticker or not chat or chat.type not in ("group", "supergroup") or (user and user.is_bot):
        return False
    sticker = msg.sticker
    set_name = (sticker.set_name or "").casefold()
    flagged = any(term in set_name for term in ADULT_STICKER_TERMS)
    # This is metadata-based detection only; Telegram does not provide an adult-content flag.
    if flagged:
        try:
            member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if member.status == ChatMemberStatus.ADMINISTRATOR:
                await msg.delete()
                await context.bot.send_message(chat.id, "🔞 Adult-labelled sticker set detected; sticker removed.")
                add_log(0, "adult_sticker_removed", user.id if user else None, f"chat={chat.id}; set={set_name[:100]}")
                return True
        except Exception:
            pass
    return False

def media_signature(message):
    if not message:
        return None
    if message.sticker:
        return ("sticker", message.sticker.file_unique_id)
    if message.photo:
        return ("photo", message.photo[-1].file_unique_id)
    for attr, kind in (("video", "video"), ("animation", "animation"), ("document", "document"),
                       ("audio", "audio"), ("voice", "voice"), ("video_note", "video_note")):
        item = getattr(message, attr, None)
        if item:
            return (kind, item.file_unique_id)
    return None

async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Only the bot owner can add or change filters.")
        return
    msg = update.effective_message
    response = " ".join(context.args).strip()[:500]
    replied = msg.reply_to_message if msg else None

    # Type-wide media filters: /filter sticker response text
    media_types = {"sticker", "photo", "video", "animation", "document", "audio", "voice", "video_note"}
    if context.args and context.args[0].lower() in media_types and len(context.args) >= 2 and not (replied and (replied.text or replied.caption)):
        media_type = context.args[0].lower()
        response = " ".join(context.args[1:]).strip()[:500]
        key = add_media_filter(media_type, "*", response)
        add_log(update.effective_user.id, "media_type_filter_add", None, f"type={media_type}; key={key}")
        await safe_reply(update, f"✅ All {media_type} messages will trigger this reply: {response}")
        return

    signature = media_signature(replied)
    if signature:
        if not response:
            await safe_reply(update, "Usage: reply to a sticker/media message with /filter your response text")
            return
        media_type, unique_id = signature
        key = add_media_filter(media_type, unique_id, response)
        add_log(update.effective_user.id, "media_filter_add", None, f"type={media_type}; key={key}")
        await safe_reply(update, f"✅ Exact {media_type} filter saved. When the same media is sent in a group, I will reply: {response}")
        return

    if replied and (replied.text or replied.caption):
        trigger = (replied.text or replied.caption or "").strip()[:100].lower()
        if not response:
            await safe_reply(update, "Reply to a text message with /filter your response text")
            return
        add_filter(trigger, response)
        add_log(update.effective_user.id, "filter_add_from_reply", None, f"keyword={trigger[:80]}")
        await safe_reply(update, f"✅ Reply-based text filter saved for: {trigger}")
        return

    if len(context.args) < 2:
        await safe_reply(update, "Usage: /filter keyword response text; reply to text/media with /filter response; or /filter sticker|photo|video|audio|document|voice|animation|video_note response.")
        return
    keyword = context.args[0].lower()[:100]
    response = " ".join(context.args[1:])[:500]
    add_filter(keyword, response)
    add_log(update.effective_user.id, "filter_add", None, f"keyword={keyword}")
    await safe_reply(update, f"✅ Text filter added for: {keyword}")

async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    rows = get_filters()
    media_rows = get_media_filters()
    lines = [f"• Text: {r['keyword']} → {r['response'] or '[delete only]'}" for r in rows[:30]]
    lines += [f"• Media: {r['media_type']} → {r['response'] or '[no reply]'} (key {r['media_key'][:24]}…)" for r in media_rows[:30]]
    if not lines:
        await safe_reply(update, "No filters configured.")
    else:
        await safe_reply(update, "Saved filters:\n" + "\n".join(lines))

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show profile for yourself by default, or a replied-to / specified user."""
    await tracked(update)
    msg = update.effective_message
    target_user = None
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
        upsert_user(target_user.id, target_user.username, target_user.first_name)
    elif context.args:
        target_id = await resolve_target(update, context)
        if not target_id:
            await safe_reply(update, "❌ User nahi mila. Reply karke /info use karo, ya pehle se known @username / numeric ID do.")
            return
        row = get_user_by_id(target_id)
        if row:
            name = row.get("first_name") or "Name not available"
            username = row.get("username")
            user_id = row["user_id"]
        else:
            name, username, user_id = "Name not available", None, target_id
        target_user = None
    else:
        target_user = update.effective_user
        if target_user:
            upsert_user(target_user.id, target_user.username, target_user.first_name)
    if target_user:
        name = target_user.full_name or "Name not available"
        username = target_user.username
        user_id = target_user.id
    username_text = f"@{html.escape(username)}" if username else "Not set"
    name_text = html.escape(str(name))
    profile_url = f"tg://user?id={user_id}"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Open Profile", url=profile_url)]])
    text = (
        "╭━━━〔 🌌 <b>NEXUS</b> 〕━━━╮\n"
        "       👤 <b>USER PROFILE</b>\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        f"✨ <b>Name:</b> {name_text}\n"
        f"📛 <b>Username:</b> {username_text}\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        "📊 <b>Status:</b> Profile details\n\n"
        "👑 <b>Owner:</b> @Look_at_me60\n"
        "💎 <i>Powered by NEXUS</i>"
    )
    await safe_reply(update, text, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)

async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    if not req:
        return
    upsert_user(req.from_user.id, req.from_user.username, req.from_user.first_name)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"jr:approve:{req.chat.id}:{req.from_user.id}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"jr:decline:{req.chat.id}:{req.from_user.id}")
    ]])
    try:
        request_time = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z (local time)")
        username_text = "@" + req.from_user.username if req.from_user.username else "(no username)"
        await context.bot.send_message(
            OWNER_ID,
            f"🔔 JOIN REQUEST\nGroup: {req.chat.title or req.chat.id}\n"
            f"Full name: {req.from_user.full_name}\nUsername: {username_text}\n"
            f"User ID: {req.from_user.id}\nRequest received: {request_time}",
            reply_markup=keyboard
        )
    except Exception:
        pass

async def join_request_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if not query.from_user or query.from_user.id != OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return
    try:
        _, action, chat_id, user_id = query.data.split(":")
        chat_id, user_id = int(chat_id), int(user_id)
        if action == "approve":
            await context.bot.approve_chat_join_request(chat_id, user_id)
            add_log(OWNER_ID, "join_approved", user_id, f"chat={chat_id}")
            await query.edit_message_text(f"✅ Approved join request for user {user_id} in chat {chat_id}.")
        elif action == "decline":
            await context.bot.decline_chat_join_request(chat_id, user_id)
            add_log(OWNER_ID, "join_declined", user_id, f"chat={chat_id}")
            await query.edit_message_text(f"❌ Declined join request for user {user_id} in chat {chat_id}.")
        else:
            await query.answer("Unknown action.", show_alert=True)
            return
        await query.answer("Done")
    except Exception as e:
        await query.answer("Action failed. Check bot permissions and whether request is still pending.", show_alert=True)
        print(f"Join request action error: {type(e).__name__}")

async def points_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        await safe_reply(update, "Use /points inside a group."); return
    row = get_score(chat.id, user.id) or {"total_points": 0, "aura_points": 0, "aura_protect_until": 0}
    import datetime as _dt
    protection = "Active until " + _dt.datetime.fromtimestamp(row["aura_protect_until"], _dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if row["aura_protect_until"] and row["aura_protect_until"] > time.time() else "Not active"
    await safe_reply(update, f"🌹 NEXUS BOT PROFILE\n\n🪙 Coins: {row['total_points']}\n✨ Aura: {row['aura_points']}\n🛡️ Aura protection: {protection}\n\nUse /top and /auratop to see this group's leaderboard.")

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, aura=False):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use this command inside a group."); return
    rows = leaderboard(chat.id, "aura_points" if aura else "total_points", 10)
    title = "✨ AURA TOPLIST" if aura else "🪙 GROUP COIN TOPLIST"
    if not rows:
        await safe_reply(update, title + "\n\nNo scores yet — play a game or chat to start earning points!"); return
    lines = []
    for i, r in enumerate(rows, 1):
        name = ("@" + r["username"]) if r.get("username") else (r.get("first_name") or str(r["user_id"]))
        value = r["aura_points"] if aura else r["total_points"]
        lines.append(f"{i}. {name} — {value} {'Aura' if aura else 'coins'}")
    await safe_reply(update, title + "\n\n" + "\n".join(lines))

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await leaderboard_cmd(update, context, False)

async def auratop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await leaderboard_cmd(update, context, True)

async def giveaura_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        await safe_reply(update, "Use /giveaura in a group."); return
    target = await resolve_target(update, context)
    if not target or not context.args:
        await safe_reply(update, "Reply to a member with /giveaura amount, or use /giveaura @username amount."); return
    amount_token = context.args[-1]
    if not amount_token.isdigit() or not 1 <= int(amount_token) <= 1000000:
        await safe_reply(update, "Usage: /giveaura @username amount (1–1000000)"); return
    amount = int(amount_token)
    if target == user.id:
        await safe_reply(update, "You cannot give Aura to yourself."); return
    sender = get_score(chat.id, user.id) or {"aura_points": 0}
    if int(sender["aura_points"]) < amount:
        await safe_reply(update, f"Not enough Aura. You have {sender['aura_points']}."); return
    profile = get_user_by_id(target) or {"username": None, "first_name": str(target)}
    adjust_score(chat.id, user.id, user.username, user.first_name, aura_delta=-amount)
    received = adjust_score(chat.id, target, profile.get("username"), profile.get("first_name"), aura_delta=amount)
    display = "@" + profile["username"] if profile.get("username") else (profile.get("first_name") or str(target))
    await safe_reply(update, f"✨ {amount} Aura sent to {display}. Their total Aura: {received['aura_points']}.")

async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        await safe_reply(update, "Use /rob in a group."); return
    target = await resolve_target(update, context)
    if not target or target == user.id:
        await safe_reply(update, "Reply to a member with /rob [amount], or use /rob @username [amount]."); return
    profile = get_user_by_id(target) or {"username": None, "first_name": str(target)}
    target_score = get_score(chat.id, target) or {"aura_points": 0}
    available = int(target_score["aura_points"])
    if available <= 0:
        await safe_reply(update, "That member has no Aura to rob."); return
    amount = int(context.args[-1]) if context.args and context.args[-1].isdigit() else random.randint(1, min(100, available))
    amount = max(1, min(amount, 1000, available))
    display = "@" + profile["username"] if profile.get("username") else (profile.get("first_name") or str(target))
    if random.random() > 0.55:
        await safe_reply(update, "🚨 Rob failed! No Aura transferred."); return
    adjust_score(chat.id, target, profile.get("username"), profile.get("first_name"), aura_delta=-amount)
    result = adjust_score(chat.id, user.id, user.username, user.first_name, aura_delta=amount)
    await safe_reply(update, f"💰 Rob successful! {amount} Aura stolen from {display}. Your total Aura: {result['aura_points']}.")

async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /lock inside a group."); return
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only group admins can lock the group."); return
    kind = (context.args[0].lower() if context.args else "all")
    try:
        if kind in ("sticker", "stickers"):
            await context.bot.set_chat_permissions(chat.id, ChatPermissions(can_send_messages=True, can_send_other_messages=False, can_send_polls=True, can_add_web_page_previews=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True))
            set_setting(f"lock:{chat.id}", "stickers")
            await safe_reply(update, "🔒 Sticker/GIF lock enabled. Use /unlock stickers to restore sending permissions.")
        else:
            await context.bot.set_chat_permissions(chat.id, ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False, can_send_photos=False, can_send_videos=False, can_send_video_notes=False, can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False, can_add_web_page_previews=False))
            set_setting(f"lock:{chat.id}", "all")
            await safe_reply(update, "🔒 𝗡𝗘𝗫𝗨𝗦 𝗚𝗥𝗢𝗨𝗣 𝗟𝗢𝗖𝗞 enabled. Admins can use /unlock to reopen chat.")
    except Exception as e:
        await safe_reply(update, f"Could not lock. Make NEXUS an admin with Manage Chat permission. ({type(e).__name__})")

async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /unlock inside a group."); return
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only group admins can unlock the group."); return
    try:
        await context.bot.set_chat_permissions(chat.id, ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
        set_setting(f"lock:{chat.id}", "off")
        await safe_reply(update, "🔓 𝗡𝗘𝗫𝗨𝗦 𝗨𝗡𝗟𝗢𝗖𝗞 — chat permissions reopened.")
    except Exception as e:
        await safe_reply(update, f"Could not unlock. Check NEXUS admin permissions. ({type(e).__name__})")

async def lockinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat:
        return
    status = get_settings().get(f"lock:{chat.id}", "off")
    await safe_reply(update, f"🔐 NEXUS LOCK STATUS\nCurrent lock: {status}\nCommands: /lock, /lock stickers, /unlock, /lockinfo")

async def approval_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can approve/decline join requests."); return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use this command in the group where the join request is pending."); return
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Usage: /approve USER_ID or /decline USER_ID. Reply/username works only if the bot knows that user."); return
    command = (update.effective_message.text or "").split()[0].split("@")[0].lower()
    try:
        if command == "/approve":
            await context.bot.approve_chat_join_request(chat.id, target)
            await safe_reply(update, f"✅ Join request approved for user ID {target}.")
        else:
            await context.bot.decline_chat_join_request(chat.id, target)
            await safe_reply(update, f"❌ Join request declined for user ID {target}.")
    except Exception as e:
        await safe_reply(update, f"Could not process request. The user must have a pending join request and bot needs Manage Chat permissions. ({type(e).__name__})")

async def protect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        await safe_reply(update, "Use /protect in a group."); return
    arg = context.args[0].lower() if context.args else ""
    plans = {"1d": (1, 500), "2d": (2, 1000)}
    if arg not in plans:
        await safe_reply(update, "🛡️ Aura Protection\n/protect 1d — 500 coins\n/protect 2d — 1000 coins\nProtection prevents Aura losses for the selected duration."); return
    days, cost = plans[arg]
    ok, row = buy_aura_protection(chat.id, user.id, user.username, user.first_name, days, cost)
    if not ok:
        await safe_reply(update, f"Not enough total points. {arg} protection costs {cost}; you have {row['total_points']}."); return
    expiry = __import__("datetime").datetime.fromtimestamp(row["aura_protect_until"], __import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    await safe_reply(update, f"🛡️ Aura Shield activated for {days} day(s)!\n💸 Cost: {cost} total points\n🏆 Remaining total points: {row['total_points']}\n✨ Current Aura: {row['aura_points']}\n⏳ Expires: {expiry}")

async def aura_for_message(update: Update):
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not msg.text or not chat or chat.type not in ("group", "supergroup") or not user or user.is_bot or msg.text.startswith("/"):
        return
    words = re.findall(r"[a-zA-Z]+", msg.text.casefold())
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    if pos or neg:
        # Premium Aura economy: +100 for each positive word, -200 for each negative word.
        # Cap one message to prevent a single huge message from dominating the leaderboard.
        delta = max(-2000, min(1000, pos * 100 - neg * 200))
        before = get_score(chat.id, user.id) or {"aura_points": 0}
        row = adjust_score(chat.id, user.id, user.username, user.first_name, aura_delta=delta)
        actual_delta = int(row["aura_points"]) - int(before["aura_points"])
        if actual_delta:
            context_text = f"✨ +{actual_delta} Aura" if actual_delta > 0 else f"🌑 {actual_delta} Aura"
            await msg.reply_text(f"🌌 𝗡𝗘𝗫𝗨𝗦 𝗔𝗨𝗥𝗔\n{context_text}\n💠 Total Aura: {row['aura_points']}")
    else:
        # Ensure user appears on this group's points tables.
        adjust_score(chat.id, user.id, user.username, user.first_name)



async def imagine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate an image from a text prompt and send it back to the same Telegram chat."""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not msg or not chat or not user:
        return

    prompt = " ".join(context.args).strip()
    if not prompt and msg.reply_to_message and msg.reply_to_message.text:
        prompt = msg.reply_to_message.text.strip()
    if not prompt:
        await msg.reply_text(
            "🎨 <b>Nexus AI Image Generator</b>\n\n"
            "Use: <code>/imagine a futuristic city at night</code>\n"
            "Hindi prompt bhi use kar sakte ho: <code>/image blue fire wala anime boy</code>",
            parse_mode="HTML",
        )
        return
    if len(prompt) > 1000:
        await msg.reply_text("Prompt 1000 characters se chhota rakho.")
        return

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        await msg.reply_text(
            "⚠️ AI image generation abhi configure nahi hai. Owner ko hosting Secrets/.env mein OPENAI_API_KEY set karke bot restart karna hoga."
        )
        return

    cooldown = max(0, int(os.getenv("IMAGE_COOLDOWN_SECONDS", "30") or 30))
    daily_limit = max(1, int(os.getenv("IMAGE_DAILY_LIMIT", "10") or 10))
    now = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cooldowns = context.application.bot_data.setdefault("image_cooldowns", {})
    daily_counts = context.application.bot_data.setdefault("image_daily_counts", {})
    user_key = (chat.id, user.id)
    last_used = cooldowns.get(user_key, 0)
    if now - last_used < cooldown:
        wait = max(1, int(cooldown - (now - last_used)))
        await msg.reply_text(f"⏳ Image generator cooldown: {wait}s baad try karo.")
        return
    count_key = (today, user.id)
    if daily_counts.get(count_key, 0) >= daily_limit:
        await msg.reply_text(f"🧮 Aaj ka image limit ({daily_limit}) complete ho gaya. Kal phir try karna.")
        return

    # Reserve usage before making the paid API call to discourage repeated requests.
    cooldowns[user_key] = now
    daily_counts[count_key] = daily_counts.get(count_key, 0) + 1
    status = await msg.reply_text("🎨 <b>Nexus AI</b> tumhari image bana raha hai…", parse_mode="HTML")
    try:
        def generate_image():
            from openai import OpenAI
            client = OpenAI(api_key=api_key, timeout=180.0, max_retries=1)
            model = os.getenv("IMAGE_MODEL", "gpt-image-2.5-flare").strip() or "gpt-image-2.5-flare"
            return client.images.generate(
                model=model,
                prompt=prompt,
                size="1024x1024",
                quality=os.getenv("IMAGE_QUALITY", "medium").strip() or "medium",
                output_format="jpeg",
                n=1,
            )

        result = await asyncio.to_thread(generate_image)
        image_b64 = result.data[0].b64_json
        if not image_b64:
            raise RuntimeError("Image API returned no image data")
        import base64
        from io import BytesIO
        image_bytes = BytesIO(base64.b64decode(image_b64))
        image_bytes.name = "nexus_ai_image.jpg"
        caption = f"🎨 <b>Nexus AI Image</b>\n📝 {html.escape(prompt[:700])}\n👤 Requested by {html.escape(user.full_name[:100])}"
        await msg.reply_photo(photo=image_bytes, caption=caption, parse_mode="HTML")
        try:
            await status.delete()
        except Exception:
            pass
    except Exception as exc:
        # Refund daily usage on failure; do not expose API keys or raw provider error text.
        daily_counts[count_key] = max(0, daily_counts.get(count_key, 1) - 1)
        cooldowns.pop(user_key, None)
        print(f"Nexus image generation failed: {type(exc).__name__}")
        message = "❌ Image generate nahi hui. API key, billing, model access aur hosting logs check karo."
        if type(exc).__name__ in ("AuthenticationError", "PermissionDeniedError"):
            message = "❌ OpenAI API key invalid hai ya is model ka access nahi hai. API key/model permissions check karo."
        elif type(exc).__name__ in ("RateLimitError", "APITimeoutError", "APIConnectionError"):
            message = "❌ Image API busy ya temporarily unavailable hai. Thodi der baad dobara try karo."
        try:
            await status.edit_text(message)
        except Exception:
            await msg.reply_text(message)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat or chat.type not in ("group", "supergroup"):
        return
    remember_group(chat.id, chat.title or str(chat.id))
    if await check_antispam(update, context):
        return
    if await remove_adult_sticker(update, context):
        return
    await maybe_translate(update, context)
    await aura_for_message(update)

    # Only DM-started members may submit answers to an active group puzzle.
    if msg.text and chat.id in ACTIVE_PUZZLES and update.effective_user:
        if not has_dm_started(update.effective_user.id):
            prompted = context.bot_data.setdefault("dm_prompted", set())
            prompt_key = (chat.id, update.effective_user.id)
            if prompt_key not in prompted:
                prompted.add(prompt_key)
                bot_username = getattr(context.bot, "username", None)
                dm_url = f"https://t.me/{bot_username}?start=play" if bot_username else "https://t.me/"
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Start Nexus Bot in DM", url=dm_url)]])
                await msg.reply_text("To answer this game, first press Start in Nexus Bot's private chat.", reply_markup=keyboard)
            return
        puzzle = ACTIVE_PUZZLES[chat.id]
        if time.time() - puzzle.get("started", 0) > 600:
            ACTIVE_PUZZLES.pop(chat.id, None)
        elif puzzle.get("kind") == "guessnumber" and msg.text.strip().isdigit() and int(msg.text.strip()) != int(puzzle["answer"]):
            guess = int(msg.text.strip())
            await msg.reply_text("⬆️ Higher!" if guess < int(puzzle["answer"]) else "⬇️ Lower!")
            return
        elif msg.text.strip().casefold() == puzzle["answer"]:
            ACTIVE_PUZZLES.pop(chat.id, None)
            scorer = update.effective_user
            score_row = adjust_score(chat.id, scorer.id, scorer.username, scorer.first_name, total_delta=3000, aura_delta=50)
            await msg.reply_text(f"🎉 WINNER: {scorer.first_name or 'player'}!\n🪙 +3000 coins • ✨ +50 Aura\n🏆 Total coins: {score_row['total_points']} • ✨ Total Aura: {score_row['aura_points']}\nStart another with /puzzlehelp.")
            return

    if msg.text and chat.id in ACTIVE_PUZZLES and update.effective_user and not update.effective_user.is_bot:
        puzzle = ACTIVE_PUZZLES.get(chat.id)
        if puzzle and time.time() - puzzle.get("started", 0) <= 600 and msg.text.strip().casefold() != puzzle["answer"]:
            row = adjust_score(chat.id, update.effective_user.id, update.effective_user.username, update.effective_user.first_name, aura_delta=-60)
            await msg.reply_text(f"❌ Wrong answer, {update.effective_user.first_name or 'player'}! -60 Aura. Total Aura: {row['aura_points']}")
            return

    signature = media_signature(msg)
    if signature:
        row = get_media_filter(signature[0], signature[1])
        if row and row["response"]:
            try:
                await msg.reply_text(row["response"])
                add_log(0, "media_filter_match", update.effective_user.id if update.effective_user else None,
                        f"type={signature[0]}; chat={chat.id}")
            except Exception:
                pass
        return

    if not msg.text:
        return
    text = msg.text.lower()
    for row in get_filters():
        if row["keyword"] in text:
            try:
                await msg.delete()
                if row["response"]:
                    await context.bot.send_message(chat.id, row["response"])
                add_log(0, "filter_match", update.effective_user.id if update.effective_user else None,
                        f"keyword={row['keyword']}; chat={chat.id}")
            except Exception:
                pass
            break

# --- Fun group features: couples and mini puzzle games ---
PUZZLE_BANK = {
    "hidden": [
        ("R_SE", "rose"), ("L_VE", "love"), ("P_ZZLE", "puzzle"),
        ("T_LEGRAM", "telegram"), ("FR_END", "friend"), ("H_PPY", "happy"),
        ("S_NSHINE", "sunshine"), ("C_UPLE", "couple"),
        ("FRI_ND", "friend"), ("G_RDEN", "garden"), ("PL_NET", "planet"),
        ("R_CKET", "rocket"), ("BR_VE", "brave"), ("SM_LE", "smile"),
        ("FL_WER", "flower"), ("BR_DGE", "bridge"), ("C_STLE", "castle"),
        ("S_LVER", "silver"), ("OR_NGE", "orange"), ("DRE_M", "dream"),
    ],
    "scramble": [
        ("ESOR", "rose"), ("EVOL", "love"), ("ZZPUEL", "puzzle"),
        ("DNEIRF", "friend"), ("YPPHA", "happy"), ("EPOELP", "people"),
        ("TENALP", "planet"), ("NEDRAG", "garden"), ("TEKCOR", "rocket"),
        ("REWOLF", "flower"), ("EGDIRB", "bridge"), ("ELTSAC", "castle"),
        ("REVLIS", "silver"), ("EGNARO", "orange"), ("ERAMD", "dream"),
        ("EVARB", "brave"), ("ELIMS", "smile"), ("TRAEH", "heart"),
    ],
    "riddle": [
        ("I have keys but no locks, and space but no room. What am I?", "keyboard"),
        ("What has a face and two hands but no arms or legs?", "clock"),
        ("What gets wetter the more it dries?", "towel"),
        ("What has to be broken before you can use it?", "egg"),
        ("What has one eye but cannot see?", "needle"),
        ("What has many teeth but cannot bite?", "comb"),
        ("What goes up but never comes down?", "age"),
        ("What has a neck but no head?", "bottle"),
        ("What can travel around the world while staying in a corner?", "stamp"),
        ("What has hands but cannot clap?", "clock"),
        ("What has words but never speaks?", "book"),
        ("What has a ring but no finger?", "telephone"),
        ("What has legs but does not walk?", "table"),
        ("What can you catch but not throw?", "cold"),
        ("What has a bottom at the top?", "leg"),
    ],
    "emoji": [
        ("🌹 + ❤️", "love"), ("🐝 + 🍯", "honey"), ("🌞 + 🌻", "sunflower"),
        ("📚 + 🐛", "bookworm"), ("🌧️ + 🌈", "rainbow"), ("🍎 + 📱", "apple"),
        ("⭐ + 🐟", "starfish"), ("🌙 + 💡", "moonlight"), ("🔥 + 🐜", "fire ant"),
        ("🦋 + 🌼", "butterfly"), ("🌊 + 🐴", "seahorse"), ("☀️ + 👓", "sunglasses"),
        ("🐱 + 🐟", "catfish"), ("🍯 + 🌙", "honeymoon"), ("🌧️ + 🧥", "raincoat"),
        ("🧈 + 🪰", "butterfly"), ("🦷 + 🪥", "toothbrush"),
    ],
    "anagram": [("NIPAO", "piano"), ("RTAES", "tears"), ("HPEAL", "alpha"),
                 ("NOLME", "lemon"), ("RBAIN", "brain"), ("RSEOT", "store"),
                 ("TCAH", "chat"), ("NIGK", "king"), ("TENALP", "planet"),
                 ("NEDRAG", "garden"), ("TEKCOR", "rocket"), ("REWOLF", "flower"),
                 ("EGDIRB", "bridge"), ("ELTSAC", "castle"), ("REVLIS", "silver"),
                 ("EGNARO", "orange"), ("EVARB", "brave"), ("ELIMS", "smile"),
                 ("TRAEH", "heart"), ("MAERD", "dream"), ("DNUOS", "sound")],
    "trivia": [("Which planet is called the Red Planet?", "mars"),
               ("How many days are in a leap year?", "366"),
               ("What is the largest ocean on Earth?", "pacific"),
               ("Which animal is known as the king of the jungle?", "lion"),
               ("How many sides does a hexagon have?", "6"),
               ("Which planet is closest to the Sun?", "mercury"),
               ("What is the largest mammal?", "blue whale"),
               ("How many continents are there?", "7"),
               ("What gas do plants absorb?", "carbon dioxide"),
               ("What is the capital of Japan?", "tokyo"),
               ("How many minutes are in an hour?", "60"),
               ("Which ocean is the largest?", "pacific"),
               ("What is H2O commonly called?", "water"),
               ("Which bird is known for mimicking speech?", "parrot"),
               ("How many days are in a week?", "7"),
               ("What is the boiling point of water in Celsius?", "100")],
    "truefalse": [("A group of lions is called a pride. (true/false)", "true"),
                  ("The Sun is a planet. (true/false)", "false"),
                  ("Water freezes at 0°C at standard pressure. (true/false)", "true"),
                  ("Spiders have six legs. (true/false)", "false"),
                  ("The Earth orbits the Sun. (true/false)", "true"),
                  ("A triangle has four sides. (true/false)", "false"),
                  ("Humans normally have two lungs. (true/false)", "true"),
                  ("The Pacific is an ocean. (true/false)", "true"),
                  ("Bats are mammals. (true/false)", "true"),
                  ("Gold is a type of gas at room temperature. (true/false)", "false"),
                  ("A week has seven days. (true/false)", "true"),
                  ("The Moon makes its own visible light. (true/false)", "false"),
                  ("An octopus has eight arms. (true/false)", "true"),
                  ("Sound travels faster than light. (true/false)", "false"),
                  ("Plants can make food using sunlight. (true/false)", "true")],
}


def puzzle_help_text():
    return ("🧩 Nexus Bot Puzzle Games\n"
            "/hidden — guess the missing-letter word\n"
            "/scramble — unscramble the word\n"
            "/riddle — solve a riddle\n"
            "/emojiquiz — guess the emoji word\n"
            "/mathquiz — solve a quick math question\n"
            "/anagram — rearrange letters\n/wordle — guess the hidden word\n/hangman — guess a word\n/wordchain — continue the word chain\n"
            "/guessnumber — guess a number\n/fasttype — type the shown word\n/truefalse — quick true/false quiz\n/trivia — general knowledge\n"
            "/puzzlehelp — show these games\n"
            "First correct answer wins. Games run in groups.")

async def start_puzzle(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str):
    if not await dm_game_gate(update, context):
        return
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Please use puzzle games inside a group.")
        return
    if kind in ("hidden", "scramble", "emoji", "anagram", "trivia", "truefalse"):
        bank_key = {"scramble": "scramble", "emoji": "emoji", "anagram": "anagram", "trivia": "trivia", "truefalse": "truefalse"}.get(kind, "hidden")
        prompt, answer = random.choice(PUZZLE_BANK[bank_key])
    elif kind in ("wordle", "hangman", "wordchain", "fasttype"):
        word = random.choice(["planet", "garden", "friend", "silver", "orange", "puzzle", "rocket", "flower", "bridge", "castle"])
        if kind == "wordle":
            word = random.choice(["apple", "grape", "lemon", "plant", "smile", "heart", "dream", "brave"])
            prompt, answer = f"Guess the 5-letter word. Hint: it has {len(set(word))} unique letters. (This is a chat word-guess round; type the full word)", word
        elif kind == "hangman":
            prompt, answer = f"Hangman-style word: {' '.join('_' for _ in word)} ({len(word)} letters). Guess the whole word!", word
        elif kind == "wordchain":
            prompt, answer = "Word chain: name an English word that starts with the letter R.", "rose"
        else:
            prompt, answer = f"⚡ FAST TYPE: type this word exactly: {word}", word
    elif kind == "guessnumber":
        answer = str(random.randint(1, 50))
        prompt = "🔢 Guess a number from 1 to 50. First exact answer wins."
    elif kind == "math":
        a, b = random.randint(2, 30), random.randint(2, 20)
        operation = random.choice(("+", "-", "×"))
        if operation == "+": answer = str(a + b)
        elif operation == "-":
            if b > a: a, b = b, a
            answer = str(a - b)
        else: answer = str(a * b)
        prompt = f"{a} {operation} {b} = ?"
    else:
        prompt, answer = random.choice(PUZZLE_BANK["riddle"])
    ACTIVE_PUZZLES[chat.id] = {"answer": answer.casefold(), "kind": kind, "started": time.time()}
    labels = {"hidden": "🔤 Hidden Letter", "scramble": "🔀 Word Scramble", "riddle": "🧠 Riddle", "emoji": "🎭 Emoji Puzzle", "math": "➗ Math Challenge", "anagram": "🔠 Anagram", "wordle": "🟩 Word Guess", "hangman": "🪢 Hangman Word", "wordchain": "🔗 Word Chain", "guessnumber": "🔢 Guess Number", "fasttype": "⚡ Fast Type", "truefalse": "✅ True or False", "trivia": "🌍 Trivia Quiz"}
    await msg.reply_text(f"{labels[kind]}\n\n{prompt}\n\nReply in chat with your answer!")

async def hidden_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "hidden")

async def scramble_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "scramble")

async def riddle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "riddle")

async def emojiquiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "emoji")

async def mathquiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "math")

async def anagram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "anagram")

async def wordle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "wordle")

async def hangman_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "hangman")

async def wordchain_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "wordchain")

async def guessnumber_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "guessnumber")

async def fasttype_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "fasttype")

async def truefalse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "truefalse")

async def trivia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "trivia")

async def puzzlehelp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await dm_game_gate(update, context):
        return
    await safe_reply(update, puzzle_help_text())

async def set_couple_image_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Only the bot owner can change the couple image.")
        return
    msg = update.effective_message
    replied = msg.reply_to_message if msg else None
    if not replied or not replied.photo:
        await safe_reply(update, "Reply to a photo with /setcoupleimage to save it as the couple image.")
        return
    # Telegram file IDs are stable for reuse by this bot; store the largest photo size.
    set_setting("couple_image_file_id", replied.photo[-1].file_id)
    await safe_reply(update, "🌹 Couple image saved. Use /couple to test it.")

async def couple_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await dm_game_gate(update, context):
        return
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /couple in a group.")
        return
    await tracked(update)

    # Replying to a member intentionally creates a fresh pair with that member.
    replied_user = msg.reply_to_message.from_user if msg.reply_to_message else None
    force_new = bool(replied_user)
    settings = get_settings()
    key = f"couple_last:{chat.id}"
    now = time.time()
    try:
        last = float(settings.get(key, "0"))
    except (TypeError, ValueError):
        last = 0
    if not force_new and now - last < COUPLE_COOLDOWN_SECONDS:
        remaining = int(COUPLE_COOLDOWN_SECONDS - (now - last))
        hours, rem = divmod(remaining, 3600)
        minutes = rem // 60
        await msg.reply_text(f"💞 A new group couple is available every 6 hours. Try again in {hours}h {minutes}m, or reply to a member's message with /couple to make a fresh pair.")
        return

    # Prefer users seen in the group/chat where possible; Telegram does not expose a full member list.
    candidates = []
    if replied_user:
        upsert_user(replied_user.id, replied_user.username, replied_user.first_name)
        upsert_group_user(chat.id, replied_user.id, replied_user.username, replied_user.first_name)
        candidates.append({"user_id": replied_user.id, "first_name": replied_user.first_name or replied_user.username or str(replied_user.id)})
    for row in list_group_users(chat.id, 500):
        if int(row["user_id"]) not in {c["user_id"] for c in candidates}:
            candidates.append({"user_id": int(row["user_id"]), "first_name": row.get("first_name") or ("@" + row["username"] if row.get("username") else str(row["user_id"]))})
    candidates = [c for c in candidates if c["user_id"] != getattr(context.bot, "id", None)]
    if len(candidates) < 2:
        await msg.reply_text("💞 I need at least two known group members. Ask members to send a message, then try /couple again.")
        return
    if replied_user:
        possible = [c for c in candidates if c["user_id"] != replied_user.id]
        if not possible:
            await msg.reply_text("I need one more known member to make a couple.")
            return
        first = candidates[0]
        second = random.choice(possible)
    else:
        first, second = random.sample(candidates, 2)
    set_setting(key, str(now))
    def display_user(row):
        uid = int(row["user_id"])
        username = row.get("username")
        name = row.get("first_name") or (f"@{username}" if username else str(uid))
        handle = f"@{username}" if username else "No username"
        return f"{name} ({handle})\\n🆔 ID: {uid}"
    caption = ("💘 <b>NEXUS NEW COUPLE</b> 💘\\n\\n"
               f"🖤 <b>Member 1:</b> {html.escape(display_user(first))}\\n"
               f"💗 <b>Member 2:</b> {html.escape(display_user(second))}\\n\\n"
               f"✨ Compatibility: {random.randint(60, 100)}%")

    image_id = get_settings().get("couple_image_file_id", "").strip()
    try:
        if image_id:
            await context.bot.send_photo(chat_id=chat.id, photo=image_id, caption=caption)
        else:
            await msg.reply_text(caption + "\n\nOwner: reply to a photo with /setcoupleimage to add the couple image.")
    except Exception:
        await msg.reply_text(caption + "\n\n(Couple image could not be loaded.)")

async def automatic_couple_for_group(bot, chat_id):
    """Post and pin a couple in a group every six hours while the bot is online."""
    candidates = list_group_users(chat_id, 500)
    candidates = [r for r in candidates if int(r["user_id"]) != getattr(bot, "id", None)]
    if len(candidates) < 2:
        return False
    first, second = random.sample(candidates, 2)
    name1 = first.get("first_name") or ("@" + first["username"] if first.get("username") else str(first["user_id"]))
    name2 = second.get("first_name") or ("@" + second["username"] if second.get("username") else str(second["user_id"]))
    uname1 = f"@{first['username']}" if first.get("username") else "No username"
    uname2 = f"@{second['username']}" if second.get("username") else "No username"
    caption = ("💞 𝗡𝗘𝗫𝗨𝗦 𝗖𝗢𝗨𝗣𝗟𝗘 𝗧𝗜𝗠𝗘 💞\\n\\n"
               f"🖤 {html.escape(name1)} ({html.escape(uname1)}) — ID: {int(first['user_id'])}\\n"
               f"💗 {html.escape(name2)} ({html.escape(uname2)}) — ID: {int(second['user_id'])}\\n\\n"
               f"✨ Compatibility: {random.randint(60, 100)}%\\n🌌 New couple every 6 hours")
    settings = get_settings()
    image_id = settings.get("couple_image_file_id", "").strip()
    if image_id:
        sent = await bot.send_photo(chat_id=chat_id, photo=image_id, caption=caption)
    else:
        sent = await bot.send_message(chat_id=chat_id, text=caption)
    await bot.pin_chat_message(chat_id=chat_id, message_id=sent.message_id, disable_notification=True)
    return True

async def couple_scheduler(bot):
    """Persistent six-hour schedule; a group needs two members the bot has seen."""
    now = time.time()
    settings = get_settings()
    for raw_chat_id in get_known_groups():
        chat_id = int(raw_chat_id)
        key = f"auto_couple_next:{chat_id}"
        try:
            next_at = float(settings.get(key, "0"))
        except (TypeError, ValueError):
            next_at = 0
        if now < next_at:
            continue
        try:
            posted = await automatic_couple_for_group(bot, chat_id)
            # Retry in 15 minutes if not enough known users; otherwise wait six hours.
            set_setting(key, str(now + (COUPLE_COOLDOWN_SECONDS if posted else 900)))
        except Exception as e:
            print(f"Auto-couple failed in group {chat_id}: {type(e).__name__}")
            set_setting(key, str(now + 900))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # Do not log secrets or full update payloads.
    print(f"Bot handler error: {type(context.error).__name__}")

def build_bot():
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", command_start))
    bot_app.add_handler(CommandHandler("help", help_cmd))
    bot_app.add_handler(CommandHandler("ping", ping_cmd))
    bot_app.add_handler(CommandHandler("imagine", imagine_cmd))
    bot_app.add_handler(CommandHandler("image", imagine_cmd))
    bot_app.add_handler(CommandHandler("adminlist", adminlist_cmd))
    bot_app.add_handler(CommandHandler("report", report_cmd))
    bot_app.add_handler(CommandHandler("points", points_cmd))
    bot_app.add_handler(CommandHandler("top", top_cmd))
    bot_app.add_handler(CommandHandler("auratop", auratop_cmd))
    bot_app.add_handler(CommandHandler("protect", protect_cmd))
    bot_app.add_handler(CommandHandler("lock", lock_cmd))
    bot_app.add_handler(CommandHandler("unlock", unlock_cmd))
    bot_app.add_handler(CommandHandler("lockinfo", lockinfo_cmd))
    bot_app.add_handler(CommandHandler("giveaura", giveaura_cmd))
    bot_app.add_handler(CommandHandler("approve", approval_cmd))
    bot_app.add_handler(CommandHandler("decline", approval_cmd))
    bot_app.add_handler(CommandHandler("rob", rob_cmd))
    bot_app.add_handler(CommandHandler("id", id_cmd))
    bot_app.add_handler(CommandHandler("info", info_cmd))
    bot_app.add_handler(CommandHandler("history", history_cmd))
    bot_app.add_handler(CommandHandler("antispam", antispam_cmd))
    bot_app.add_handler(CommandHandler("free", free_cmd))
    bot_app.add_handler(CommandHandler("unfree", unfree_cmd))
    bot_app.add_handler(CommandHandler("translate", translate_cmd))
    bot_app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    bot_app.add_handler(CommandHandler("broadcastdm", broadcastdm_cmd))
    bot_app.add_handler(CommandHandler("broadcastgroups", broadcastgroups_cmd))
    bot_app.add_handler(CommandHandler("broadcast_at", broadcast_at_cmd))
    bot_app.add_handler(CommandHandler("ban", ban_cmd))
    bot_app.add_handler(CommandHandler("unban", unban_cmd))
    bot_app.add_handler(CommandHandler("mute", mute_cmd))
    bot_app.add_handler(CommandHandler("unmute", unmute_cmd))
    bot_app.add_handler(CommandHandler("filter", filter_cmd))
    bot_app.add_handler(CommandHandler("filters", filters_cmd))
    bot_app.add_handler(CommandHandler("couple", couple_cmd))
    bot_app.add_handler(CommandHandler("newcouple", couple_cmd))
    bot_app.add_handler(CommandHandler("setcoupleimage", set_couple_image_cmd))
    bot_app.add_handler(CommandHandler("hidden", hidden_cmd))
    bot_app.add_handler(CommandHandler("scramble", scramble_cmd))
    bot_app.add_handler(CommandHandler("anagram", anagram_cmd))
    bot_app.add_handler(CommandHandler("wordle", wordle_cmd))
    bot_app.add_handler(CommandHandler("hangman", hangman_cmd))
    bot_app.add_handler(CommandHandler("wordchain", wordchain_cmd))
    bot_app.add_handler(CommandHandler("guessnumber", guessnumber_cmd))
    bot_app.add_handler(CommandHandler("fasttype", fasttype_cmd))
    bot_app.add_handler(CommandHandler("truefalse", truefalse_cmd))
    bot_app.add_handler(CommandHandler("trivia", trivia_cmd))
    bot_app.add_handler(CommandHandler("riddle", riddle_cmd))
    bot_app.add_handler(CommandHandler("emojiquiz", emojiquiz_cmd))
    bot_app.add_handler(CommandHandler("mathquiz", mathquiz_cmd))
    bot_app.add_handler(CommandHandler("puzzlehelp", puzzlehelp_cmd))
    bot_app.add_handler(ChatJoinRequestHandler(join_request))
    bot_app.add_handler(CallbackQueryHandler(join_request_action, pattern=r"^jr:(approve|decline):-?\d+:\d+$"))
    bot_app.add_handler(CallbackQueryHandler(start_buttons_callback, pattern=r"^(start:(help|ping|games|home)|games:puzzles|help:(handbook|aura|tools|social|games|core|admin|misc|home))$"))
    bot_app.add_handler(MessageHandler((filters.ALL & ~filters.COMMAND), on_message))
    bot_app.add_error_handler(error_handler)
    return bot_app

async def run_bot():
    bot_app = build_bot()
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    try:
        # Run the persisted auto-couple scheduler; it checks groups every minute.
        while True:
            await couple_scheduler(bot_app.bot)
            await asyncio.sleep(60)
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

if __name__ == "__main__":
    async def main():
        task = asyncio.create_task(run_bot())
        from threading import Thread
        Thread(target=lambda: serve(app, host="0.0.0.0", port=PORT, threads=8), daemon=True).start()
        await task
    asyncio.run(main())
