import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Token and Render URL from Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

# Initialize Telegram Bot Application natively
telegram_app = Application.builder().token(TOKEN).build()

# Flag to ensure the webhook is only set up once
webhook_initialized = False

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

# --- ASYNC WEBHOOK INITIALIZATION ---

async def setup_webhook():
    """Initializes the application and sets the webhook configuration."""
    global webhook_initialized
    if not webhook_initialized and RENDER_URL:
        # Initialize components under the hood
        await telegram_app.initialize()
        
        # Set Telegram webhook target
        webhook_target = f"{RENDER_URL}/{TOKEN}"
        await telegram_app.bot.set_webhook(url=webhook_target)
        logger.info(f"🚀 Webhook successfully set to: {webhook_target}")
        
        webhook_initialized = True

# --- WEBHOOK ROUTES FOR RENDER ---

@app.before_request
def initialize_bot_webhook():
    """Flask hook that runs right before processing the incoming web request."""
    if not webhook_initialized:
        try:
            # Safely bridge async webhook setup into Flask's sync lifecycle
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(setup_webhook())

@app.route("/", methods=["GET"])
def index():
    return "Bot is running perfectly!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def respond():
    """Receives updates from Telegram and processes them."""
    if request.method == "POST":
        try:
            # Extract update payload and push it directly into the queue
            update = Update.de_json(request.get_json(force=True), telegram_app.bot)
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
                
            loop.create_task(telegram_app.process_update(update))
            return "OK", 200
        except Exception as e:
            logger.error(f"Error handling webhook update: {e}")
            return "Error", 500
