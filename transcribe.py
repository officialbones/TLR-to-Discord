"""Audio transcription via Whisper-compatible API."""

import logging
import tempfile
import time
import os
import requests
from config import TRANSCRIPTION_URL
import db

logger = logging.getLogger(__name__)

# Map MIME types to file extensions
MIME_TO_EXT = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/webm": ".webm",
}


def _get_extension(filename: str, mime_type: str) -> str:
    """Determine file extension from filename or MIME type."""
    if filename:
        _, ext = os.path.splitext(filename)
        if ext:
            return ext
    return MIME_TO_EXT.get(mime_type, ".wav")


def transcribe_audio(audio_bytes: bytes, filename: str, mime_type: str) -> str:
    """
    Transcribe audio bytes via the Whisper-compatible API.
    Retries up to 3 times on server errors.
    """
    ext = _get_extension(filename, mime_type)
    max_retries = 3

    for attempt in range(max_retries):
        tmp_path = None
        try:
            # Write audio to temp file
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            # Send to transcription API
            with open(tmp_path, "rb") as f:
                files = {"file": (f"audio{ext}", f, mime_type or "audio/wav")}
                data = {"model": "whisper-1"}
                response = requests.post(
                    TRANSCRIPTION_URL,
                    files=files,
                    data=data,
                    timeout=120,
                )

            if response.status_code == 200:
                result = response.json()
                transcript = result.get("text", "").strip()
                if transcript:
                    logger.info(f"Transcription successful ({len(transcript)} chars)")
                return transcript

            if response.status_code >= 500:
                logger.warning(
                    f"Transcription server error (attempt {attempt + 1}/{max_retries}): "
                    f"{response.status_code} {response.text[:200]}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
                continue

            # Client error - don't retry
            logger.error(
                f"Transcription failed: {response.status_code} {response.text[:200]}"
            )
            return ""

        except requests.exceptions.Timeout:
            logger.warning(f"Transcription timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
        except requests.exceptions.ConnectionError:
            logger.warning(f"Transcription connection error (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    logger.error("Transcription failed after all retries")
    return ""


def get_or_create_transcript(alert: dict) -> str:
    """
    Return existing transcript if available, otherwise transcribe the audio.
    Updates the calls table with the new transcript.
    """
    transcript = alert.get("transcript", "")
    status = alert.get("transcriptionStatus", "pending")

    # Use existing transcript if it's not empty and not still pending
    if transcript and status != "pending":
        logger.debug(f"Using existing transcript for callId={alert['callId']}")
        return transcript

    # Need to transcribe
    logger.info(f"Transcribing audio for callId={alert['callId']}...")
    try:
        audio_bytes, filename, mime_type = db.fetch_call_audio(alert["callId"])
        if not audio_bytes:
            logger.warning(f"No audio data for callId={alert['callId']}")
            return ""

        transcript = transcribe_audio(audio_bytes, filename, mime_type)
        if transcript:
            db.update_call_transcript(alert["callId"], transcript)
        return transcript

    except Exception as e:
        logger.error(f"Failed to transcribe callId={alert['callId']}: {e}")
        return ""
