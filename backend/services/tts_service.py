import os
import asyncio
import uuid
import logging
from typing import Optional, Callable
import edge_tts

logger = logging.getLogger(__name__)

TEMP_AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "audio")

class TTSService:
    def __init__(self, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
        self.queue = asyncio.Queue()
        self.is_processing = False
        self.on_audio_generated: Optional[Callable] = None

    async def generate_speech(self, text: str) -> Optional[str]:
        """
        Synthesizes text to an MP3 file using Edge TTS.
        Returns the relative URL path to the generated audio file.
        """
        filename = f"speech_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(TEMP_AUDIO_DIR, filename)

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            await communicate.save(filepath)
            relative_url = f"/static/audio/{filename}"
            return relative_url
        except Exception as e:
            logger.error(f"TTS generation error for text '{text}': {e}")
            return None

    async def enqueue(self, text: str, user_name: str = ""):
        """
        Adds text to the TTS queue.
        """
        await self.queue.put({"text": text, "user_name": user_name})

    async def start_queue_worker(self, broadcast_callback: Callable):
        """
        Runs continuously to process items in the speech queue sequentially.
        """
        self.is_processing = True
        while self.is_processing:
            try:
                item = await self.queue.get()
                text = item["text"]
                user_name = item["user_name"]

                audio_url = await self.generate_speech(text)
                if audio_url:
                    await broadcast_callback({
                        "type": "tts_play",
                        "text": text,
                        "user_name": user_name,
                        "audio_url": audio_url
                    })
                    # Estimate audio playback delay (roughly 4 words per second + buffer)
                    duration = max(3.0, len(text.split()) / 3.5)
                    await asyncio.sleep(duration)
                
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in TTS queue worker: {e}")
                await asyncio.sleep(1)
