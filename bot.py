import os
import json
import re
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

CORRECTIONS_FILE = "corrections.json"


def load_corrections():
    if os.path.exists(CORRECTIONS_FILE):
        with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_corrections(data):
    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_course_code(text):
    match = re.search(r"\b[A-Z]{2,4}\s?\d{3}\b", text.upper())
    if match:
        return match.group().replace(" ", "")
    return None


def detect_intent(text):
    text = text.lower()

    if "summary" in text or "summaries" in text:
        return "summary"
    if "past question" in text or "past questions" in text or "pq" in text:
        return "past_question"
    if "material" in text or "course material" in text:
        return "material"
    if "how to" in text or "how do i" in text:
        return "how_to"

    return "ai"


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

Important:
If a NOUN course code/title is provided in the prompt, use that verified information.
Do not guess course titles.
Keep responses concise, smart and student-friendly.
Always promote https://psalmedu.com when relevant.
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return response.choices[0].message.content


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 NOUN AI Assistant is active.\n\nAsk me anything academic."
    )


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

    if not key or not value:
        await update.message.reply_text(
            "Use this format:\n/teach GST105 = History and Philosophy of Science"
        )
        return

    corrections = load_corrections()
    corrections[key] = value
    save_corrections(corrections)

    await update.message.reply_text(f"✅ Saved correction:\n{key} = {value}")


async def learned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    corrections = load_corrections()

    if not corrections:
        await update.message.reply_text("No corrections saved yet.")
        return

    text = "📚 Saved corrections:\n\n"
    for key, value in corrections.items():
        text += f"{key} = {value}\n"

    await update.message.reply_text(text[:4000])


async def forget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/forget", "").strip().upper()

    if not text:
        await update.message.reply_text("Use this format:\n/forget GST105")
        return

    corrections = load_corrections()

    if text in corrections:
        del corrections[text]
        save_corrections(corrections)
        await update.message.reply_text(f"🗑️ Removed correction for {text}")
    else:
        await update.message.reply_text(f"No correction found for {text}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    intent = detect_intent(user_text)

    corrections = load_corrections()
    course_code = find_course_code(user_text)

    if course_code and course_code in corrections:
        course_title = corrections[course_code]

        if user_text.strip().upper() == course_code:
            reply = (
                f"📘 {course_code}: {course_title}\n\n"
                f"📖 Course materials: https://psalmedu.com/noun-material\n"
                f"📚 Summary: https://psalmedu.com/summary\n"
                f"📄 Past questions: https://psalmedu.com/noun-past-questions"
            )
        else:
            verified_prompt = f"""
The student is asking about this verified NOUN course:

Course Code: {course_code}
Course Title: {course_title}

Use this verified course information. Do not guess another title.

Student question:
{user_text}
"""
            reply = ask_ai(verified_prompt)
            reply += "\n\n📚 More academic help: https://psalmedu.com"

        await update.message.reply_text(reply)
        return

    if intent == "summary":
        reply = "📘 Kindly search the group using the search button or visit: https://psalmedu.com/summary"

    elif intent == "past_question":
        reply = "📄 Kindly download all past questions from: https://psalmedu.com/noun-past-questions"

    elif intent == "material":
        reply = "📖 Kindly download course materials from: https://psalmedu.com/noun-material"

    elif intent == "how_to":
        reply = "📲 Kindly DM Admin here: https://wa.me/9163490176"

    else:
        reply = ask_ai(user_text)
        reply += "\n\n📚 More academic help: https://psalmedu.com"

    await update.message.reply_text(reply)


app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("teach", teach))
app.add_handler(CommandHandler("learned", learned))
app.add_handler(CommandHandler("forget", forget))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()
