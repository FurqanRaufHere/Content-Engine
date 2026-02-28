import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_script(topic):
    """
    Uses Llama 3 via Groq to generate a viral short script.
    Returns a JSON object with 'hook', 'body', and 'visual_keywords'.
    """
    print(f"Brainstorming concept for: '{topic}'...")

    system_prompt = """
    You are an expert viral content strategist for YouTube Shorts.
    Your goal is to write a high-retention script.
    
    RULES:
    1. The 'hook' must be 1 short sentence that grabs attention immediately.
    2. The 'body' must be deep, punchy, and strictly above  20 words and less than 100. (Do not write less than 20 words).
    3. 'visual_keywords' must be a list of 2-3 specific nouns/verbs for stock footage search.
    
    OUTPUT FORMAT (Strict JSON):
    {
      "hook": "The text for the opening hook.",
      "body": "The main motivational speech text.",
      "visual_keywords": ["keyword1", "keyword2"]
    }
    """


    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic: {topic}"}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}  # CRITICAL: Forces JSON
        )

        # Parse the response
        response_content = completion.choices[0].message.content
        script_data = json.loads(response_content)

        print("✅ Script Generated:")
        print(f"   🪝 Hook: {script_data['hook']}")
        print(f"   📜 Body: {script_data['body']}")
        print(f"   👀 Visuals: {script_data['visual_keywords']}")

        return script_data

    except Exception as e:
        print(f"Brain Error: {e}")
        return None

if __name__ == "__main__":
    # Test the Brain
    generate_script("Discipline")