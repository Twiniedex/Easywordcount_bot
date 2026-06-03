@app.route(f"/{TOKEN}", methods=["POST"])
def respond():
    """Receives updates from Telegram and processes them."""
    if request.method == "POST":
        try:
            # Extract update payload
            update = Update.de_json(request.get_json(force=True), telegram_app.bot)
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
                
            # FIX: We use 'run_until_complete' to force Gunicorn to wait 
            # until the bot handles and replies to the message before closing the request.
            loop.run_until_complete(telegram_app.process_update(update))
            return "OK", 200
        except Exception as e:
            logger.error(f"Error handling webhook update: {e}")
            return "Error", 500
