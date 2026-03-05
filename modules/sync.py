import whisper
import json
import os
import torch

# Check for GPU (Your RTX 3050)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"   ⚙️ Whisper running on: {DEVICE.upper()}")

# Load model once (Global variable) to avoid reloading it every time
# 'base' is fast and accurate enough for clear TTS audio.
model = whisper.load_model("base", device=DEVICE)

def generate_subtitles(audio_path):
    """
    Uses OpenAI Whisper to generate word-level timestamps.
    Returns a list of dicts: [{'word': 'Hello', 'start': 0.5, 'end': 0.9}, ...]
    """
    print(f"👂 Listening to audio: {audio_path}...")
    
    if not os.path.exists(audio_path):
        print(f"❌ Error: Audio file not found at {audio_path}")
        return None

    try:
        # Transcribe with word timestamps
        result = model.transcribe(audio_path, word_timestamps=True)
        
        # Extract just the words
        word_segments = []
        for segment in result['segments']:
            for word in segment['words']:
                word_segments.append({
                    "word": word['word'].strip(),
                    "start": word['start'],
                    "end": word['end']
                })
        
        # Save to JSON for debugging/caching
        json_path = audio_path.replace(".mp3", ".json").replace(".wav", ".json")
        with open(json_path, "w") as f:
            json.dump(word_segments, f, indent=2)
            
        print(f"✅ Sync Complete! Found {len(word_segments)} words.")
        return word_segments

    except Exception as e:
        print(f"❌ Whisper Error: {e}")
        return None

if __name__ == "__main__":
    # Test path (Make sure you have audio from Step 1.1)
    TEST_AUDIO = "assets/temp/base_audio.mp3"
    
    # Run Sync
    segments = generate_subtitles(TEST_AUDIO)
    
    # Print first 3 words to prove it works
    if segments:
        print("   First 3 words:", segments[:3])