import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

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
                "content": "You are NOUN AI Assistant for Nigerian Open University students. Give short, clear academic help and promote PSALMEDU resources when relevant."
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    intent = detect_intent(user_text)

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
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()
