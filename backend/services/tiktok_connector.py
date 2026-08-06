import asyncio
import logging
import random
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Try importing TikTokLive
TIKTOK_AVAILABLE = False
MemberEvent = None
try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import CommentEvent, GiftEvent, LikeEvent, FollowEvent, ShareEvent
    try:
        from TikTokLive.events import MemberEvent
    except ImportError:
        MemberEvent = None
    TIKTOK_AVAILABLE = True
except ImportError:
    logger.warning("TikTokLive library not installed or failed to import. Simulation mode available.")

MOCK_COMMENTS = [
    ("Hoa Nguyễn", "Áo này có size L không shop ơi?"),
    ("Minh Trí", "Giá bao nhiêu vậy ạ?"),
    ("Thanh Hà", "Shop cho mình coi cận chất vải với"),
    ("Quốc Bảo", "Ship về Hà Nội mất bao lâu ạ?"),
    ("Trang Phạm", "Có màu đen không ạ?"),
    ("Đức Anh", "Đã chốt 1 em nha shop!")
]

MOCK_JOIN_USERS = [
    "Linh Trần", "Hoàng Nam", "Ngọc Mai", "Anh Tuấn", 
    "Thu Hà", "Hải Đăng", "Hồng Ngọc", "Bảo Long"
]

class TikTokConnector:
    def __init__(self, username: str = "", event_callback: Optional[Callable] = None):
        self.username = username
        self.event_callback = event_callback
        self.client = None
        self.is_connected = False
        self.simulation_task = None

    async def connect(self, username: str):
        self.username = username
        if TIKTOK_AVAILABLE and username and not username.startswith("mock_"):
            try:
                self.client = TikTokLiveClient(unique_id=username)

                @self.client.on(CommentEvent)
                async def on_comment(event: CommentEvent):
                    if self.event_callback:
                        await self.event_callback({
                            "type": "chat",
                            "user_name": event.user.nickname or event.user.unique_id,
                            "comment": event.comment,
                            "user_id": event.user.unique_id
                        })

                @self.client.on(GiftEvent)
                async def on_gift(event: GiftEvent):
                    if self.event_callback:
                        await self.event_callback({
                            "type": "gift",
                            "user_name": event.user.nickname or event.user.unique_id,
                            "gift_name": event.gift.name,
                            "repeat_count": event.repeat_count
                        })

                @self.client.on(LikeEvent)
                async def on_like(event: LikeEvent):
                    if self.event_callback:
                        await self.event_callback({
                            "type": "like",
                            "user_name": event.user.nickname or event.user.unique_id,
                            "like_count": event.total_likes
                        })

                if MemberEvent:
                    @self.client.on(MemberEvent)
                    async def on_member(event: MemberEvent):
                        if self.event_callback:
                            await self.event_callback({
                                "type": "member",
                                "user_name": event.user.nickname or event.user.unique_id,
                                "user_id": event.user.unique_id
                            })

                asyncio.create_task(self.client.start())
                self.is_connected = True
                logger.info(f"Connected to TikTok Live room @{username}")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to TikTok Live room @{username}: {e}")
                self.is_connected = False
                return False
        else:
            # Fallback to simulation mode
            return await self.start_simulation()

    async def start_simulation(self):
        self.is_connected = True
        if self.simulation_task:
            self.simulation_task.cancel()

        self.simulation_task = asyncio.create_task(self._run_simulation())
        logger.info("TikTok simulation mode started.")
        return True

    async def disconnect(self):
        self.is_connected = False
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
        if self.simulation_task:
            self.simulation_task.cancel()
        logger.info("Disconnected from TikTok Live.")

    async def _run_simulation(self):
        while self.is_connected:
            await asyncio.sleep(random.randint(5, 10))
            if not self.is_connected:
                break
            
            if not self.event_callback:
                continue

            # Randomize between simulated chat comment (60%) and member join event (40%)
            event_choice = random.choices(["chat", "member"], weights=[0.6, 0.4])[0]
            if event_choice == "chat":
                user_name, comment = random.choice(MOCK_COMMENTS)
                await self.event_callback({
                    "type": "chat",
                    "user_name": user_name,
                    "comment": comment,
                    "user_id": f"sim_{random.randint(100, 999)}"
                })
            else:
                user_name = random.choice(MOCK_JOIN_USERS)
                await self.event_callback({
                    "type": "member",
                    "user_name": user_name,
                    "user_id": f"sim_{random.randint(100, 999)}"
                })

