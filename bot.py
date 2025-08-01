# bot.py
import os
import sys
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import your modules
from src.google_docs import get_doc_content
from src.chatgpt import generate_chatgpt_responseimport os
print("Current Directory:", os.getcwd())
print("Directory Contents:", os.listdir())
print("src Contents:", os.listdir('src'))
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google_docs import get_doc_content
from chatgpt import generate_chatgpt_response
from dotenv import load_dotenv

load_dotenv()  # For local testing

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id
    logger.info(f"User {user_id}: {user_message}")
    
    mode = os.getenv('SOURCE_MODE', 'hybrid')
    
    try:
        if mode == 'google_docs':
            response = get_doc_content(os.getenv('GOOGLE_DOC_ID'))
        elif mode == 'chatgpt':
            response = await generate_chatgpt_response(user_message)
        else:  # Hybrid mode
            doc_content = get_doc_content(os.getenv('GOOGLE_DOC_ID'))
            prompt = f"Based on this document: '{doc_content[:2000]}'...\n\nAnswer this: {user_message}"
            response = await generate_chatgpt_response(prompt)
        
        await update.message.reply_text(response[:4000])  # Truncate to Telegram limits
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("⚠️ Sorry, I encountered an error. Please try again later.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! I'm your knowledge assistant. Ask me anything!")

def main():
    app = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    # Command Handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('mode', set_mode_command))
    
    # Message Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()
