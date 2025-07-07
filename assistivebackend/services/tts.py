from gtts import gTTS
from pydub import AudioSegment
from pathlib import Path
import time
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_tts_audio(text: str, custom_filename=None) -> str:
    try:
        timestamp = int(time.time() * 1000)
        audio_dir = Path("static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Use custom filename if provided, otherwise use timestamp
        if custom_filename:
            audio_filename = custom_filename
        else:
            audio_filename = f"description_{timestamp}.mp3"
            
        audio_path = audio_dir / audio_filename
        temp_path = audio_dir / f"temp_{timestamp}.mp3"

        logger.info(f"Generating TTS audio for text: '{text}' to {audio_path}")

        # Generate basic TTS audio
        tts = gTTS(text=text, lang='en')
        tts.save(str(temp_path))
        logger.info(f"Saved temp audio file to {temp_path}")

        # Verify temp file exists
        if not temp_path.exists():
            logger.error(f"Failed to save temp audio file at {temp_path}")
            return None

        # Speed up the audio
        try:
            sound = AudioSegment.from_file(str(temp_path))
            faster_sound = sound.speedup(playback_speed=1.5)
            faster_sound.export(str(audio_path), format="mp3")
            logger.info(f"Exported final audio file to {audio_path}")
        except Exception as e:
            logger.error(f"Error processing audio with pydub: {e}")
            # If pydub fails, just use the original file
            import shutil
            shutil.copy(str(temp_path), str(audio_path))
            logger.info(f"Copied temp file to final location as fallback")

        # Verify final file exists and has content
        if not audio_path.exists():
            logger.error(f"Final audio file does not exist at {audio_path}")
            return None
            
        if audio_path.stat().st_size == 0:
            logger.error(f"Final audio file is empty at {audio_path}")
            return None

        # Clean up temp file
        try:
            os.remove(str(temp_path))
            logger.info(f"Removed temp file {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temp file: {e}")

        audio_url = f"/static/audio/{audio_path.name}"
        logger.info(f"Returning audio URL: {audio_url}")
        return audio_url
    except Exception as e:
        logger.exception(f"TTS generation error: {e}")
        return None