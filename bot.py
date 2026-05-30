import os
import json
import re
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

CORRECTIONS_FILE = "corrections.json"

# =========================
# LOAD COURSES (WITH FULL NORMALIZATION)
# =========================
with open("courses.json", "r", encoding="utf-8") as f:
    RAW_COURSES = json.load(f)

def normalize(code):
    return re.sub(r"[^A-Z0-9]", "", code.upper())

COURSES = {normalize(k): v for k, v in RAW_COURSES.items()}


# =========================
# CORRECTIONS SYSTEM
# =========================
def load_corrections():
    if os.path.exists(CORRECTIONS_FILE):
        with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_corrections(data):
    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =========================
# COURSE DETECTION (IMPROVED)
# =========================
def find_course_code(text):
    match = re.search(r"\b[A-Z]{2,4}\s?-?\d{3}\b", text.upper())
    if match:
        return normalize(match.group())
    return None


# =========================
# INTENT DETECTION
# =========================
def detect_intent(text):
    text = text.lower()

    if re.search(r"\b[a-z]{2,4}\s?-?\d{3}\b", text.lower()):
        return "course"

    if "summary" in text:
        return "summary"

    if "past question" in text or "pq" in text:
        return "past_question"

    if "material" in text:
        return "material"

    if "how to" in text:
        return "how_to"

    return "ai"


# =========================
# AI (SAFE FALLBACK)
# =========================
def ask_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
You are NOUN AI Assistant.
NEVER invent course codes or titles.
Be concise.
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
    await update.message.reply_text(
        "🤖 NOUN AI Assistant is active.\nAsk me anything academic."
    )


async def teach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/teach", "").strip()

    if "=" not in text:
        await update.message.reply_text("Format: /teach GST105 = Course Title")
        return

    key, value = text.split("=", 1)
    key = normalize(key)
    value = value.strip()

    corrections = load_corrections()
    corrections[key] = value
    save_corrections(corrections)

    await update.message.reply_text(f"✅ Learned: {key} = {value}")


async def learned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    corrections = load_corrections()

    if not corrections:
        await update.message.reply_text("No saved corrections.")
        return

    msg = "📚 Learned courses:\n\n"
    for k, v in corrections.items():
        msg += f"{k} = {v}\n"

    await update.message.reply_text(msg[:4000])


async def forget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = normalize(update.message.text.replace("/forget", "").strip())

    corrections = load_corrections()

    if key in corrections:
        del corrections[key]
        save_corrections(corrections)
        await update.message.reply_text(f"🗑 Removed {key}")
    else:
        await update.message.reply_text("Not found.")


# =========================
# MAIN HANDLER
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    corrections = load_corrections()

    code = find_course_code(user_text)

    # =========================
    # 1. CORRECTIONS FIRST
    # =========================
    if code:
        if code in corrections:
            await update.message.reply_text(f"📘 {code}: {corrections[code]}")
            return

        if code in COURSES:
            course = COURSES[code]

            await update.message.reply_text(
                f"""📘 {code}
🎓 {course['title']}

📖 {course.get('psalmedu_material', '')}
📚 {course.get('summary', '')}
📄 {course.get('past_questions', '')}
"""
            )
            return

        await update.message.reply_text("❌ Course not found.")
        return

    # =========================
    # 2. INTENT HANDLING
    # =========================
    intent = detect_intent(user_text)

    if intent == "summary":
        reply = "📘 https://psalmedu.com/summary"

    elif intent == "past_question":
        reply = "📄 https://psalmedu.com/noun-past-questions"

    elif intent == "material":
        reply = "📖 https://psalmedu.com/noun-material"

    elif intent == "how_to":
        reply = "📲 https://wa.me/9163490176"

    else:
        reply = ask_ai(user_text)

    await update.message.reply_text(reply)


# =========================
# START BOT (RAILWAY SAFE)
# =========================
if __name__ == "__main__":
    print("Bot is starting...")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("teach", teach))
    app.add_handler(CommandHandler("learned", learned))
    app.add_handler(CommandHandler("forget", forget))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)