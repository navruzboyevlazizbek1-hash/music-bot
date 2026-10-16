import asyncio
import os
import re
import shutil
import traceback
import uuid

import yt_dlp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

try:
    from shazamio import Shazam
except ImportError:  # shazamio o'rnatilmagan bo'lsa ham bot ishlayveradi
    Shazam = None

# ============ SOZLAMA ============
BOT_TOKEN = "8939490453:AAH9gk9vwIwnk7YzBPQYk1Ycq-lRoPTM6vcmain.py"  # @BotFather dan olingan token
DOWNLOAD_DIR = "downloads"
MAX_TG_FILE = 49 * 1024 * 1024  # Telegram bot orqali yuboriladigan fayl chegarasi (~50 MB)
PAGE_SIZE = 6
# Trend musiqalar uchun so'rovlar; ro'yxat tugasa, boshidan aylanadi
TREND_QUERIES = ["top music hits", "trending songs", "popular songs", "new music hits"]
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

LANG_NAMES = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
EMOJIS = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]

# ============ MATNLAR ============
TEXTS = {
    "uz": {
        "welcome": "🎵 Musiqa botiga xush kelibsiz!",
        "choose_lang": "🌐 Tilni tanlang:",
        "lang_set": "✅ Til tanlandi!",
        "ask": "🎤 Qanday musiqa kerak? Nomini yozing yoki Instagram, TikTok, YouTube linkini yuboring.",
        "searching": "🔎 Qidirilmoqda...",
        "source_menu": "📥 Nima yuklab olamiz?",
        "audio_btn": "🎵 Audio",
        "video_btn": "🎬 Vedyo yuklab olish",
        "link_detected": "🔗 Audio yuklanmoqda va qo'shiq aniqlanmoqda...",
        "video_sending": "⏳ Vedyo yuklanmoqda...",
        "video_too_big": "⚠️ Vedyo 50 MB dan katta, Telegram orqali yuborib bo'lmaydi. Havola:",
        "not_found": "😔 Afsuski topilmadi. Aniqroq qilib yozing yoki video link tashlang.",
        "choose_track": "🎶 Qo'shiqni tanlang:",
        "trend_title": "🔥 Trenddagi musiqalar:",
        "trend_btn": "🔥 Trenddagi musiqalar",
        "downloading": "⏳ Yuklanmoqda...",
        "error": "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
        "fallback_link": "⚠️ Audio yuborib bo'lmadi. Qo'shiqni shu havola orqali tinglang:",
        "change_lang": "🌐 Til almashtirish",
    },
    "ru": {
        "welcome": "🎵 Добро пожаловать в музыкального бота!",
        "choose_lang": "🌐 Выберите язык:",
        "lang_set": "✅ Язык выбран!",
        "ask": "🎤 Какая музыка нужна? Напишите название или отправьте ссылку из Instagram, TikTok или YouTube.",
        "searching": "🔎 Ищу...",
        "source_menu": "📥 Что скачать?",
        "audio_btn": "🎵 Аудио",
        "video_btn": "🎬 Скачать видео",
        "link_detected": "🔗 Загружаю аудио и определяю песню...",
        "video_sending": "⏳ Видео загружается...",
        "video_too_big": "⚠️ Видео больше 50 МБ, Telegram не может его отправить. Ссылка:",
        "not_found": "😔 К сожалению, ничего не найдено. Напишите точнее или отправьте ссылку на видео.",
        "choose_track": "🎶 Выберите песню:",
        "trend_title": "🔥 Популярные песни:",
        "trend_btn": "🔥 Популярные песни",
        "downloading": "⏳ Загрузка...",
        "error": "❌ Произошла ошибка. Попробуйте ещё раз.",
        "fallback_link": "⚠️ Не удалось отправить аудио. Слушайте песню по ссылке:",
        "change_lang": "🌐 Сменить язык",
    },
    "en": {
        "welcome": "🎵 Welcome to the music bot!",
        "choose_lang": "🌐 Choose a language:",
        "lang_set": "✅ Language set!",
        "ask": "🎤 What music do you need? Type its name or send an Instagram, TikTok or YouTube link.",
        "searching": "🔎 Searching...",
        "source_menu": "📥 What do you want to download?",
        "audio_btn": "🎵 Audio",
        "video_btn": "🎬 Download video",
        "link_detected": "🔗 Downloading the audio and identifying the song...",
        "video_sending": "⏳ Downloading video...",
        "video_too_big": "⚠️ The video is over 50 MB, Telegram can't send it. Link:",
        "not_found": "😔 Sorry, nothing found. Try a more specific name or send a video link.",
        "choose_track": "🎶 Choose a song:",
        "trend_title": "🔥 Trending songs:",
        "trend_btn": "🔥 Trending songs",
        "downloading": "⏳ Downloading...",
        "error": "❌ Something went wrong. Please try again.",
        "fallback_link": "⚠️ Couldn't send the audio. Listen to the song via this link:",
        "change_lang": "🌐 Change language",
    },
}

USER_LANG = {}  # chat_id -> til kodi
USER_TREND = {} # chat_id -> oxirgi trend sahifasi
RESULTS = {}    # natijalar to'plami: key -> [(nom, url, rasm), ...]
SEARCHES = {}   # qidiruv to'plami: key -> {"query", "page", "used"}
LINKS = {}      # Instagram/TikTok/YouTube havolalari: key -> url


def t(chat_id, key):
    return TEXTS[USER_LANG.get(chat_id, "uz")][key]


def lang_keyboard():
    rows = [[InlineKeyboardButton(name, callback_data=f"lang:{code}")]
            for code, name in LANG_NAMES.items()]
    return InlineKeyboardMarkup(rows)


def trend_keyboard(chat_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(chat_id, "trend_btn"), callback_data="trend")]])


def results_markup(chat_id, key, results, refresh_label=None):
    # 1-qator: trend (va qidiruv bo'lsa 🔁); 2-qator: til; keyin variantlar
    row0 = [InlineKeyboardButton(t(chat_id, "trend_btn"), callback_data="trend")]
    if refresh_label is not None:
        row0.append(InlineKeyboardButton(refresh_label, callback_data=f"more:{key}"))
    rows = [row0, [InlineKeyboardButton(t(chat_id, "change_lang"), callback_data="change_lang")]]
    rows += [
        [InlineKeyboardButton(f"{EMOJIS[i]} {title[:50]}", callback_data=f"pick:{key}:{i}")]
        for i, (title, _, _) in enumerate(results)
    ]
    return InlineKeyboardMarkup(rows)


# ============ YUKLASH / QIDIRISH ============
def search_youtube(query, count=PAGE_SIZE):
    opts = {"quiet": True, "no_warnings": True,
            "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
    results = []
    for entry in info.get("entries") or []:
        if entry and entry.get("id"):
            url = f"https://www.youtube.com/watch?v={entry['id']}"
            thumb = f"https://i.ytimg.com/vi/{entry['id']}/hqdefault.jpg"
            results.append((entry.get("title") or "Nomsiz", url, thumb))
    return results[:count]


def fetch_page(query, page):
    # page-chi 6 talik blok; ro'yxat tugasa boshidan qaytadi (cheklov yo'q)
    results = search_youtube(query, count=PAGE_SIZE * (page + 1))
    block = results[PAGE_SIZE * page: PAGE_SIZE * page + PAGE_SIZE]
    if not block and page > 0:
        block = results[:PAGE_SIZE]
    return block


def download_audio(url, key):
    # FFmpeg bo'lsa mp3 ga o'giramiz, bo'lmasa m4a ni to'g'ridan-to'g'ri yuklaymiz
    has_ffmpeg = shutil.which("ffmpeg") is not None
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, key + ".%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if has_ffmpeg:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if has_ffmpeg:
            path = os.path.join(DOWNLOAD_DIR, key + ".mp3")
        else:
            path = ydl.prepare_filename(info)
    return path, info


def download_video(url, key):
    # ffmpeg shart emas: 720p gacha, bitta faylli mp4 (birlashtirish kerak bo'lmaydi)
    opts = {
        "format": "best[ext=mp4][height<=720]/best[height<=720]/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, key + ".%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
    return path, info


async def recognize_song(path):
    if Shazam is None:
        return None
    try:
        out = await Shazam().recognize(path)
        track = out.get("track")
        if track:
            return f"{track.get('subtitle', '')} {track.get('title', '')}".strip()
    except Exception:
        traceback.print_exc()
    return None


# ============ BUYRUQLAR ============
async def start(update, context):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Boshlash", callback_data="start")]])
    await update.message.reply_text(TEXTS["uz"]["welcome"], reply_markup=kb)


async def lang_command(update, context):
    chat_id = update.effective_chat.id
    await update.message.reply_text(t(chat_id, "choose_lang"), reply_markup=lang_keyboard())


# ============ TUGMALAR ============
async def on_button(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    chat_id = message.chat_id
    data = query.data

    if data in ("start", "change_lang"):
        await message.reply_text(t(chat_id, "choose_lang"), reply_markup=lang_keyboard())

    elif data.startswith("lang:"):
        USER_LANG[chat_id] = data.split(":", 1)[1]
        await message.reply_text(
            t(chat_id, "lang_set") + "\n\n" + t(chat_id, "ask"),
            reply_markup=trend_keyboard(chat_id),
        )

    elif data == "trend":
        await send_trend(message, chat_id)

    elif data.startswith("more:"):
        await refresh_search(message, chat_id, data.split(":", 1)[1])

    elif data.startswith("pick:"):
        _, key, idx = data.split(":")
        await send_track(message, chat_id, key, int(idx))

    elif data.startswith("src:"):
        _, mode, key = data.split(":")
        await handle_source(message, chat_id, mode, key)


# ============ MATN ============
async def on_text(update, context):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if re.search(r"https?://", text):
        await handle_link(update.message, chat_id, text)
    else:
        await handle_search(update.message, chat_id, text)


async def handle_search(message, chat_id, query):
    status = await message.reply_text(t(chat_id, "searching"))
    try:
        results = await asyncio.to_thread(fetch_page, query, 0)
    except Exception:
        traceback.print_exc()
        results = []
    await status.delete()
    await send_search(message, chat_id, query, results)


async def send_search(message, chat_id, query, results):
    if not results:
        await message.reply_text(t(chat_id, "not_found"))
        return
    await send_batch(message, chat_id, results, t(chat_id, "choose_track"), query=query, page=0)


async def send_batch(message, chat_id, results, caption, query=None, page=0):
    # Har bir natijalar to'plamining o'z kaliti bor: eski tugmalar doim ishlaydi
    key = uuid.uuid4().hex[:10]
    RESULTS[key] = results
    refresh_label = None
    if query is not None:
        SEARCHES[key] = {"query": query, "page": page, "used": False}
        refresh_label = f"🔁 {page}"  # necha marta yangilangani
    kb = results_markup(chat_id, key, results, refresh_label)
    try:
        await message.reply_photo(photo=results[0][2], caption=caption, reply_markup=kb)
    except Exception:
        traceback.print_exc()
        await message.reply_text(caption, reply_markup=kb)


async def refresh_search(message, chat_id, key):
    info = SEARCHES.get(key)
    if info is None or info["used"] or key not in RESULTS:
        return  # bu 🔁 allaqachon ishlatilgan
    info["used"] = True
    try:
        # shu xabardagi 🔁 tugmasini olib tashlaymiz: endi u ishlamaydi
        await message.edit_reply_markup(reply_markup=results_markup(chat_id, key, RESULTS[key]))
    except Exception:
        traceback.print_exc()
    status = await message.reply_text(t(chat_id, "searching"))
    page = info["page"] + 1
    try:
        results = await asyncio.to_thread(fetch_page, info["query"], page)
    except Exception:
        traceback.print_exc()
        results = []
    finally:
        await status.delete()
    if not results:
        await message.reply_text(t(chat_id, "not_found"))
        return
    await send_batch(message, chat_id, results, t(chat_id, "choose_track"),
                     query=info["query"], page=page)


async def send_trend(message, chat_id):
    n = USER_TREND.get(chat_id, -1) + 1  # har bosilganda keyingi trend to'plami
    USER_TREND[chat_id] = n
    query = TREND_QUERIES[n % len(TREND_QUERIES)]
    block = n // len(TREND_QUERIES)
    status = await message.reply_text(t(chat_id, "searching"))
    try:
        results = await asyncio.to_thread(fetch_page, query, block)
    except Exception:
        traceback.print_exc()
        results = []
    await status.delete()
    if not results:
        await message.reply_text(t(chat_id, "not_found"))
        return
    await send_batch(message, chat_id, results, t(chat_id, "trend_title"))


async def handle_link(message, chat_id, url):
    # Havola kelganda avval tanlov chiqadi: audio yoki vedyo
    key = uuid.uuid4().hex[:10]
    LINKS[key] = url
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(chat_id, "audio_btn"), callback_data=f"src:audio:{key}"),
        InlineKeyboardButton(t(chat_id, "video_btn"), callback_data=f"src:video:{key}"),
    ]])
    await message.reply_text(t(chat_id, "source_menu"), reply_markup=kb)


async def handle_source(message, chat_id, mode, key):
    url = LINKS.get(key)
    if url is None:
        await message.reply_text(t(chat_id, "error"))
        return
    if mode == "audio":
        await audio_from_link(message, chat_id, url)
    else:
        await video_from_link(message, chat_id, url)


async def audio_from_link(message, chat_id, url):
    status = await message.reply_text(t(chat_id, "link_detected"))
    path = None
    query = ""
    results = []
    try:
        path, info = await asyncio.to_thread(download_audio, url, uuid.uuid4().hex[:10])
        query = await recognize_song(path) or info.get("track") or info.get("title") or ""
        if query:
            results = await asyncio.to_thread(fetch_page, query, 0)
    except Exception:
        traceback.print_exc()
        await message.reply_text(t(chat_id, "error") + "\n" + url)
        return
    finally:
        if path and os.path.exists(path):
            os.remove(path)  # bu faqat aniqlash uchun kerak edi
        await status.delete()
    await send_search(message, chat_id, query, results)


async def video_from_link(message, chat_id, url):
    status = await message.reply_text(t(chat_id, "video_sending"))
    path = None
    try:
        path, _ = await asyncio.to_thread(download_video, url, uuid.uuid4().hex[:10])
        if os.path.getsize(path) > MAX_TG_FILE:
            await message.reply_text(t(chat_id, "video_too_big") + "\n" + url)
        else:
            with open(path, "rb") as f:
                await message.reply_video(video=f, supports_streaming=True)
    except Exception:
        traceback.print_exc()
        await message.reply_text(t(chat_id, "error") + "\n" + url)
    finally:
        if path and os.path.exists(path):
            os.remove(path)  # telefonda joy egallamasligi uchun
        await status.delete()


async def send_track(message, chat_id, key, idx):
    # Har bir variant tanlanganda o'sha qo'shiq alohida yuboriladi (eski to'plamlardan ham)
    if key not in RESULTS or idx >= len(RESULTS[key]):
        await message.reply_text(t(chat_id, "error"))
        return
    title, url, _ = RESULTS[key][idx]
    status = await message.reply_text(t(chat_id, "downloading"))
    path = None
    try:
        path, _ = await asyncio.to_thread(download_audio, url, uuid.uuid4().hex[:10])
        with open(path, "rb") as f:
            await message.reply_audio(audio=f, title=title[:60])
    except Exception:
        traceback.print_exc()
        # Audio yuborilmasa ham foydalanuvchi qo'shiqni havola orqali eshitsin
        await message.reply_text(t(chat_id, "fallback_link") + "\n" + url)
    finally:
        if path and os.path.exists(path):
            os.remove(path)  # yuborilgandan keyin telefondan o'chiriladi
        await status.delete()


# ============ ISHGA TUSHIRISH ============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("Musiqa boti ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
  
