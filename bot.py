import os
import openai
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize conversation history
conversations = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when user sends /start"""
    user = update.message.from_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 🤖\n"
        "I'm your AI Telegram assistant.\n\n"
        "Just send me a message and I'll respond!\n"
        "Use /help for commands info\n"
        "Use /reset to clear our conversation history."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when user sends /help"""
    help_text = """
    🤖 AI Telegram Bot Help:
    
    Available commands:
    /start - Start the bot
    /help - Show this help message
    /reset - Clear conversation history
    
    Just send a message to chat with the AI!
    """
    await update.message.reply_text(help_text)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history"""
    user_id = update.message.from_user.id
    conversations[user_id] = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    await update.message.reply_text("🔄 Conversation history cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages with conversation history"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Initialize conversation if new user
    if user_id not in conversations:
        conversations[user_id] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
    
    # Add user message to history
    conversations[user_id].append({"role": "user", "content": text})
    
    try:
        # Generate response
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversations[user_id],
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_reply = response.choices[0].message.content
        
        # Add to history
        conversations[user_id].append({"role": "assistant", "content": ai_reply})
        
        # Split long messages
        if len(ai_reply) > 4000:
            for i in range(0, len(ai_reply), 4000):
                await update.message.reply_text(ai_reply[i:i+4000])
        else:
            await update.message.reply_text(ai_reply)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("⚠️ I encountered an error. Please try again later.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot with webhook or polling"""
    logger.info("Starting bot...")
    
    # Validate environment variables
    if not os.getenv("TELEGRAM_TOKEN") or not os.getenv("OPENAI_API_KEY"):
        logger.error("Missing required environment variables!")
        raise ValueError("TELEGRAM_TOKEN and OPENAI_API_KEY must be set")
    
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Deployment detection
    if os.getenv("RENDER", "false").lower() == "true":
        public_url = os.getenv("RENDER_EXTERNAL_URL") or f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com"
        logger.info(f"Starting webhook on {public_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 10000)),
            webhook_url=f"{public_url}/webhook",
            drop_pending_updates=True
        )
    else:
        logger.info("Starting polling...")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
