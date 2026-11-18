"""
In-app daily scheduler (APScheduler). Runs the career-page pipeline every day
and sends the Telegram digest. Boards stay on their own nightly run.py.

Time is IST. Change CAREER_HOUR / CAREER_MIN in config or here.
"""
from apscheduler.schedulers.background import BackgroundScheduler

import config
from app.services import pipeline

_sched = None


def _daily_job():
    # Launch through the tracker so scheduled runs show in Run history too.
    from app.services import runner
    runner.launch("career")


def start():
    """Start the scheduler; safe to call once at server startup."""
    global _sched
    if _sched is not None:
        return _sched
    hour = int(getattr(config, "CAREER_HOUR", 8))
    minute = int(getattr(config, "CAREER_MIN", 0))
    _sched = BackgroundScheduler(timezone="Asia/Kolkata")
    _sched.add_job(_daily_job, "cron", hour=hour, minute=minute,
                   id="daily_career", replace_existing=True, misfire_grace_time=3600)
    _sched.start()
    print(f"[scheduler] daily career run scheduled at {hour:02d}:{minute:02d} IST")
    return _sched


def jobs_info():
    if _sched is None:
        return []
    return [{"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None}
            for j in _sched.get_jobs()]
