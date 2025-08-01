import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google_docs import get_doc_content
from chatgpt import generate_chatgpt_response
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Restrict access to specific users (optional)
ALLOWED_USERS = [int(os.getenv('TELEGRAM_ADMIN_ID'))] if os.getenv('TELEGRAM_ADMIN_ID') else None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Check if user is allowed
        if ALLOWED_USERS and update.effective_user.id not in ALLOWED_USERS:
            await update.message.reply_text("⛔ Unauthorized access")
            return

        user_message = update.message.text
        mode = os.getenv('SOURCE_MODE', 'hybrid')
        
        if mode == 'google_docs':
            response = get_doc_content(os.getenv('GOOGLE_DOC_ID'))
        elif mode == 'chatgpt':
            response = await generate_chatgpt_response(user_message)
        else:  # Hybrid mode
            doc_content = get_doc_content(os.getenv('GOOGLE_DOC_ID'))
            prompt = f"Document context:\n{doc_content[:2000]}\n\nUser question: {user_message}"
            response = await generate_chatgpt_response(prompt)
        
        await update.message.reply_text(response[:4000])  # Telegram message limit
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("⚠️ Sorry, I encountered an error. Please try again later.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! I'm your knowledge assistant. Ask me anything!")

def main():
    app = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    # Command Handlers
    app.add_handler(CommandHandler('start', start_command))
    
    # Message Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    app.run_polling()

if __name__ == '__main__':
    main()
