from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime
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

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
