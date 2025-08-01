import os
import openai
from cachetools import TTLCache

# Configure response caching (1-hour TTL)
response_cache = TTLCache(maxsize=500, ttl=3600)

async def generate_chatgpt_response(prompt: str) -> str:
    try:
        # Check cache first
        cached = response_cache.get(prompt)
        if cached:
            return f"⚡ Cached response:\n\n{cached}"
        
        client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = await client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4-turbo'),
            messages=[
                {"role": "system", "content": "You're a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        response_cache[prompt] = content  # Cache response
        return content
    
    except Exception as e:
        return f"⚠️ ChatGPT error: {str(e)}"
