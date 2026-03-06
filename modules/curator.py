import requests
import json

def get_quote(category="inspiration"):
    print(f"🕵️ Searching for a {category} quote...")
    
    # ZenQuotes API (Free tier)
    url = "https://zenquotes.io/api/random"
    
    try:
        response = requests.get(url)
        data = response.json()[0]
        
        quote_text = data['q']
        author = data['a']
        
        # Filter: Keep it short (under 200 chars) for video retention
        if len(quote_text) > 400:
            print("   ⚠️ Quote too long, retrying...")
            return get_quote(category)
            
        print(f"✅ Quote Found: \"{quote_text}\" - {author}")
        
        return {
            "text": quote_text,
            "author": author
        }
        
    except Exception as e:
        print(f"❌ Curator Error: {e}")
        return None

if __name__ == "__main__":
    # Test the Curator
    get_quote()