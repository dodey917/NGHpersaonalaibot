import os
import logging
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
import gspread
from google.oauth2.service_account import Credentials
import json

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
KNOWLEDGE_BASE_SHEET = "KnowledgeBase"  # Name of your knowledge base sheet
SYSTEM_PROMPT = "You're a helpful assistant that answers questions conversationally"

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Initialize Google Sheets
def init_google_sheets():
    # Load service account credentials from environment variable
    service_account_info = json.loads(os.getenv('SERVICE_ACCOUNT_JSON'))
    
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID)

# Load knowledge base from Google Sheets
def load_knowledge_base():
    try:
        spreadsheet = init_google_sheets()
        worksheet = spreadsheet.worksheet(KNOWLEDGE_BASE_SHEET)
        records = worksheet.get_all_records()
        
        knowledge_base = []
        for record in records:
            patterns = record['Question Pattern'].split('|')
            response = record['Response']
            keywords = record['Keywords'].split(',') if record['Keywords'] else []
            knowledge_base.append({
                'patterns': patterns,
                'response': response,
                'keywords': [kw.strip().lower() for kw in keywords]
            })
        return knowledge_base
    except Exception as e:
        logging.error(f"Error loading knowledge base: {e}")
        return []

# Check if message matches knowledge base
def check_knowledge_base(message, knowledge_base):
    message_lower = message.lower()
    
    for item in knowledge_base:
        # Check patterns
        for pattern in item['patterns']:
            if re.search(r'\b' + re.escape(pattern.lower()) + r'\b', message_lower):
                return item['response']
        
        # Check keywords
        if any(keyword in message_lower for keyword in item['keywords']):
            return item['response']
    
    return None

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load knowledge base at startup
KNOWLEDGE_BASE = load_knowledge_base()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I\'m your AI assistant. Ask me anything!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message.text
        user_id = update.message.from_user.id
        username = update.message.from_user.username or str(user_id)
        logging.info(f"User: {username} | Query: {message}")
        
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action='typing'
        )
        
        # First check knowledge base
        kb_response = check_knowledge_base(message, KNOWLEDGE_BASE)
        if kb_response:
            await update.message.reply_text(kb_response)
            reply = kb_response
        else:
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
        try:
            spreadsheet = init_google_sheets()
            log_sheet = spreadsheet.sheet1  # First sheet for logging
            log_sheet.append_row([
                str(user_id), 
                username, 
                message, 
                reply, 
                update.message.date.isoformat()
            ])
        except Exception as e:
            logging.error(f"Google Sheets error: {e}")

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
