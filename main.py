import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Token and Render URL from Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") # Render provides this automatically

# Initialize Telegram Bot Application natively (without starting its own polling loop)
telegram_app = Application.builder().token(TOKEN).build()

# --- BOT LOGIC ---

async def start(update: Update, context):
    """Sends a welcoming message when /start is used."""
    await update.message.reply_text(
        "👋 Welcome to Easy Word Count Bot!\n\n"
        "Just send me any text, and I will analyze the word count and format it into UPPERCASE and lowercase for you."
    )

async def process_text(update: Update, context):
    """Analyzes the text sent by the user."""
    text = update.message.text
    
    # Calculate Metrics
    words = text.split()
    word_count = len(words)
    char_count_with_spaces = len(text)
    char_count_no_spaces = len(text.replace(" ", ""))
    
    # Text Formats
    uppercase_text = text.upper()
    lowercase_text = text.lower()
    
    # Construct Response
    response_message = (
        f"📊 **Text Analysis:**\n"
        f"▪️ **Word Count:** {word_count}\n"
        f"▪️ **Characters (with spaces):** {char_count_with_spaces}\n"
        f"▪️ **Characters (no spaces):** {char_count_no_spaces}\n\n"
        f"🔠 **UPPERCASE VERSION:**\n`{uppercase_text}`\n\n"
        f"🔡 **lowercase version:**\n`{lowercase_text}`"
    )
    
    await update.message.reply_text(response_message, parse_mode="Markdown")

# Register Handlers to the application queue
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_text))

# --- WEBHOOK ROUTES FOR RENDER ---

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def respond():
    """Receives updates from Telegram and processes them."""
    if request.method == "POST":
        try:
            # Put the update into the telegram queue asynchronously
            update = Update.de_json(request.get_json(force=True), telegram_app.bot)
            telegram_app.update_queue.put_nowait(update)
            return "OK", 200
        except Exception as e:
            logger.error(f"Error handling webhook update: {e}")
            return "Error", 500

# Set webhook on startup (Runs once when Render triggers the container)
with telegram_app:
    if RENDER_URL:
        # We target the URL endpoint assigned to the token for security
        webhook_target = f"{RENDER_URL}/{TOKEN}"
        import asyncio
        asyncio.get_event_loop().run_until_complete(telegram_app.bot.set_webhook(url=webhook_target))
        logger.info(f"Webhook set to: {webhook_target}")
