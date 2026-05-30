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

# Load courses database
with open("courses.json", "r", encoding="utf-8") as f:
    COURSES = json.load(f)


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
# COURSE DETECTION
# =========================

def find_course_code(text):
    match = re.search(r"\b[A-Z]{2,4}\s?\d{3}\b", text.upper())

    if match:
        return match.group().replace(" ", "")

    return None


def find_course_info(text):
    code = find_course_code(text)

    if code and code in COURSES:
        return code, COURSES[code]

    return None, None


# =========================
# INTENT DETECTION
# =========================

def detect_intent(text):
    text = text.lower()

    if "summary" in text or "summaries" in text:
        return "summary"

    if (
        "past question" in text
        or "past questions" in text
        or "pq" in text
    ):
        return "past_question"

    if "material" in text or "course material" in text:
        return "material"

    if "how to" in text or "how do i" in text:
        return "how_to"

    return "ai"


# =========================
# OPENAI RESPONSE
# =========================

def ask_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
You are NOUN AI Assistant created by PSALMEDU.

You help NOUN students with:
- summaries
- past questions
- course materials
- exam guidance
- TMA guidance

IMPORTANT RULES:
- If a verified NOUN course title exists, use it.
- Never invent course titles.
- Be concise and student-friendly.
- Always promote https://psalmedu.com when relevant.
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# =========================
# START COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 NOUN AI Assistant is active.\n\nAsk me anything academic."
    )


# =========================
# TEACH COMMAND
# =========================

async def teach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/teach", "").strip()

    if "=" not in text:
        await update.message.reply_text(
            "Use this format:\n/teach GST105 = History and Philosophy of Science"
        )
        return

    key, value = text.split("=", 1)

    key = key.strip().upper()
    value = value.strip()

    corrections = load_corrections()

    corrections[key] = value

    save_corrections(corrections)

    await update.message.reply_text(
        f"✅ Saved correction:\n{key} = {value}"
    )


# =========================
# LEARNED COMMAND
# =========================

async def learned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    corrections = load_corrections()

    if not corrections:
        await update.message.reply_text(
            "No corrections saved yet."
        )
        return

    text = "📚 Saved corrections:\n\n"

    for key, value in corrections.items():
        text += f"{key} = {value}\n"

    await update.message.reply_text(text[:4000])


# =========================
# FORGET COMMAND
# =========================

async def forget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.replace("/forget", "").strip().upper()

    if not key:
        await update.message.reply_text(
            "Use this format:\n/forget GST105"
        )
        return

    corrections = load_corrections()

    if key in corrections:
        del corrections[key]

        save_corrections(corrections)

        await update.message.reply_text(
            f"🗑️ Removed correction for {key}"
        )
    else:
        await update.message.reply_text(
            f"No correction found for {key}"
        )


# =========================
# MAIN MESSAGE HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # -------------------------
    # CHECK MANUAL CORRECTIONS
    # -------------------------

    corrections = load_corrections()

    detected_code = find_course_code(user_text)

    if detected_code and detected_code in corrections:

        course_title = corrections[detected_code]

        if user_text.strip().upper() == detected_code:

            reply = (
                f"📘 {detected_code}: {course_title}\n\n"
                f"📖 Course Materials:\nhttps://psalmedu.com/noun-material\n\n"
                f"📚 Summaries:\nhttps://psalmedu.com/summary\n\n"
                f"📄 Past Questions:\nhttps://psalmedu.com/noun-past-questions"
            )

        else:

            verified_prompt = f"""
The student is asking about this verified NOUN course:

Course Code: {detected_code}
Course Title: {course_title}

Use this verified information.
Do not invent another title.

Student question:
{user_text}
"""

            reply = ask_ai(verified_prompt)

            reply += "\n\n📚 More academic help: https://psalmedu.com"

        await update.message.reply_text(reply)

        return

    # -------------------------
    # CHECK COURSES DATABASE
    # -------------------------

    course_code, course_data = find_course_info(user_text)

    if course_code:

        reply = (
            f"📘 {course_code}\n"
            f"🎓 {course_data['title']}\n\n"
            f"📖 Materials:\n{course_data['psalmedu_material']}\n\n"
            f"📚 Summaries:\n{course_data['summary']}\n\n"
            f"📄 Past Questions:\n{course_data['past_questions']}"
        )

        await update.message.reply_text(reply)

        return

    # -------------------------
    # DETECT INTENT
    # -------------------------

    intent = detect_intent(user_text)

    if intent == "summary":

        reply = (
            "📘 Kindly search the group using the search button "
            "or visit:\nhttps://psalmedu.com/summary"
        )

    elif intent == "past_question":

        reply = (
            "📄 Kindly download all past questions from:\n"
            "https://psalmedu.com/noun-past-questions"
        )

    elif intent == "material":

        reply = (
            "📖 Kindly download course materials from:\n"
            "https://psalmedu.com/noun-material"
        )

    elif intent == "how_to":

        reply = (
            "📲 Kindly DM Admin here:\n"
            "https://wa.me/9163490176"
        )

    else:

        reply = ask_ai(user_text)

        reply += "\n\n📚 More academic help: https://psalmedu.com"

    await update.message.reply_text(reply)


# =========================
# APP
# =========================

app = ApplicationBuilder().token(
    TELEGRAM_BOT_TOKEN
).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("teach", teach))
app.add_handler(CommandHandler("learned", learned))
app.add_handler(CommandHandler("forget", forget))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("Bot is running...")

app.run_polling()