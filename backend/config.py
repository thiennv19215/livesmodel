from pathlib import Path
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    APP_NAME: str = "LivestreamAgent AI"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'livestream.db').as_posix()}"
    
    # TikTok Default
    DEFAULT_TIKTOK_USERNAME: str = ""
    
    # LLM Settings
    DEFAULT_LLM_PROVIDER: str = "openai" # openai, ollama, openrouter
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    
    # TTS Settings
    TTS_PROVIDER: str = "edge-tts" # edge-tts, http, custom
    EDGE_TTS_VOICE: str = "vi-VN-HoaiMyNeural" # Vietnamese female voice default
    EDGE_TTS_RATE: str = "+0%"
    EDGE_TTS_PITCH: str = "+0Hz"
    
    class Config:
        env_file = str(BACKEND_DIR / ".env")
        extra = "ignore"

settings = Settings()
