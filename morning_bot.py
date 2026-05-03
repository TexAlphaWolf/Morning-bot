import asyncio
import re
import feedparser
import requests
from datetime import datetime
from difflib import SequenceMatcher
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os

# ============================================================
#  CONFIGURATION — set these as Environment Variables on Railway
#  (never hardcode secrets in code!)
# ============================================================
TELEGRAM_TOKEN      = os.environ["TELEGRAM_TOKEN"]       # from @BotFather
TELEGRAM_CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]     # from @userinfobot
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]  # openweathermap.org
CITY                = os.environ.get("CITY", "Rome")
TIMEZONE            = os.environ.get("TIMEZONE", "Europe/Rome")
SEND_HOUR           = int(os.environ.get("SEND_HOUR", "8"))
SEND_MINUTE         = int(os.environ.get("SEND_MINUTE", "0"))
NEWS_PER_FEED       = 3
MAX_TOTAL_NEWS      = 20
SIMILARITY_THRESHOLD = 0.72
# ============================================================

NEWS_FEEDS = [
    # ── Global / English ──────────────────────────────────────────────────────
    ("BBC World",                "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Reuters",                  "https://feeds.reuters.com/reuters/topNews"),
    ("AP News",                  "https://rsshub.app/apnews/topics/apf-topnews"),
    ("Al Jazeera",               "https://www.aljazeera.com/xml/rss/all.xml"),
    ("The Guardian",             "https://www.theguardian.com/world/rss"),
    ("CNN World",                "http://rss.cnn.com/rss/edition_world.rss"),
    ("NPR World",                "https://feeds.npr.org/1004/rss.xml"),
    ("DW English",               "https://rss.dw.com/rdf/rss-en-world"),
    ("France 24",                "https://www.france24.com/en/rss"),
    ("Euronews",                 "https://www.euronews.com/rss?level=theme&name=news"),
    ("Sky News",                 "https://feeds.skynews.com/feeds/rss/world.xml"),
    ("The Independent",          "https://www.independent.co.uk/news/world/rss"),
    # ── Business / Finance ────────────────────────────────────────────────────
    ("Bloomberg",                "https://feeds.bloomberg.com/markets/news.rss"),
    ("Financial Times",          "https://www.ft.com/?format=rss"),
    ("WSJ World",                "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ("CNBC",                     "https://www.cnbc.com/id/100727362/device/rss/rss.html"),
    # ── Technology ────────────────────────────────────────────────────────────
    ("TechCrunch",               "https://techcrunch.com/feed/"),
    ("The Verge",                "https://www.theverge.com/rss/index.xml"),
    ("Wired",                    "https://www.wired.com/feed/rss"),
    # ── Regional ──────────────────────────────────────────────────────────────
    ("NYT World",                "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("South China Morning Post", "https://www.scmp.com/rss/91/feed"),
    ("Times of India",           "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms"),
    ("Haaretz",                  "https://www.haaretz.com/srv/haaretz-en-rss.xml"),
    ("Arab News",                "https://www.arabnews.com/rss.xml"),
]

# ── Weather icons ─────────────────────────────────────────────────────────────

_ICONS = {
    "clear": "☀️", "cloud": "☁️", "rain": "🌧️", "drizzle": "🌦️",
    "thunder": "⛈️", "snow": "❄️", "mist": "🌫️", "fog": "🌫️",
    "haze": "🌫️", "smoke": "🌫️", "dust": "🌪️", "squall": "💨",
    "tornado": "🌪️",
}

def _wicon(desc: str) -> str:
    d = desc.lower()
    return next((v for k, v in _ICONS.items() if k in d), "🌡️")

# ── MarkdownV2 escaping ───────────────────────────────────────────────────────

_MD_CHARS = r"\_*[]()~`>#+-=|{}.!"

def _esc(text: str) -> str:
    for ch in _MD_CHARS:
        text = text.replace(ch, f"\\{ch}")
    return text

# ── 7-day forecast ────────────────────────────────────────────────────────────

def get_forecast() -> str:
    url = (
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?q={CITY}&appid={OPENWEATHER_API_KEY}&units=metric&lang=en&cnt=56"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        days: dict[str, list] = {}
        for item in data["list"]:
            day = datetime.fromtimestamp(item["dt"]).strftime("%A %d %b")
            days.setdefault(day, []).append(item)

        lines = [f"🗓️ *7\\-Day Forecast — {_esc(CITY)}*"]
        for day in list(days.keys())[:7]:
            slots    = days[day]
            temps    = [s["main"]["temp"] for s in slots]
            descs    = [s["weather"][0]["description"] for s in slots]
            dominant = max(set(descs), key=descs.count)
            icon     = _wicon(dominant)
            t_min    = round(min(temps))
            t_max    = round(max(temps))
            pop      = round(max(s.get("pop", 0) for s in slots) * 100)
            rain     = f" 🌂{pop}%" if pop >= 20 else ""
            lines.append(
                f"  {icon} *{_esc(day)}*: {t_min}°C – {t_max}°C, "
                f"{_esc(dominant.capitalize())}{rain}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Could not fetch forecast: {_esc(str(e))}"

# ── News fetching & deduplication ─────────────────────────────────────────────

def _normalise(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()

def _similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= SIMILARITY_THRESHOLD

def get_news() -> tuple[str, int, int]:
    raw: list[dict] = []
    for source, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:NEWS_PER_FEED]:
                title = e.get("title", "").strip()
                link  = e.get("link",  "").strip()
                if title and link:
                    raw.append({"source": source, "title": title, "link": link})
        except Exception:
            pass

    unique: list[dict] = []
    seen:   list[str]  = []
    for item in raw:
        norm = _normalise(item["title"])
        if not any(_similar(norm, s) for s in seen):
            unique.append(item)
            seen.append(norm)
        if len(unique) >= MAX_TOTAL_NEWS:
            break

    if not unique:
        return "⚠️ No news available\\.", 0, 0

    lines = []
    for item in unique:
        lines.append(f"• [{_esc(item['title'])}]({item['link']})  _— {_esc(item['source'])}_")

    return "\n".join(lines), len(raw), len(unique)

# ── Message splitting (Telegram 4096-char limit) ──────────────────────────────

def _split(text: str, limit: int = 4096) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            parts.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        parts.append(cur)
    return parts

# ── Send message ──────────────────────────────────────────────────────────────

async def send_morning_message(bot: Bot) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending morning message...")
    today              = _esc(datetime.now().strftime("%A, %B %d %Y"))
    forecast           = get_forecast()
    news_str, fetched, unique = get_news()
    divider            = _esc("─" * 32)

    message = (
        f"🌅 *Good Morning\\! — {today}*\n"
        f"{divider}\n\n"
        f"{forecast}\n\n"
        f"{divider}\n"
        f"📰 *Today's Top News*\n"
        f"_\\({unique} unique stories from {fetched} fetched across {len(NEWS_FEEDS)} sources\\)_\n\n"
        f"{news_str}\n\n"
        f"{divider}\n"
        f"_Have a great day\\! 🚀_"
    )

    chunks = _split(message)
    for chunk in chunks:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=chunk,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )
        await asyncio.sleep(0.5)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Done — {len(chunks)} part(s), "
          f"{unique} unique news / {fetched} fetched.")

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        send_morning_message,
        trigger="cron",
        hour=SEND_HOUR,
        minute=SEND_MINUTE,
        args=[bot],
    )
    scheduler.start()
    print(f"✅ Bot running on Railway — daily message at {SEND_HOUR:02d}:{SEND_MINUTE:02d} ({TIMEZONE})")

    # Keep alive forever
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
