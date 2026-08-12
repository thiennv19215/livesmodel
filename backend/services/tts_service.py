import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import edge_tts

logger = logging.getLogger(__name__)

TEMP_AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "audio")
AUDIO_TTL_SECONDS = 600


class TTSService:
    """Single-responsibility TTS adapter used by InteractionQueueService.

    Queue orchestration belongs to InteractionQueueService. This service only
    synthesizes speech files and manages their lifecycle.
    """

    def __init__(
        self,
        voice: str = "vi-VN-HoaiMyNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> None:
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
        self.cleanup_tasks: set[asyncio.Task] = set()

    def cleanup_temp_files(self) -> None:
        """Remove speech files left behind by an earlier process."""
        audio_root = Path(TEMP_AUDIO_DIR).resolve()
        for path in audio_root.glob("speech_*.mp3"):
            try:
                if path.resolve().parent == audio_root:
                    path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Unable to remove temporary TTS file '%s': %s", path, exc)

    async def shutdown(self) -> None:
        tasks = list(self.cleanup_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.cleanup_tasks.clear()
        self.cleanup_temp_files()

    async def _delete_audio_later(self, filepath: str) -> None:
        """Remove generated speech after clients have had time to play it."""
        try:
            await asyncio.sleep(AUDIO_TTL_SECONDS)
            if os.path.exists(filepath):
                os.remove(filepath)
        except asyncio.CancelledError:
            raise
        except OSError as exc:
            logger.warning("Unable to remove expired TTS file '%s': %s", filepath, exc)

    async def generate_speech(self, text: str) -> Optional[str]:
        """Synthesize text to an MP3 and return its relative static URL."""
        filename = f"speech_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(TEMP_AUDIO_DIR, filename)

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
            )
            await communicate.save(filepath)
            cleanup_task = asyncio.create_task(self._delete_audio_later(filepath))
            self.cleanup_tasks.add(cleanup_task)
            cleanup_task.add_done_callback(self.cleanup_tasks.discard)
            return f"/static/audio/{filename}"
        except Exception as exc:
            logger.error("TTS generation error: %s", exc)
            return None
