import os
import logging
import re
import json
from datetime import datetime
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
KNOWLEDGE_BASE_SHEET = "KnowledgeBase"
LOG_SHEET = "ConversationLogs"
SYSTEM_PROMPT = "You're a helpful assistant that answers questions conversationally"

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Initialize Google Sheets
def get_google_sheets_client():
    """Create authenticated Google Sheets client"""
    try:
        service_account_info = json.loads(os.getenv('SERVICE_ACCOUNT_JSON'))
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return gspread.authorize(creds)
    except Exception as e:
        logging.error(f"Google Sheets auth error: {e}")
        return None

# Load knowledge base from Google Sheets
def load_knowledge_base():
    """Load knowledge base from Google Sheet"""
    knowledge_base = []
    try:
        client = get_google_sheets_client()
        if not client:
            return []
            
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        worksheet = spreadsheet.worksheet(KNOWLEDGE_BASE_SHEET)
        records = worksheet.get_all_records()
        
        for record in records:
            patterns = record.get('Question Pattern', '').split('|')
            response = record.get('Response', '')
            keywords = record.get('Keywords', '').split(',') if record.get('Keywords') else []
            
            if patterns and response:
                knowledge_base.append({
                    'patterns': [p.strip().lower() for p in patterns if p.strip()],
                    'response': response,
                    'keywords': [kw.strip().lower() for kw in keywords if kw.strip()]
                })
                
    except Exception as e:
        logging.error(f"Error loading knowledge base: {e}")
    
    return knowledge_base

# Check if message matches knowledge base
def check_knowledge_base(message, knowledge_base):
    """Check if message matches any knowledge base entry"""
    message_lower = message.lower()
    
    for item in knowledge_base:
        # Check exact patterns
        for pattern in item['patterns']:
            if pattern and re.search(r'\b' + re.escape(pattern) + r'\b', message_lower):
                return item['response']
        
        # Check keywords
        if any(keyword and keyword in message_lower for keyword in item['keywords']):
            return item['response']
    
    return None

# Log conversation to Google Sheet
def log_conversation(user_id, username, message, response):
    """Log conversation to Google Sheet"""
    try:
        client = get_google_sheets_client()
        if not client:
            return
            
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            worksheet = spreadsheet.worksheet(LOG_SHEET)
        except:
            # Create sheet if doesn't exist
            worksheet = spreadsheet.add_worksheet(title=LOG_SHEET, rows=1000, cols=10)
            worksheet.append_row(["User ID", "Username", "User Message", "Bot Response", "Timestamp"])
        
        worksheet.append_row([
            str(user_id), 
            username, 
            message, 
            response, 
            datetime.utcnow().isoformat() + "Z"
        ])
    except Exception as e:
        logging.error(f"Conversation log error: {e}")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load knowledge base at startup
KNOWLEDGE_BASE = load_knowledge_base()
logger.info(f"Loaded {len(KNOWLEDGE_BASE)} knowledge base entries")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text('👋 Hello! I\'m your AI assistant powered by ChatGPT 3.5 and Google Sheets. Ask me anything!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    try:
        message = update.message.text
        user_id = update.message.from_user.id
        username = update.message.from_user.username or f"user_{user_id}"
        logger.info(f"User: {username} | Query: {message}")
        
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
            logger.info("Used knowledge base response")
        else:
            # Get ChatGPT response
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message}
                ],
                temperature=0.7
            )
            reply = response.choices[0].message.content
            await update.message.reply_text(reply)
            logger.info("Used ChatGPT response")
        
        # Log conversation
        log_conversation(user_id, username, message, reply)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("⚠️ Sorry, I encountered an error. Please try again.")

def main():
    """Start the bot"""
    # Create Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start Bot
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
