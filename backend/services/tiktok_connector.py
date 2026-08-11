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
    from TikTokLive.events import (
        CommentEvent,
        ConnectEvent,
        DisconnectEvent,
        FollowEvent,
        GiftEvent,
        LikeEvent,
        LiveEndEvent,
        ShareEvent,
    )
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
        self.client_task = None
        self.connection_ready = None
        self.connection_error = None

    async def _run_client(self):
        try:
            await self.client.start()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.connection_error = e
            logger.error(f"TikTok Live connection stopped: {e}")
        finally:
            self.is_connected = False
            if self.connection_ready:
                self.connection_ready.set()

    async def connect(self, username: str):
        if self.is_connected or self.client_task or self.simulation_task:
            await self.disconnect()
        self.username = username
        if TIKTOK_AVAILABLE and username and not username.startswith("mock_"):
            try:
                self.client = TikTokLiveClient(unique_id=username)
                self.connection_ready = asyncio.Event()
                self.connection_error = None

                @self.client.on(ConnectEvent)
                async def on_connect(_event: ConnectEvent):
                    self.is_connected = True
                    self.connection_ready.set()

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
                    # Streakable gifts emit intermediate events. Process only the
                    # final event so a combo is thanked exactly once.
                    if getattr(event, "streaking", False):
                        return
                    if self.event_callback:
                        await self.event_callback({
                            "type": "gift",
                            "user_name": event.user.nickname or event.user.unique_id,
                            "user_id": event.user.unique_id,
                            "gift_name": event.gift.name,
                            "repeat_count": event.repeat_count,
                            "repeat_end": bool(getattr(event, "repeat_end", True)),
                        })

                @self.client.on(LikeEvent)
                async def on_like(event: LikeEvent):
                    if self.event_callback:
                        await self.event_callback({
                            "type": "like",
                            "user_name": event.user.nickname or event.user.unique_id,
                            "user_id": event.user.unique_id,
                            "like_count": event.total_likes
                        })

                @self.client.on(FollowEvent)
                async def on_follow(event: FollowEvent):
                    if self.event_callback:
                        await self.event_callback({
                            "type": "follow",
                            "user_name": event.user.nickname or event.user.unique_id,
                            "user_id": event.user.unique_id,
                        })

                @self.client.on(ShareEvent)
                async def on_share(event: ShareEvent):
                    if self.event_callback:
                        await self.event_callback({
                            "type": "share",
                            "user_name": event.user.nickname or event.user.unique_id,
                            "user_id": event.user.unique_id,
                        })

                @self.client.on(DisconnectEvent)
                async def on_disconnect(_event: DisconnectEvent):
                    if self.event_callback:
                        await self.event_callback({"type": "disconnect"})

                @self.client.on(LiveEndEvent)
                async def on_live_end(_event: LiveEndEvent):
                    if self.event_callback:
                        await self.event_callback({"type": "live_end"})

                if MemberEvent:
                    @self.client.on(MemberEvent)
                    async def on_member(event: MemberEvent):
                        if self.event_callback:
                            await self.event_callback({
                                "type": "member",
                                "user_name": event.user.nickname or event.user.unique_id,
                                "user_id": event.user.unique_id
                            })

                self.client_task = asyncio.create_task(self._run_client())
                try:
                    await asyncio.wait_for(self.connection_ready.wait(), timeout=15.0)
                except asyncio.TimeoutError:
                    logger.error(f"Timed out connecting to TikTok Live room @{username}")
                    await self.disconnect()
                    return False

                if self.connection_error or not self.is_connected:
                    await self.disconnect()
                    return False

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
        if self.client_task and not self.client_task.done():
            self.client_task.cancel()
            try:
                await self.client_task
            except asyncio.CancelledError:
                pass
        self.client_task = None
        self.client = None
        self.connection_ready = None
        self.connection_error = None
        if self.simulation_task:
            self.simulation_task.cancel()
            try:
                await self.simulation_task
            except asyncio.CancelledError:
                pass
        self.simulation_task = None
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
