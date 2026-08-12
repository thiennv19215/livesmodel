import asyncio
import logging
from typing import Any, Dict, Optional

from database import LiveLog
from services.product_matcher import ProductMatcher

logger = logging.getLogger(__name__)


class InteractionOrchestrator:
    def __init__(
        self,
        *,
        session_factory,
        trigger_engine,
        ai_service,
        interaction_queue,
        live_ws_manager,
        ai_timeout_seconds: float = 60.0,
    ):
        self.session_factory = session_factory
        self.trigger_engine = trigger_engine
        self.ai_service = ai_service
        self.interaction_queue = interaction_queue
        self.live_ws_manager = live_ws_manager
        self.ai_timeout_seconds = ai_timeout_seconds
        self._tiktok_username_provider = lambda: ""

    def set_tiktok_username_provider(self, provider) -> None:
        self._tiktok_username_provider = provider

    async def handle(self, event: Dict[str, Any]):
        logger.info("Incoming TikTok Event: %s", event)
        event_type = event.get("type", "chat")
        user_name = event.get("user_name", "Khán giả")
        user_id = event.get("user_id", user_name)

        await self.live_ws_manager.broadcast({"type": "raw_event", "data": event})

        if event_type in {"disconnect", "live_end"}:
            await self.live_ws_manager.broadcast({
                "type": "tiktok_lifecycle",
                "data": {"state": event_type, "username": self._tiktok_username_provider()},
            })
            return None

        user_message = self._build_user_message(event_type, event)
        job = await self.interaction_queue.create_job(
            event_type=event_type,
            user_id=str(user_id),
            user_name=user_name,
            user_message=user_message,
        )
        if job["status"] == "skipped":
            return job

        if event_type == "chat":
            return await self._handle_chat(job, user_name, user_id, user_message)
        if event_type in {"gift", "like", "follow", "share", "member", "join"}:
            return await self._handle_social_event(job, event_type, user_name, user_message)
        return await self.interaction_queue.mark_skipped(job["id"], "unsupported_event_type")

    @staticmethod
    def _build_user_message(event_type: str, event: Dict[str, Any]) -> str:
        if event_type == "chat":
            return event.get("comment", "")
        if event_type == "gift":
            gift_name = event.get("gift_name", "quà tặng")
            repeat_count = event.get("repeat_count", 1)
            return f"Tặng {gift_name} x{repeat_count}"
        if event_type in {"member", "join"}:
            return "Vừa vào phòng livestream"
        return f"Sự kiện: {event_type}"

    async def _handle_chat(self, job, user_name: str, user_id: str, comment: str):
        should_process, cleaned_comment, reason = self.trigger_engine.evaluate_comment(
            user_name, user_id, comment
        )
        if not should_process:
            logger.info("Comment from '%s' filtered out. Reason: %s", user_name, reason)
            skipped = await self.interaction_queue.mark_skipped(job["id"], reason)
            await self.live_ws_manager.broadcast({
                "type": "event_filtered",
                "job_id": skipped["id"],
                "user_name": user_name,
                "comment": comment,
                "reason": reason,
            })
            return skipped

        await self.interaction_queue.mark_ai_processing(job["id"])
        db = self.session_factory()
        try:
            matcher = ProductMatcher(db, score_threshold=160)
            product, score = matcher.match_comment(cleaned_comment)
            product_ctx: Optional[str] = None
            if product:
                product_ctx = (
                    f"Sản phẩm: {product.name}, Giá: {product.price}. "
                    f"Điểm nổi bật: {product.selling_points}."
                )
                if product.custom_script:
                    product_ctx += f" Kịch bản tư vấn ưu tiên: {product.custom_script}."

            ai_reply = await asyncio.wait_for(
                self.ai_service.generate_response(
                    user_name, cleaned_comment, product_ctx, event_type="chat"
                ),
                timeout=self.ai_timeout_seconds,
            )
            db.add(LiveLog(
                event_type="chat",
                user_name=user_name,
                user_message=comment,
                ai_reply=ai_reply,
                status="processed",
            ))
            db.commit()

            await self.live_ws_manager.broadcast({
                "type": "ai_response",
                "job_id": job["id"],
                "user_name": user_name,
                "user_message": comment,
                "ai_reply": ai_reply,
                "matched_product": product.name if product else None,
                "match_score": score,
            })
            return await self.interaction_queue.set_ai_reply_and_enqueue(job["id"], ai_reply)
        except Exception as exc:
            reason = "ai_timeout" if isinstance(exc, asyncio.TimeoutError) else str(exc)
            return await self.interaction_queue.mark_error(job["id"], reason)
        finally:
            db.close()

    async def _handle_social_event(self, job, event_type: str, user_name: str, user_message: str):
        rule = self.trigger_engine.event_rules.get(event_type)
        if rule and not rule.get("enabled", True):
            return await self.interaction_queue.mark_skipped(job["id"], "event_disabled")

        try:
            await self.interaction_queue.mark_ai_processing(job["id"])
            ai_reply = await asyncio.wait_for(
                self.ai_service.generate_response(user_name, "", event_type=event_type),
                timeout=self.ai_timeout_seconds,
            )
            db = self.session_factory()
            try:
                db.add(LiveLog(
                    event_type=event_type,
                    user_name=user_name,
                    user_message=user_message,
                    ai_reply=ai_reply,
                    status="processed",
                ))
                db.commit()
            finally:
                db.close()

            await self.live_ws_manager.broadcast({
                "type": "ai_response",
                "job_id": job["id"],
                "user_name": user_name,
                "user_message": user_message,
                "ai_reply": ai_reply,
            })
            return await self.interaction_queue.set_ai_reply_and_enqueue(job["id"], ai_reply)
        except Exception as exc:
            reason = "ai_timeout" if isinstance(exc, asyncio.TimeoutError) else str(exc)
            return await self.interaction_queue.mark_error(job["id"], reason)
