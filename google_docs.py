import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from cachetools import TTLCache

# Cache document content (30-minute TTL)
doc_cache = TTLCache(maxsize=5, ttl=1800)

SCOPES = ['https://www.googleapis.com/auth/documents.readonly']

def get_doc_content(doc_id: str) -> str:
    try:
        # Check cache first
        if doc_id in doc_cache:
            return doc_cache[doc_id]
        
        # Load credentials from environment
        creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if not creds_json:
            return "❌ Google credentials not configured"
            
        creds = service_account.Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=SCOPES
        )
        
        service = build('docs', 'v1', credentials=creds)
        document = service.documents().get(documentId=doc_id).execute()
        
        # Extract text content
        content = []
        for elem in document.get('body', {}).get('content', []):
            if 'paragraph' in elem:
                for para in elem['paragraph']['elements']:
                    if 'textRun' in para:
                        content.append(para['textRun']['content'])
        
        full_content = ''.join(content)
        doc_cache[doc_id] = full_content  # Cache result
        return full_content
    
    except Exception as e:
        return f"❌ Google Docs error: {str(e)}"
