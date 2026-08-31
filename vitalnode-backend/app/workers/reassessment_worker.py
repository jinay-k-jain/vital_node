"""
Reassessment Background Worker.

Every 60 seconds:
1. Find all waiting patients whose reassessment timer has expired
2. For each: recalculate time_in_queue_mins, delta_hr, delta_spo2
3. Run process_patient() through the ML engine
4. Push updated queue to all WebSocket clients

This is the real-time continuous triage loop described in the ML spec.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.db.database import AsyncSessionLocal
from app.services.reassessment_service import check_and_notify_overdue
from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_once() -> int:
    """Run one cycle: check overdue timers + notify + broadcast queue."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            count = await check_and_notify_overdue(session)

    # Broadcast updated queue to all WebSocket clients after processing
    try:
        from app.api.v1.websocket import broadcast_queue_update
        await broadcast_queue_update()
    except Exception as exc:
        logger.error("websocket_broadcast_error", error=str(exc))

    if count:
        logger.info("reassessment_cycle_complete", overdue_notifications=count)
    return count


async def run_loop(interval_seconds: int = 60) -> None:
    """
    Continuous background loop.
    Fires every `interval_seconds` (default 60s = 1 minute).
    Started automatically on application startup via main.py lifespan.
    """
    logger.info("reassessment_worker_started", interval_seconds=interval_seconds)
    while True:
        try:
            await run_once()
        except Exception as exc:
            logger.error("reassessment_worker_error", error=str(exc))
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_loop(interval_seconds=30))
