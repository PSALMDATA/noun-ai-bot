import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 🔑 YOUR KEYS
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

openai.api_key = OPENAI_API_KEY


# 🧠 INTENT DETECTION FUNCTION
def detect_intent(text: str):
    text = text.lower()

    if "summary" in text:
        return "summary"
    if "past question" in text or "exam question" in text:
        return "past_question"
    if "material" in text or "course material" in text:
        return "material"
    if "how to" in text:
        return "how_to"

    return "ai"


# 🤖 AI RESPONSE FUNCTION
def ask_ai(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an academic assistant for Nigerian university students. Keep answers simple and helpful."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']


# 📩 MESSAGE HANDLER
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    intent = detect_intent(user_text)

    if intent == "summary":
        reply = "📘 Kindly search the group or visit: https://psalmedu.com/summary"

    elif intent == "past_question":
        reply = "📄 Download past questions here: https://psalmedu.com/noun-past-questions"

    elif intent == "material":
        reply = "📖 Access course materials: https://psalmedu.com/noun-material"

    elif intent == "how_to":
        reply = "📲 Kindly contact admin for guidance: https://wa.me/9163490176"

    else:
        reply = ask_ai(user_text)
        reply += "\n\n📚 More resources: https://psalmedu.com"

    await update.message.reply_text(reply)


# 🚀 START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 NOUN AI Bot is active. Ask me anything academic.")


# 🔥 MAIN APP
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()