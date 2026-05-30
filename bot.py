import os
import re
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# =========================
# CONFIG
# =========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

CORRECTIONS_FILE = "memory.json"

NOUN_SITES = [
    "https://nou.edu.ng/ecourseware-degs/",
    "https://nou.edu.ng/ecourseware-faculty-of-edu/",
    "https://nou.edu.ng/ecourseware-faculty-of-agric/",
    "https://nou.edu.ng/ecourseware-faculty-of-health-sc/",
    "https://nou.edu.ng/ecourseware/"
]

# =========================
# MEMORY SYSTEM
# =========================
def load_memory():
    if os.path.exists(CORRECTIONS_FILE):
        with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_memory(data):
    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# =========================
# LIVE SCRAPER (AUTONOMOUS LEARNING)
# =========================
def scrape_noun_courses():
    courses = {}

    for url in NOUN_SITES:
        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")

            links = soup.find_all("a")

            for link in links:
                text = link.text.strip()

                match = re.search(r"\b[A-Z]{2,4}\s?-?\d{3}\b", text.upper())

                if match:
                    code = match.group().replace(" ", "").upper()
                    title = text.replace(match.group(), "").strip(" -–:")

                    courses[code] = {
                        "title": title,
                        "source": url
                    }

        except:
            continue

    return courses


# =========================
# SMART NORMALIZER
# =========================
def normalize(code):
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def extract_code(text):
    match = re.search(r"\b[A-Z]{2,4}\s?-?\d{3}\b", text.upper())
    if match:
        return normalize(match.group())
    return None


# =========================
# AI ENGINE
# =========================
def ask_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
You are NOUN AUTONOMOUS AI SYSTEM.

You:
- use web knowledge + memory + reasoning
- never hallucinate exact course lists
- always explain clearly like a university system
"""
            },
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


# =========================
# AUTO LEARN ENGINE
# =========================
COURSE_DB = scrape_noun_courses()


# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Autonomous NOUN AI is ACTIVE")


async def teach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/teach", "").strip()

    if "=" in text:
        key, value = text.split("=", 1)
        key = normalize(key)
        mem = load_memory()
        mem[key] = value.strip()
        save_memory(mem)

        await update.message.reply_text(f"✅ Learned {key}")


# =========================
# MAIN ENGINE
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    memory = load_memory()
    code = extract_code(text)

    # =========================
    # 1. MEMORY CHECK
    # =========================
    if code:
        if code in memory:
            await update.message.reply_text(f"📘 {code}: {memory[code]}")
            return

        # =========================
        # 2. LIVE SCRAPED DB
        # =========================
        if code in COURSE_DB:
            course = COURSE_DB[code]
            await update.message.reply_text(
                f"📘 {code}\n🎓 {course['title']}\n\n🌐 Source: {course['source']}"
            )
            return

        # =========================
        # 3. AI FALLBACK (SAFE)
        # =========================
        reply = ask_ai(f"Explain NOUN course code {code}")
        await update.message.reply_text(reply)
        return

    # =========================
    # GENERAL AI MODE
    # =========================
    reply = ask_ai(text)
    await update.message.reply_text(reply)


# =========================
# START BOT
# =========================
if __name__ == "__main__":
    print("🚀 AUTONOMOUS NOUN AI RUNNING")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("teach", teach))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)