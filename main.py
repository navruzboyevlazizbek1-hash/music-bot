"""Telegram musiqa boti: qidiruv, trend, Instagram/TikTok/YouTube havolalari."""
import asyncio, glob, html, itertools, logging, os, shutil

from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, Defaults, MessageHandler, filters
import yt_dlp

try:
    from shazamio import Shazam
except Exception:
    Shazam = None

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("musicbot")

BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8939490453:AAH9gk9vwIwnk7YzBPQYk1Ycq-lRoPTM6vc"
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
MAX_FILE = 49 * 1024 * 1024
PAGE = 6
FFMPEG = shutil.which("ffmpeg") is not None
COUNTER = itertools.count(1)
EMOJIS = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
LANGS = {"uz": "O'zbekcha", "ru": "Русский", "en": "English"}
TREND = [
    "top music hits", "trending songs", "popular songs", "new music hits", "viral songs",
    "top 50 global songs", "best pop songs", "hit songs this week", "new music releases",
    "top charts songs", "best hip hop songs", "best rock songs",
]
HOSTS = ("instagram.com", "tiktok.com", "youtube.com", "youtu.be")
USER_LANG, USER_TREND, LINKS, FILE_IDS, ACTIVE = {}, {}, {}, {}, {}

TEXTS = {
    "uz": {
        "welcome": "🎵 <b>Musiqa botiga xush kelibsiz!</b>\n\n📸 Instagram • 🎵 TikTok • ▶️ YouTube\n\nQo'shiq nomini yozing yoki havola tashlang.",
        "start": "▶️ Boshlash",
        "lang": "🌐 <b>Tilni tanlang:</b>",
        "lang_set": "✅ Til: O'zbekcha",
        "ask": "🎧 Qaysi qo'shiqni topmoqchisiz? Nomini yozing yoki havola tashlang.",
        "trend_btn": "🔥 Trenddagi musiqalar",
        "change": "🌐 Til almashtirish",
        "searching": "🔎 Qidirilmoqda...",
        "results": "🎵 <b>«{}»</b> bo'yicha natijalar\n👇 Variantni tanlang:",
        "trend_results": "🔥 <b>Trenddagi musiqalar</b>\n👇 Variantni tanlang:",
        "not_found": "😔 Topilmadi. Aniqroq yozing yoki havola tashlang.",
        "link": "🔗 <b>{}</b>\n\nNima qilay?",
        "link_plain": "🔗 Havola qabul qilindi.\n\nNima qilay?",
        "video_btn": "🎬 Vedyo yuklab olish",
        "audio_btn": "🎵 Musiqani topish",
        "recognizing": "🎧 Musiqa aniqlanmoqda...",
        "recognized": "✅ Topildi: <b>{}</b>\n👇 Variantni tanlang:",
        "from_title": "🔎 Aniq aniqlanmadi, video nomi bo'yicha qidirildi.\n👇 Variantni tanlang:",
        "loading": "⏳ Yuklanmoqda...",
        "too_big": "⚠️ Fayl 50 MB dan katta.\nHavola: {}",
        "fallback": "⚠️ Hozir yuklab bo'lmadi.\nHavola: {}",
        "expired": "⚠️ Tugma eskirgan. Qayta qidiring.",
        "error": "⚠️ Xatolik bo'ldi, qayta urinib ko'ring.",
    },
    "ru": {
        "welcome": "🎵 <b>Добро пожаловать в музыкального бота!</b>\n\n📸 Instagram • 🎵 TikTok • ▶️ YouTube\n\nНапишите название песни или отправьте ссылку.",
        "start": "▶️ Начать",
        "lang": "🌐 <b>Выберите язык:</b>",
        "lang_set": "✅ Язык: Русский",
        "ask": "🎧 Какую песню ищете? Напишите название или отправьте ссылку.",
        "trend_btn": "🔥 Трендовые треки",
        "change": "🌐 Сменить язык",
        "searching": "🔎 Ищу...",
        "results": "🎵 Результаты по запросу <b>«{}»</b>\n👇 Выберите вариант:",
        "trend_results": "🔥 <b>Трендовые треки</b>\n👇 Выберите вариант:",
        "not_found": "😔 Ничего не найдено. Напишите точнее или отправьте ссылку.",
        "link": "🔗 <b>{}</b>\n\nЧто сделать?",
        "link_plain": "🔗 Ссылка получена.\n\nЧто сделать?",
        "video_btn": "🎬 Скачать видео",
        "audio_btn": "🎵 Найти музыку",
        "recognizing": "🎧 Определяю музыку...",
        "recognized": "✅ Найдено: <b>{}</b>\n👇 Выберите вариант:",
        "from_title": "🔎 Точно не определилось, искал по названию видео.\n👇 Выберите вариант:",
        "loading": "⏳ Загружаю...",
        "too_big": "⚠️ Файл больше 50 МБ.\nСсылка: {}",
        "fallback": "⚠️ Сейчас не удалось загрузить.\nСсылка: {}",
        "expired": "⚠️ Кнопка устарела. Ищите заново.",
        "error": "⚠️ Произошла ошибка, попробуйте еще раз.",
    },
    "en": {
        "welcome": "🎵 <b>Welcome to the music bot!</b>\n\n📸 Instagram • 🎵 TikTok • ▶️ YouTube\n\nType a song name or send a link.",
        "start": "▶️ Start",
        "lang": "🌐 <b>Choose a language:</b>",
        "lang_set": "✅ Language: English",
        "ask": "🎧 Which song are you looking for? Type a name or send a link.",
        "trend_btn": "🔥 Trending songs",
        "change": "🌐 Change language",
        "searching": "🔎 Searching...",
        "results": "🎵 Results for <b>«{}»</b>\n👇 Choose a variant:",
        "trend_results": "🔥 <b>Trending songs</b>\n👇 Choose a variant:",
        "not_found": "😔 Nothing found. Try a more specific name or send a link.",
        "link": "🔗 <b>{}</b>\n\nWhat should I do?",
        "link_plain": "🔗 Link received.\n\nWhat should I do?",
        "video_btn": "🎬 Download video",
        "audio_btn": "🎵 Find the music",
        "recognizing": "🎧 Recognizing the music...",
        "recognized": "✅ Found: <b>{}</b>\n👇 Choose a variant:",
        "from_title": "🔎 Could not recognize it exactly, searched by video title.\n👇 Choose a variant:",
        "loading": "⏳ Downloading...",
        "too_big": "⚠️ The file is larger than 50 MB.\nLink: {}",
        "fallback": "⚠️ Could not download right now.\nLink: {}",
        "expired": "⚠️ Button is outdated. Search again.",
        "error": "⚠️ Something went wrong, please try again.",
    },
}


def t(cid, key, *args):
    s = TEXTS[USER_LANG.get(cid, "uz")].get(key, TEXTS["uz"][key])
    return s.format(*[html.escape(str(a)) for a in args]) if args else s


# ---------- klaviaturalar ----------

def lang_kb():
    return M([[B(name, callback_data=f"lang:{code}")] for code, name in LANGS.items()])


def base_rows(cid):
    return [
        [B(t(cid, "trend_btn"), callback_data="trend")],
        [B(t(cid, "change"), callback_data="change")],
    ]


def results_kb(cid, items):
    rows = base_rows(cid)
    for i, it in enumerate(items):
        name = it["title"][:47] + "…" if len(it["title"]) > 48 else it["title"]
        rows.append([B(f"{EMOJIS[i % len(EMOJIS)]} {name}{it['dur']}", callback_data=f"p:{it['vid']}")])
    return M(rows)


def link_kb(cid, lid):
    rows = [
        [B(t(cid, "video_btn"), callback_data=f"src:v:{lid}")],
        [B(t(cid, "audio_btn"), callback_data=f"src:a:{lid}")],
    ]
    return M(rows + base_rows(cid))


# ---------- qidiruv ----------

def fmt_dur(sec):
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return ""
    return f" · {sec // 60}:{sec % 60:02d}" if sec > 0 else ""


def search(query, count):
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{count}:{query}", download=False) or {}
    out = []
    for e in info.get("entries") or []:
        if e and e.get("id"):
            vid = e["id"]
            out.append({
                "vid": vid,
                "title": e.get("title") or vid,
                "dur": fmt_dur(e.get("duration")),
                "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            })
    return out


def fetch(query, page):
    return search(query, (page + 1) * PAGE)[page * PAGE:(page + 1) * PAGE]


# ---------- yuklash ----------

def find_file(name):
    files = [f for f in glob.glob(os.path.join(DIR, name + ".*")) if not f.endswith((".part", ".ytdl"))]
    if not files:
        raise RuntimeError("fayl topilmadi")
    return max(files, key=os.path.getmtime)


def download(url, name, video=False):
    os.makedirs(DIR, exist_ok=True)
    opts = {"outtmpl": os.path.join(DIR, name + ".%(ext)s"), "noplaylist": True, "quiet": True, "no_warnings": True}
    if video:
        opts["format"] = "best[ext=mp4][height<=720]/best[height<=720]/best"
    else:
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        if FFMPEG:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True) or {}
    return find_file(name), info.get("title") or ""


def get_info(url):
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False) or {}
    return info.get("title") or "", info.get("thumbnail") or ""


def cleanup(name):
    for f in glob.glob(os.path.join(DIR, name + ".*")):
        try:
            os.remove(f)
        except OSError:
            pass


async def recognize(path):
    if Shazam is None:
        return None
    try:
        sh = Shazam()
        func = getattr(sh, "recognize", None) or sh.recognize_song
        tr = ((await func(path)) or {}).get("track") or {}
        return f"{tr.get('subtitle', '')} {tr.get('title', '')}".strip() or None
    except Exception:
        log.exception("Shazam xatosi")
        return None


# ---------- yuborish ----------

async def quiet_delete(m):
    try:
        await m.delete()
    except Exception:
        pass


async def clear_active(cid):
    old = ACTIVE.pop(cid, None)
    if old is not None:
        try:
            await old.edit_reply_markup(reply_markup=None)
        except Exception:
            pass


async def send_results(msg, cid, items, header):
    await clear_active(cid)
    kb = results_kb(cid, items)
    sent = None
    if items:
        try:
            sent = await msg.reply_photo(photo=items[0]["thumb"], caption=header, reply_markup=kb)
        except Exception:
            log.exception("Rasm yuborilmadi")
    if sent is None:
        sent = await msg.reply_text(header, reply_markup=kb)
    ACTIVE[cid] = sent


async def search_and_send(msg, cid, query):
    status = await msg.reply_text(t(cid, "searching"))
    try:
        items = await asyncio.to_thread(fetch, query, 0)
    except Exception:
        log.exception("Qidiruv xatosi")
        items = []
    await quiet_delete(status)
    if not items:
        return await msg.reply_text(t(cid, "not_found"), reply_markup=M(base_rows(cid)))
    await send_results(msg, cid, items, t(cid, "results", query))


async def send_trend(msg, cid):
    await clear_active(cid)
    n = USER_TREND.get(cid, 0)
    USER_TREND[cid] = n + 1
    q = TREND[n % len(TREND)]
    page = (n // len(TREND)) % 4
    items = []
    try:
        items = await asyncio.to_thread(fetch, q, page)
        if not items and page:
            items = await asyncio.to_thread(fetch, q, 0)
    except Exception:
        log.exception("Trend xatosi")
    if not items:
        return await msg.reply_text(t(cid, "not_found"), reply_markup=M(base_rows(cid)))
    await send_results(msg, cid, items, t(cid, "trend_results"))


async def send_link_menu(msg, cid, link):
    await clear_active(cid)
    lid = next(COUNTER)
    LINKS[lid] = link
    title, thumb = "", ""
    try:
        title, thumb = await asyncio.to_thread(get_info, link)
    except Exception:
        log.exception("Havola ma'lumoti olinmadi")
    text = t(cid, "link", title[:200]) if title else t(cid, "link_plain")
    kb = link_kb(cid, lid)
    sent = None
    if thumb:
        try:
            sent = await msg.reply_photo(photo=thumb, caption=text, reply_markup=kb)
        except Exception:
            log.exception("Havola rasmi yuborilmadi")
    if sent is None:
        sent = await msg.reply_text(text, reply_markup=kb)
    ACTIVE[cid] = sent


async def send_track(msg, cid, vid):
    fid = FILE_IDS.get(vid)
    if fid:
        try:
            await msg.reply_audio(audio=fid)
            return
        except Exception:
            FILE_IDS.pop(vid, None)
    url = f"https://www.youtube.com/watch?v={vid}"
    status = await msg.reply_text(t(cid, "loading"))
    name = f"a{next(COUNTER)}"
    try:
        path, title = await asyncio.to_thread(download, url, name)
        if os.path.getsize(path) > MAX_FILE:
            return await msg.reply_text(t(cid, "too_big", url))
        with open(path, "rb") as f:
            sent = await msg.reply_audio(audio=f, title=title[:64] or None)
        if sent and sent.audio:
            FILE_IDS[vid] = sent.audio.file_id
    except Exception:
        log.exception("Audio xatosi")
        await msg.reply_text(t(cid, "fallback", url))
    finally:
        cleanup(name)
        await quiet_delete(status)


async def send_video(msg, cid, url):
    status = await msg.reply_text(t(cid, "loading"))
    name = f"v{next(COUNTER)}"
    try:
        path, _ = await asyncio.to_thread(download, url, name, True)
        if os.path.getsize(path) > MAX_FILE:
            return await msg.reply_text(t(cid, "too_big", url))
        with open(path, "rb") as f:
            await msg.reply_video(video=f, supports_streaming=True)
    except Exception:
        log.exception("Video xatosi")
        await msg.reply_text(t(cid, "fallback", url))
    finally:
        cleanup(name)
        await quiet_delete(status)


async def audio_from_link(msg, cid, url):
    status = await msg.reply_text(t(cid, "recognizing"))
    name = f"l{next(COUNTER)}"
    query, found = "", None
    try:
        path, title = await asyncio.to_thread(download, url, name)
        found = await recognize(path)
        query = found or title
    except Exception:
        log.exception("Havoladan audio olinmadi")
        try:
            query = (await asyncio.to_thread(get_info, url))[0]
        except Exception:
            query = ""
    finally:
        cleanup(name)
    items = []
    if query:
        try:
            items = await asyncio.to_thread(fetch, query, 0)
        except Exception:
            log.exception("Qidiruv xatosi")
    await quiet_delete(status)
    if not items:
        return await msg.reply_text(t(cid, "fallback", url))
    text = t(cid, "recognized", found) if found else t(cid, "from_title")
    await send_results(msg, cid, items, text)


async def handle_source(msg, cid, kind, lid):
    url = LINKS.get(lid)
    if not url:
        return await msg.reply_text(t(cid, "expired"), reply_markup=M(base_rows(cid)))
    if kind == "v":
        await send_video(msg, cid, url)
    else:
        await audio_from_link(msg, cid, url)


# ---------- handlerlar ----------

def extract_link(text):
    for tok in text.split():
        if any(h in tok.lower() for h in HOSTS):
            return tok if "://" in tok else "https://" + tok
    return None


async def start(update, context):
    cid = update.effective_chat.id
    kb = M([[B(t(cid, "start"), callback_data="start")]])
    await update.message.reply_text(t(cid, "welcome"), reply_markup=kb)


async def on_text(update, context):
    msg, cid = update.message, update.effective_chat.id
    text = (msg.text or "").strip()
    if not text:
        return
    await clear_active(cid)
    link = extract_link(text)
    if link:
        await send_link_menu(msg, cid, link)
    else:
        await search_and_send(msg, cid, text)


async def on_button(update, context):
    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass
    msg = q.message
    cid = msg.chat_id
    data = q.data or ""
    if data in ("start", "change"):
        await msg.reply_text(t(cid, "lang"), reply_markup=lang_kb())
    elif data.startswith("lang:"):
        USER_LANG[cid] = data.split(":", 1)[1]
        await msg.reply_text(t(cid, "lang_set") + "\n\n" + t(cid, "ask"), reply_markup=M(base_rows(cid)))
    elif data == "trend":
        await send_trend(msg, cid)
    elif data.startswith("p:"):
        await send_track(msg, cid, data[2:])
    elif data.startswith("src:"):
        _, kind, lid = data.split(":", 2)
        await clear_active(cid)
        await handle_source(msg, cid, kind, int(lid))


async def on_error(update, context):
    log.error("Xatolik: %s", context.error, exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, t(update.effective_chat.id, "error"))
        except Exception:
            pass


def main():
    os.makedirs(DIR, exist_ok=True)
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .defaults(Defaults(parse_mode=ParseMode.HTML))
        .concurrent_updates(True)
        .connect_timeout(30)
        .read_timeout(60)
        .write_timeout(120)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    log.info("Bot ishga tushdi")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
