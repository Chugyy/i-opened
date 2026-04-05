"""Background scheduler — processes automation queue every 30 seconds."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_pool = None


async def _run_automation_queue():
    """Job callback — process pending automation logs."""
    if not _pool:
        return
    try:
        from app.core.jobs.automation_log import process_automation_queue
        result = await process_automation_queue(_pool)
        if result["processed"] > 0:
            logger.info(
                "Automation queue: %d processed, %d sent, %d failed",
                result["processed"], result["sent"], result["failed"],
            )
    except Exception as e:
        logger.error("Automation queue error: %s", e)


def start_scheduler(pool):
    """Start the background scheduler with the DB pool."""
    global _pool
    _pool = pool

    scheduler.add_job(
        _run_automation_queue,
        trigger=IntervalTrigger(seconds=30),
        id="automation_queue",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — automation queue every 30s")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
