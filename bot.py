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

MEMORY_FILE = "memory.json"

# =========================
# NOUN SOURCES
# =========================
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
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# =========================
# NORMALIZER
# =========================
def normalize(code):
    return re.sub(r"[^A-Z0-9]", "", code.upper())

def extract_code(text):
    match = re.search(r"\b[A-Z]{2,4}\s?-?\d{3}\b", text.upper())
    if match:
        return normalize(match.group())
    return None

# =========================
# SCRAPER (SAFE VERSION)
# =========================
def scrape_noun_courses():
    courses = {}

    for url in NOUN_SITES:
        try:
            r = requests.get(url, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            text = soup.get_text(" ")

            matches = re.findall(r"\b[A-Z]{2,4}\s?-?\d{3}\b", text.upper())

            for match in matches:
                code = normalize(match)

                # try find surrounding text as title (basic fallback)
                title_guess = "NOUN Course"

                courses[code] = {
                    "title": title_guess,
                    "source": url
                }

        except:
            continue

    return courses
# =========================
# BUILD COURSE DB ON START
# =========================
COURSE_DB = scrape_noun_courses()

# =========================
# AI ENGINE (SAFE)
# =========================
def ask_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
You are NOUN AI Assistant.

Rules:
- NEVER invent course titles
- If unsure, say you are unsure
- Only explain general academic meaning
"""
            },
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 NOUN AI is ACTIVE (Hybrid Engine)")

async def teach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/teach", "").strip()

    if "=" in text:
        key, value = text.split("=", 1)
        key = normalize(key)

        memory = load_memory()
        memory[key] = value.strip()
        save_memory(memory)

        await update.message.reply_text(f"✅ Learned: {key}")

# =========================
# MAIN ENGINE
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper().strip()

    memory = load_memory()
    code = extract_code(text)

    if code:

        # 1. MEMORY
        if code in memory:
            await update.message.reply_text(f"📘 {code}: {memory[code]}")
            return

        # 2. COURSE DB (STRICT)
        course = COURSE_DB.get(code)

        if course:
            await update.message.reply_text(
                f"""📘 {code}
🎓 {course['title']}
🌐 {course['source']}"""
            )
        else:
            await update.message.reply_text(
                f"❌ {code} not found in NOUN database."
            )

        return

    # NON-CODE → NO AI GUESSING
    await update.message.reply_text("Please send a valid course code like GST101")

    # =========================
    # 1. MEMORY FIRST
    # =========================
    if code:
        if code in memory:
            await update.message.reply_text(f"📘 {code}: {memory[code]}")
            return

        # =========================
        # 2. COURSE DB SECOND
        # =========================
        if code in COURSE_DB:
            course = COURSE_DB[code]

            await update.message.reply_text(
                f"""📘 {code}
🎓 {course['title']}

🌐 Source: {course['source']}"""
            )
            return

        # =========================
        # 3. AI LAST RESORT
        # =========================
       
    # =========================
    # GENERAL AI MODE
    # =========================
    reply = ask_ai(text)
    await update.message.reply_text(reply)

# =========================
# START BOT
# =========================
if __name__ == "__main__":
    print("🚀 NOUN HYBRID AI RUNNING")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("teach", teach))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)