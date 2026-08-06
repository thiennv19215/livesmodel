import re
import time
import unicodedata
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Sales keywords list matching app-64 spec
SALES_KEYWORDS = [
    "gia", "bao nhieu", "ship", "freeship", "mua", "chot", "dat hang",
    "size", "mau", "con hang", "het hang", "tu van", "cong dung",
    "thanh phan", "cach dung", "sale", "giam", "xin link", "inbox", "?"
]

GREETING_WORDS = {"hi", "hello", "ok", "haha", "chao shop", "alo", "alô", "1", "2", "quá đẹp", "đẹp"}

def strip_accents(text: str) -> str:
    """Removes Vietnamese accents for accent-insensitive matching."""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.replace('đ', 'd').replace('Đ', 'D')

class TriggerEngine:
    def __init__(self, dedup_window_seconds: int = 45, global_cooldown_seconds: float = 2.0, user_cooldown_seconds: float = 30.0):
        self.dedup_window_seconds = dedup_window_seconds
        self.global_cooldown_seconds = global_cooldown_seconds
        self.user_cooldown_seconds = user_cooldown_seconds

        # Deduplication cache: {comment_hash: timestamp}
        self.recent_comments: Dict[str, float] = {}

        # Cooldown trackers
        self.last_global_processed_time: float = 0.0
        self.user_last_processed_time: Dict[str, float] = {}

        # Event rules state
        self.event_rules = {
            "chat": {"enabled": True, "actionType": "voice_tts"},
            "gift": {"enabled": True, "actionType": "voice_tts"},
            "like": {"enabled": False, "actionType": "voice_tts"},
            "follow": {"enabled": True, "actionType": "voice_tts"},
            "share": {"enabled": True, "actionType": "voice_tts"}
        }

    def clean_cache(self, current_time: float):
        """Purges entries older than the deduplication and cooldown windows."""
        expired_dedup = [k for k, v in self.recent_comments.items() if current_time - v > self.dedup_window_seconds]
        for k in expired_dedup:
            del self.recent_comments[k]

        expired_user = [k for k, v in self.user_last_processed_time.items() if current_time - v > self.user_cooldown_seconds]
        for k in expired_user:
            del self.user_last_processed_time[k]

    def evaluate_comment(self, user_name: str, user_id: str, comment: str) -> Tuple[bool, str, str]:
        """
        9-Step Comment Filter Pipeline matching app-64 specification.
        Returns (should_process, cleaned_text, reason)
        """
        current_time = time.time()
        self.clean_cache(current_time)

        # Check Global Cooldown (2s)
        if current_time - self.last_global_processed_time < self.global_cooldown_seconds:
            return False, comment, "global_cooldown_active"

        # Check Per-User Cooldown (30s)
        if user_id in self.user_last_processed_time:
            if current_time - self.user_last_processed_time[user_id] < self.user_cooldown_seconds:
                return False, comment, "user_cooldown_active"

        # Step 1 & 2: Lowercase & Strip Accents
        lower_raw = comment.strip().lower()
        no_accents = strip_accents(lower_raw)

        # Step 3: Remove URLs & Punctuation
        no_urls = re.sub(r'https?://\S+|www\.\S+', '', no_accents)
        cleaned_words = re.sub(r'[^\w\s\?]', '', no_urls).strip()

        # Step 4: Skip empty, emoji-only, or very short comments (< 2 chars)
        if not cleaned_words or len(cleaned_words) < 2:
            return False, comment, "comment_too_short_or_empty"

        # Step 5: Skip simple social greetings
        if cleaned_words in GREETING_WORDS:
            return False, comment, "trivial_greeting"

        # Step 6: 45-second Duplicate Window Check
        comment_key = f"{user_id}:{cleaned_words}"
        if comment_key in self.recent_comments:
            if current_time - self.recent_comments[comment_key] <= self.dedup_window_seconds:
                return False, comment, "duplicate_comment_suppressed"

        # Record this comment in deduplication and cooldown tracking
        self.recent_comments[comment_key] = current_time
        self.user_last_processed_time[user_id] = current_time
        self.last_global_processed_time = current_time

        return True, cleaned_words, "accepted"
