# Autoshorts MVP

An autonomous pipeline that generates ready-to-publish vertical short-form videos (YouTube Shorts, TikTok, Reels) from a single text prompt or a bulk text file. 

## Architecture

* **Brain (`modules/brain.py`)**: Generates the hook, script body, and visual keywords using an LLM.
* **Curator (`modules/curator.py`)**: Validates script information and sources factual external quotes.
* **Audio (`modules/audio.py`)**: Converts the text script to human-sounding text-to-speech using Edge-TTS.
* **Visuals (`modules/visuals.py`)**: Fetches relevant vertical HD background footage via the Pexels API.
* **Sync (`modules/sync.py`)**: Generates precise word-level timestamps using Whisper for karaoke subtitles.
* **Editor (`modules/editor.py`)**: Assembles the final video using MoviePy and FFmpeg. Normalizes audio, mixes background music, and burns subtitles.
* **Master Loop (`main.py`)**: The core controller running the pipeline in single or batch factory mode.

## Prerequisites

1. **Python 3.10+**
2. **FFmpeg**: Must be installed and accessible by the system.
3. **ImageMagick**: Required for MoviePy text rendering. 
   * Windows: Download the DLL version and check "Install legacy utilities". Verify the `IMAGEMAGICK_PATH` in `modules/editor.py` points to your `magick.exe`.