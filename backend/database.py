from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    keywords = Column(Text, default="") # Comma separated
    price = Column(String(100), default="")
    selling_points = Column(Text, default="")
    custom_script = Column(Text, default="")
    product_link = Column(String(500), default="")
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TriggerRule(Base):
    __tablename__ = "trigger_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    event_type = Column(String(50), default="chat") # chat, gift, like, follow, share
    keywords = Column(Text, default="") # Comma separated matching
    blacklist = Column(Text, default="")
    action_type = Column(String(50), default="ai_reply") # ai_reply, static_reply, product_pin
    reply_template = Column(Text, default="")
    cooldown_seconds = Column(Integer, default=5)
    enabled = Column(Boolean, default=True)

class LiveLog(Base):
    __tablename__ = "live_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String(50))
    user_name = Column(String(255))
    user_message = Column(Text)
    ai_reply = Column(Text)
    status = Column(String(50), default="processed") # processed, ignored, error

class RuntimeSetting(Base):
    __tablename__ = "runtime_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, default="", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class InteractionJob(Base):
    __tablename__ = "interaction_jobs"

    id = Column(String(36), primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(String(255), default="")
    user_name = Column(String(255), default="")
    user_message = Column(Text, default="")
    status = Column(String(50), nullable=False, default="received", index=True)
    decision_reason = Column(String(255), default="")
    ai_reply = Column(Text, default="")
    audio_url = Column(String(500), default="")
    playback_id = Column(String(36), default="")
    playback_owner = Column(String(50), default="")
    error = Column(Text, default="")
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

class SceneSetting(Base):
    __tablename__ = "scene_settings"

    id = Column(Integer, primary_key=True, index=True)
    aspect_ratio = Column(String(20), default="9:16")
    avatar_x = Column(Integer, default=50) # %
    avatar_y = Column(Integer, default=65) # %
    avatar_scale = Column(Integer, default=100) # %
    avatar_visible = Column(Boolean, default=True)
    avatar_style = Column(String(50), default="default") # default, anime, corporate, cyberpunk
    avatar_mode = Column(String(20), default="builtin") # builtin, video
    avatar_media_url = Column(String(500), default="")
    avatar_fit = Column(String(20), default="contain") # contain, cover
    video_media_url = Column(String(500), default="")
    video_name = Column(String(255), default="")
    video_x = Column(Integer, default=50) # %
    video_y = Column(Integer, default=50) # %
    video_width = Column(Integer, default=100) # %
    video_height = Column(Integer, default=100) # %
    video_rotation = Column(Integer, default=0) # degrees
    video_fit = Column(String(20), default="contain") # contain, cover
    video_visible = Column(Boolean, default=True)
    caption_x = Column(Integer, default=50) # %
    caption_y = Column(Integer, default=88) # %
    caption_visible = Column(Boolean, default=True)
    caption_font_size = Column(Integer, default=18)
    caption_text_color = Column(String(20), default="#ffffff")
    caption_bg_color = Column(String(20), default="rgba(15, 23, 42, 0.85)")
    caption_preset = Column(String(50), default="capcut_yellow")
    bg_mode = Column(String(30), default="transparent") # transparent, chroma_green, dark_studio

def init_db():
    Base.metadata.create_all(bind=engine)
    # create_all does not add new columns to an existing SQLite database.
    # Keep this lightweight migration here until the project adopts Alembic.
    scene_columns = {column["name"] for column in inspect(engine).get_columns("scene_settings")}
    missing_columns = {
        "avatar_mode": "VARCHAR(20) DEFAULT 'builtin'",
        "avatar_media_url": "VARCHAR(500) DEFAULT ''",
        "avatar_fit": "VARCHAR(20) DEFAULT 'contain'",
        "avatar_visible": "BOOLEAN DEFAULT 1",
        "caption_visible": "BOOLEAN DEFAULT 1",
        "video_media_url": "VARCHAR(500) DEFAULT ''",
        "video_name": "VARCHAR(255) DEFAULT ''",
        "video_x": "INTEGER DEFAULT 50",
        "video_y": "INTEGER DEFAULT 50",
        "video_width": "INTEGER DEFAULT 100",
        "video_height": "INTEGER DEFAULT 100",
        "video_rotation": "INTEGER DEFAULT 0",
        "video_fit": "VARCHAR(20) DEFAULT 'contain'",
        "video_visible": "BOOLEAN DEFAULT 1",
    }
    with engine.begin() as connection:
        for column_name, definition in missing_columns.items():
            if column_name not in scene_columns:
                connection.execute(text(f"ALTER TABLE scene_settings ADD COLUMN {column_name} {definition}"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
