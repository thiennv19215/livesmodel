import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "LivestreamAgent AI"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./livestream.db"
    
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
        env_file = ".env"
        extra = "ignore"

settings = Settings()
