import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
SYSTEM_PROMPT = "You're a helpful assistant that answers questions conversationally"

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Initialize Google Sheets
def init_google_sheets():
    creds = Credentials.from_service_account_file(
        'service_account.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I\'m your ChatGPT 3.5 assistant with Google Docs integration. Ask me anything!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message.text
        user_id = update.message.from_user.id
        logging.info(f"User: {user_id} | Query: {message}")
        
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action='typing'
        )
        
        # Get ChatGPT response
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            temperature=0.7
        )
        
        reply = response.choices[0].message['content']
        await update.message.reply_text(reply)
        
        # Log to Google Sheet
        sheet = init_google_sheets()
        sheet.append_row([str(user_id), message, reply])
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("Sorry, I encountered an error. Please try again.")

def main():
    # Create Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start Bot
    application.run_polling()

if __name__ == "__main__":
    main()
