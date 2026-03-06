import os
import json
import random
import subprocess
import time
from moviepy.config import change_settings, get_setting

# --- CONFIGURATION ---
IMAGEMAGICK_PATH = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe" 
if os.path.exists(IMAGEMAGICK_PATH):
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_PATH})

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# --- SETTINGS ---
FONT = "Arial-Bold" 
FONT_SIZE = 80
FONT_COLOR = "white"
STROKE_COLOR = "black"
STROKE_WIDTH = 3

def get_random_music():
    music_folder = "assets/music"
    if not os.path.exists(music_folder): return None
    valid_extensions = ('.mp3', '.wav', '.m4a')
    tracks = [f for f in os.listdir(music_folder) if f.lower().endswith(valid_extensions)]
    return os.path.join(music_folder, random.choice(tracks)) if tracks else None

def check_file_exists(path, description):
    """Verifies a file exists and is not empty."""
    if not os.path.exists(path):
        print(f"❌ ERROR: {description} not found at {path}")
        return False
    size = os.path.getsize(path)
    if size < 1000: # Less than 1KB
        print(f"⚠️ WARNING: {description} is suspiciously small ({size} bytes).")
        return False
    return True

def run_ffmpeg(cmd):
    """Runs FFmpeg and prints errors if it fails."""
    print(f"   ⚙️ Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"❌ FFmpeg Failed:\n{result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ System Error: {e}")
        return False

def create_advanced_video(video_path, audio_path, timestamp_path, output_path):
    print("🎬 Starting Advanced Video Assembly...")
    ffmpeg = get_setting("FFMPEG_BINARY")

    # RELATIVE PATHS (Safe Mode)
    video_path = os.path.relpath(video_path)
    audio_path = os.path.relpath(audio_path)
    output_path = os.path.relpath(output_path)

    if not os.path.exists(timestamp_path):
        print("❌ Error: Timestamps JSON not found.")
        return

    # --- PART 1: VISUALS ---
    print("   1. Generating Video Layer...")
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)

    with open(timestamp_path, 'r') as f:
        word_segments = json.load(f)

    # Crop & Resize
    target_ratio = 9/16
    if video_clip.w / video_clip.h > target_ratio:
        video_clip = video_clip.crop(x1=video_clip.w/2 - (video_clip.h*target_ratio)/2, 
                                     width=video_clip.h*target_ratio, height=video_clip.h)
    video_clip = video_clip.resize(height=1920)

    # Loop
    if audio_clip.duration > video_clip.duration:
        video_clip = video_clip.loop(duration=audio_clip.duration)
    else:
        video_clip = video_clip.subclip(0, audio_clip.duration)

    # Subtitles
    subtitle_clips = []
    for segment in word_segments:
        word = segment['word'].upper()
        if not word: continue
        txt_clip = (TextClip(word, fontsize=FONT_SIZE, font=FONT, 
                             color=FONT_COLOR, stroke_color=STROKE_COLOR, stroke_width=STROKE_WIDTH)
                    .set_position('center').set_start(segment['start']).set_duration(segment['end'] - segment['start']))
        subtitle_clips.append(txt_clip)

    # Render Silent Video
    temp_silent = "assets/temp/final_silent.mp4"
    if os.path.exists(temp_silent): os.remove(temp_silent)
    
    CompositeVideoClip([video_clip] + subtitle_clips).write_videofile(
        temp_silent, fps=30, codec="libx264", audio=False, preset="ultrafast", threads=4, logger=None
    )
    time.sleep(1)

    # --- PART 2: AUDIO ENGINE ---
    print("   2. Preparing Audio Engine...")
    music_path = get_random_music()
    
    # Intermediate files
    norm_voice = "assets/temp/norm_voice.wav"
    norm_music = "assets/temp/norm_music.wav"
    mixed_wav = "assets/temp/mixed.wav" # <--- We will merge THIS directly

    # A. Normalize Voice
    run_ffmpeg([ffmpeg, '-y', '-i', audio_path, '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', norm_voice])
    if not check_file_exists(norm_voice, "Normalized Voice"): return

    if music_path:
        print(f"      🎵 Mixing Music: {os.path.basename(music_path)}")
        # B. Normalize Music
        run_ffmpeg([ffmpeg, '-y', '-i', music_path, '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', norm_music])
        
        # C. Mix to WAV
        cmd_mix = [
            ffmpeg, '-y',
            '-i', norm_voice, '-i', norm_music,
            '-filter_complex', '[1:a]volume=0.2[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[a]',
            '-map', '[a]', '-c:a', 'pcm_s16le',
            mixed_wav
        ]
        run_ffmpeg(cmd_mix)
        
        if not check_file_exists(mixed_wav, "Mixed Audio"): return
        final_audio_source = mixed_wav
        
    else:
        # No music found? Use normalized voice.
        final_audio_source = norm_voice

    # --- PART 3: FINAL GLUE (ENCODE MODE) ---
    print("   3. Gluing Video + Audio...")
    
    # CRITICAL CHANGE: We do NOT use '-c copy' for audio.
    # We force FFmpeg to encode the WAV to AAC *during* the merge.
    # This fixes the "Silent MP4" bug.
    cmd_merge = [
        ffmpeg, '-y',
        '-i', temp_silent,        # Input 0: Video
        '-i', final_audio_source, # Input 1: WAV Audio
        '-c:v', 'copy',           # Copy Video (Fast)
        '-c:a', 'aac',            # Encode Audio (Reliable)
        '-b:a', '192k',           # High Quality Audio
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        output_path
    ]
    
    if run_ffmpeg(cmd_merge):
        print(f"✅ SUCCESS! Final video saved to: {output_path}")
        # Final Verification
        final_size = os.path.getsize(output_path)
        print(f"   📊 Final File Size: {final_size/1024/1024:.2f} MB")
        
        # FINAL CHECK
        if final_size < 1000000: # If < 1MB, something is wrong
             print("   ⚠️ WARNING: Video seems small. Check assets/temp/mixed.wav to see if audio exists.")
    else:
        print("❌ CRITICAL: Final merge failed.")

    # Cleanup
    try:
        time.sleep(1)
        if os.path.exists(temp_silent): os.remove(temp_silent)
        if os.path.exists(norm_voice): os.remove(norm_voice)
        if os.path.exists(norm_music): os.remove(norm_music)
        # We keep mixed.wav for a moment in case you need to debug
        if os.path.exists(mixed_wav): os.remove(mixed_wav)
    except:
        pass

if __name__ == "__main__":
    # Test Block
    VIDEO = "assets/temp/test_video.mp4" 
    AUDIO = "assets/temp/test_audio.mp3" 
    # create_advanced_video(VIDEO, AUDIO, "assets/temp/test_audio.json", "assets/output/test.mp4")




# import os
# import json
# import random
# import subprocess
# from moviepy.config import change_settings, get_setting

# # --- CONFIGURATION ---
# IMAGEMAGICK_PATH = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe" 
# if os.path.exists(IMAGEMAGICK_PATH):
#     change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_PATH})

# # --- HOTFIX FOR PILLOW ---
# import PIL.Image
# if not hasattr(PIL.Image, 'ANTIALIAS'):
#     PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# # --- STYLE SETTINGS ---
# FONT = "Arial-Bold" 
# FONT_SIZE = 80
# FONT_COLOR = "white"
# STROKE_COLOR = "black"
# STROKE_WIDTH = 3

# def get_random_music():
#     """Finds a random music file in assets/music."""
#     music_folder = "assets/music"
#     if not os.path.exists(music_folder): return None
    
#     valid_extensions = ('.mp3', '.wav', '.m4a')
#     tracks = [f for f in os.listdir(music_folder) if f.lower().endswith(valid_extensions)]
    
#     if not tracks: return None
#     return os.path.join(music_folder, random.choice(tracks))

# def run_ffmpeg(cmd):
#     """Runs FFmpeg and prints errors if it fails."""
#     try:
#         # We allow it to print errors (stderr) so you can see if it crashes
#         subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
#         return True
#     except subprocess.CalledProcessError as e:
#         print(f"❌ FFmpeg Error: {e.stderr.decode('utf-8')}")
#         return False

# def create_advanced_video(video_path, audio_path, timestamp_path, output_path):
#     print("🎬 Starting Advanced Video Assembly...")
#     ffmpeg = get_setting("FFMPEG_BINARY")

#     if not os.path.exists(timestamp_path):
#         print("❌ Error: Timestamps JSON not found.")
#         return

#     # --- PART 1: VISUALS (MOVIEPY) ---
#     print("   1. Generating Video Layer...")
#     video_clip = VideoFileClip(video_path)
#     audio_clip = AudioFileClip(audio_path) # Used only for duration

#     with open(timestamp_path, 'r') as f:
#         word_segments = json.load(f)

#     # Crop & Resize
#     target_ratio = 9/16
#     if video_clip.w / video_clip.h > target_ratio:
#         video_clip = video_clip.crop(x1=video_clip.w/2 - (video_clip.h*target_ratio)/2, 
#                                      width=video_clip.h*target_ratio, height=video_clip.h)
#     video_clip = video_clip.resize(height=1920)

#     # Loop
#     if audio_clip.duration > video_clip.duration:
#         video_clip = video_clip.loop(duration=audio_clip.duration)
#     else:
#         video_clip = video_clip.subclip(0, audio_clip.duration)

#     # Subtitles
#     subtitle_clips = []
#     for segment in word_segments:
#         word = segment['word'].upper()
#         if not word: continue
#         txt_clip = (TextClip(word, fontsize=FONT_SIZE, font=FONT, 
#                              color=FONT_COLOR, stroke_color=STROKE_COLOR, stroke_width=STROKE_WIDTH)
#                     .set_position('center').set_start(segment['start']).set_duration(segment['end'] - segment['start']))
#         subtitle_clips.append(txt_clip)

#     # Render Silent Video
#     temp_silent = "assets/temp/final_silent.mp4"
#     if os.path.exists(temp_silent): os.remove(temp_silent)
    
#     # Write video WITHOUT audio
#     CompositeVideoClip([video_clip] + subtitle_clips).write_videofile(
#         temp_silent, fps=30, codec="libx264", audio=False, preset="ultrafast", threads=4, logger=None
#     )

#     # --- PART 2: AUDIO MIXING (NUCLEAR METHOD) ---
#     print("   2. Mixing Audio (Nuclear Method)...")
#     music_path = get_random_music()
#     final_audio_source = audio_path # Default to just voice

#     if music_path:
#         print(f"      🎵 Mixing with: {os.path.basename(music_path)}")
#         norm_voice = "assets/temp/norm_voice.wav"
#         norm_music = "assets/temp/norm_music.wav"
#         mixed_wav = "assets/temp/mixed_audio.wav"

#         # 1. Normalize Voice (Force 44.1kHz Stereo WAV)
#         cmd_v = [ffmpeg, '-y', '-i', audio_path, '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', norm_voice]
#         run_ffmpeg(cmd_v)

#         # 2. Normalize Music (Force 44.1kHz Stereo WAV)
#         cmd_m = [ffmpeg, '-y', '-i', music_path, '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', norm_music]
#         run_ffmpeg(cmd_m)

#         # 3. Mix (Voice 100%, Music 20%)
#         cmd_mix = [
#             ffmpeg, '-y',
#             '-i', norm_voice, 
#             '-i', norm_music,
#             '-filter_complex', '[1:a]volume=0.2[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[a]',
#             '-map', '[a]',
#             '-c:a', 'pcm_s16le', # Output uncompressed WAV for safety
#             mixed_wav
#         ]
        
#         if run_ffmpeg(cmd_mix):
#             final_audio_source = mixed_wav
#             print("      ✅ Audio Mix Created Successfully.")
#         else:
#             print("      ⚠️ Mixing failed. Falling back to voice only.")

#     # --- PART 3: FINAL MERGE ---
#     print("   3. Merging Video & Audio...")
    
#     cmd_merge = [
#         ffmpeg, '-y',
#         '-i', temp_silent,       # Input 0: Video
#         '-i', final_audio_source, # Input 1: Mixed Audio
#         '-c:v', 'copy',          # Copy video stream (don't re-encode)
#         '-c:a', 'aac',           # Encode audio to AAC
#         '-b:a', '192k',          # High bitrate
#         '-map', '0:v:0',         # Map video from file 0
#         '-map', '1:a:0',         # Map audio from file 1
#         '-shortest',             # Stop when video ends
#         output_path
#     ]
    
#     if run_ffmpeg(cmd_merge):
#         print(f"✅ SUCCESS! Final video saved to: {output_path}")
#     else:
#         print("❌ CRITICAL: Final merge failed.")

#     # Cleanup (Optional - you can comment this out if you want to inspect files)
#     try:
#         if os.path.exists(temp_silent): os.remove(temp_silent)
#         if os.path.exists("assets/temp/norm_voice.wav"): os.remove("assets/temp/norm_voice.wav")
#         if os.path.exists("assets/temp/norm_music.wav"): os.remove("assets/temp/norm_music.wav")
#         if os.path.exists("assets/temp/mixed_audio.wav"): os.remove("assets/temp/mixed_audio.wav")
#     except:
#         pass


# # import os
# # import json
# # import random
# # import subprocess
# # from moviepy.config import change_settings, get_setting

# # # --- 1. CONFIGURATION ---
# # # We force ImageMagick to be found
# IMAGEMAGICK_PATH = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe" 
# if os.path.exists(IMAGEMAGICK_PATH):
#     change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_PATH})

# # # --- 2. HOTFIX FOR PILLOW ---
# # import PIL.Image
# # if not hasattr(PIL.Image, 'ANTIALIAS'):
# #     PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# # from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# # # --- 3. STYLE SETTINGS ---
# # FONT = "Arial-Bold" 
# # FONT_SIZE = 80
# # FONT_COLOR = "white"
# # STROKE_COLOR = "black"
# # STROKE_WIDTH = 3

# # def get_random_music():
# #     """Finds a random music file in assets/music."""
# #     music_folder = "assets/music"
# #     if not os.path.exists(music_folder): return None
    
# #     valid_extensions = ('.mp3', '.wav', '.m4a')
# #     tracks = [f for f in os.listdir(music_folder) if f.lower().endswith(valid_extensions)]
    
# #     if not tracks: return None
# #     return os.path.join(music_folder, random.choice(tracks))

# # def normalize_audio(input_path, output_path):
# #     """
# #     CRITICAL FIX: Converts audio to 44.1kHz Stereo WAV.
# #     This prevents FFmpeg from crashing when mixing different audio types.
# #     """
# #     ffmpeg = get_setting("FFMPEG_BINARY")
# #     cmd = [
# #         ffmpeg, '-y', 
# #         '-i', input_path,
# #         '-ar', '44100',       # Force 44.1kHz sample rate
# #         '-ac', '2',           # Force Stereo (2 channels)
# #         '-c:a', 'pcm_s16le',  # Uncompressed WAV
# #         output_path
# #     ]
# #     # We suppress output logs unless it crashes
# #     subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# # def create_advanced_video(video_path, audio_path, timestamp_path, output_path):
# #     print("🎬 Starting Advanced Video Assembly...")

# #     if not os.path.exists(timestamp_path):
# #         print("❌ Error: Timestamps JSON not found.")
# #         return

# #     # --- PART A: PREPARE ASSETS ---
# #     print("   1. Preparing Assets...")
# #     video_clip = VideoFileClip(video_path)
# #     audio_clip = AudioFileClip(audio_path)
# #     music_path = get_random_music()

# #     if music_path:
# #         print(f"   🎵 Music Selected: {os.path.basename(music_path)}")
# #     else:
# #         print("   ⚠️ No music found. Video will have voice only.")

# #     with open(timestamp_path, 'r') as f:
# #         word_segments = json.load(f)

# #     # Resize/Crop to 9:16
# #     target_ratio = 9/16
# #     if video_clip.w / video_clip.h > target_ratio:
# #         video_clip = video_clip.crop(x1=video_clip.w/2 - (video_clip.h*target_ratio)/2, 
# #                                      width=video_clip.h*target_ratio, height=video_clip.h)
# #     video_clip = video_clip.resize(height=1920)

# #     # Loop Logic
# #     if audio_clip.duration > video_clip.duration:
# #         video_clip = video_clip.loop(duration=audio_clip.duration)
# #     else:
# #         video_clip = video_clip.subclip(0, audio_clip.duration)

# #     # Text Generation
# #     print("   2. Generating Text Overlays...")
# #     subtitle_clips = []
# #     for segment in word_segments:
# #         word = segment['word'].upper()
# #         # Ensure we don't crash on empty segments
# #         if not word: continue
        
# #         txt_clip = (TextClip(word, fontsize=FONT_SIZE, font=FONT, 
# #                              color=FONT_COLOR, stroke_color=STROKE_COLOR, stroke_width=STROKE_WIDTH)
# #                     .set_position('center')
# #                     .set_start(segment['start'])
# #                     .set_duration(segment['end'] - segment['start']))
# #         subtitle_clips.append(txt_clip)

# #     # Render Silent Video
# #     temp_silent = "assets/temp/temp_silent.mp4"
# #     if os.path.exists(temp_silent): os.remove(temp_silent)

# #     print(f"   3. Rendering Silent Video Layer (Please Wait)...")
# #     final = CompositeVideoClip([video_clip] + subtitle_clips)
# #     final.write_videofile(temp_silent, fps=30, codec="libx264", audio=False, preset="ultrafast", threads=4, logger=None)

# #     # --- PART B: THE ROBUST MIXER ---
# #     print(f"   4. 🔨 Mixing & Merging Audio...")
# #     ffmpeg = get_setting("FFMPEG_BINARY")
    
# #     try:
# #         final_audio_source = audio_path # Default to just voice

# #         if music_path:
# #             # 1. Normalize both inputs (The Magic Fix)
# #             norm_voice = "assets/temp/norm_voice.wav"
# #             norm_music = "assets/temp/norm_music.wav"
# #             mixed_audio = "assets/temp/mixed.wav"
            
# #             # Convert Voice & Music to identical formats
# #             normalize_audio(audio_path, norm_voice)
# #             normalize_audio(music_path, norm_music)
            
# #             # 2. Mix them
# #             # Volume: Music=15%, Voice=100%
# #             cmd_mix = [
# #                 ffmpeg, '-y', 
# #                 '-i', norm_voice, 
# #                 '-i', norm_music,
# #                 '-filter_complex', '[1:a]volume=0.15[bg];[0:a][bg]amix=inputs=2:duration=first[a]',
# #                 '-map', '[a]', 
# #                 mixed_audio
# #             ]
# #             subprocess.run(cmd_mix, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)
            
# #             # Success! Use the mixed file
# #             final_audio_source = mixed_audio
        
# #         # 3. Final Merge with Video
# #         cmd_merge = [
# #             ffmpeg, '-y', 
# #             '-i', temp_silent, 
# #             '-i', final_audio_source,
# #             '-c:v', 'copy',   # Copy video stream
# #             '-c:a', 'aac',    # Encode audio stream
# #             '-map', '0:v:0', 
# #             '-map', '1:a:0', 
# #             '-shortest',
# #             output_path
# #         ]
# #         subprocess.run(cmd_merge, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)
# #         print(f"✅ SUCCESS! Final video saved to: {output_path}")

# #     except subprocess.CalledProcessError as e:
# #         print(f"❌ FFmpeg Error: {e}")
# #     except Exception as e:
# #         print(f"❌ General Error: {e}")

# #     # Cleanup Temps
# #     temp_files = [temp_silent, "assets/temp/norm_voice.wav", "assets/temp/norm_music.wav", "assets/temp/mixed.wav"]
# #     for f in temp_files:
# #         if os.path.exists(f): 
# #             try: os.remove(f)
# #             except: pass



# # # import os
# # # import json
# # # import subprocess
# # # from moviepy.config import change_settings, get_setting

# # # # --- 1. CONFIGURATION ---
# # # IMAGEMAGICK_PATH = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe" 
# # # if os.path.exists(IMAGEMAGICK_PATH):
# # #     change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_PATH})

# # # # --- 2. HOTFIX FOR PILLOW ---
# # # import PIL.Image
# # # if not hasattr(PIL.Image, 'ANTIALIAS'):
# # #     PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# # # from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# # # # --- 3. STYLE SETTINGS ---
# # # FONT = "Arial-Bold" 
# # # FONT_SIZE = 80
# # # FONT_COLOR = "white"
# # # STROKE_COLOR = "black"
# # # STROKE_WIDTH = 3

# # # def create_advanced_video(video_path, audio_path, timestamp_path, output_path):
# # #     print("🎬 Starting Advanced Video Assembly...")

# # #     if not os.path.exists(timestamp_path):
# # #         print("❌ Error: Timestamps JSON not found.")
# # #         return

# # #     # --- PART A: VIDEO GENERATION (SILENT) ---
# # #     print("   1. Preparing Assets...")
# # #     video_clip = VideoFileClip(video_path)
# # #     audio_clip = AudioFileClip(audio_path)
    
# # #     with open(timestamp_path, 'r') as f:
# # #         word_segments = json.load(f)

# # #     # Resize/Crop
# # #     target_ratio = 9/16
# # #     if video_clip.w / video_clip.h > target_ratio:
# # #         video_clip = video_clip.crop(x1=video_clip.w/2 - (video_clip.h*target_ratio)/2, 
# # #                                      width=video_clip.h*target_ratio, 
# # #                                      height=video_clip.h)
# # #     video_clip = video_clip.resize(height=1920)

# # #     # Loop Logic
# # #     if audio_clip.duration > video_clip.duration:
# # #         video_clip = video_clip.loop(duration=audio_clip.duration)
# # #     else:
# # #         video_clip = video_clip.subclip(0, audio_clip.duration)
    
# # #     # Text Generation
# # #     print("   2. Generating Text Overlays...")
# # #     subtitle_clips = []
# # #     for segment in word_segments:
# # #         word = segment['word'].upper()
# # #         start = segment['start']
# # #         end = segment['end']
# # #         duration = end - start
        
# # #         txt_clip = (TextClip(word, fontsize=FONT_SIZE, font=FONT, 
# # #                              color=FONT_COLOR, stroke_color=STROKE_COLOR, stroke_width=STROKE_WIDTH)
# # #                     .set_position('center')
# # #                     .set_start(start)
# # #                     .set_duration(duration))
# # #         subtitle_clips.append(txt_clip)

# # #     # Render Silent Video
# # #     temp_silent = "assets/temp/temp_silent.mp4"
# # #     if os.path.exists(temp_silent):
# # #         os.remove(temp_silent)

# # #     print(f"   3. Rendering Silent Video Layer (Please Wait)...")
# # #     final = CompositeVideoClip([video_clip] + subtitle_clips)
# # #     final.write_videofile(
# # #         temp_silent, 
# # #         fps=30, 
# # #         codec="libx264", 
# # #         audio=False, 
# # #         preset="ultrafast", 
# # #         threads=4,
# # #         logger=None 
# # #     )

# # #     # --- PART B: DIRECT STREAM COPY (THE FIX) ---
# # #     print(f"   4. 🔨 Force-Merging Audio...")
    
# # #     ffmpeg_binary = get_setting("FFMPEG_BINARY")
    
# # #     cmd = [
# # #         ffmpeg_binary,
# # #         '-y',
# # #         '-i', temp_silent, # Input 0 (Video)
# # #         '-i', audio_path,  # Input 1 (Audio)
# # #         '-c:v', 'copy',    # Copy Video Stream directly
# # #         '-c:a', 'copy',    # <--- CRITICAL FIX: Copy Audio Stream (No Encode)
# # #         '-map', '0:v:0',   # Map Video from Input 0
# # #         '-map', '1:a:0',   # Map Audio from Input 1
# # #         '-shortest',
# # #         output_path
# # #     ]
    
# # #     try:
# # #         subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
# # #         print(f"✅ SUCCESS! Final video saved to: {output_path}")
# # #     except subprocess.CalledProcessError as e:
# # #         print(f"❌ FFmpeg Merge Failed: {e}")

# # #     # Cleanup
# # #     if os.path.exists(temp_silent):
# # #         os.remove(temp_silent)

# # # if __name__ == "__main__":
# # #     VIDEO = "assets/temp/background.mp4"
# # #     AUDIO = "assets/temp/base_audio.mp3"
# # #     TIMESTAMPS = "assets/temp/base_audio.json"
# # #     OUTPUT = "assets/output/final_short.mp4"

# # #     os.makedirs("assets/output", exist_ok=True)
    
# # #     try:
# # #         create_advanced_video(VIDEO, AUDIO, TIMESTAMPS, OUTPUT)
# # #     except Exception as e:
# # #         print(f"❌ Editor Error: {e}")