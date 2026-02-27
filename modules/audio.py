import edge_tts
import asyncio
import os

# CONSTANTS
# "en-US-ChristopherNeural" is a deep, calm male voice. 
# "en-US-GuyNeural" is another good option.

VOICE = "en-US-ChristopherNeural"
OUTPUT_FILE = "assets/temp/base_audio.mp3"

async def generate_base_audio(text: str, output_path: str) -> str:
    """
    Generates standard TTS audio using Microsoft Edge's free API.
    
    Args:
        text (str): The script to speak.
        output_path (str): Where to save the .mp3 file.
        
    Returns:
        str: The path to the generated file.
    """
    print(f"Generating TTS for: '{text[:30]}...'")
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)
    
    print(f"Base audio saved to: {output_path}")
    return output_path

# --- TESTING BLOCK ---
# This only runs if you execute this file directly.
# --- UPDATED TESTING BLOCK ---
if __name__ == "__main__":
    test_text = "This is a system check. The audio engine is fully operational. and I am happy to be of service. Let's create some amazing content together!"
    
    # Python 3.13+ safe way to run async
    try:
        asyncio.run(generate_base_audio(test_text, OUTPUT_FILE))
    except Exception as e:
        print(f"❌ Error: {e}")