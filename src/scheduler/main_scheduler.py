"""
Main Scheduler
Uses APScheduler to run Weekly Digest and Real-time Alerts pipelines.
"""
import time
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from run_weekly_digest import main as run_digest
from run_realtime_alerts import main as run_alerts
from src.utils.logger import setup_logger

logger = setup_logger("scheduler")

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def start_scheduler():
    config = load_config()
    pipelines = config.get('pipelines', {})
    
    scheduler = BlockingScheduler()
    

    # Wrapper to add jitter
    def run_with_jitter(job_func):
        import random
        # Random delay between 0 and 15 mins (900 seconds)
        delay = random.randint(0, 900)
        logger.info(f"💤 Jitter: Sleeping for {delay} seconds before starting job.")
        time.sleep(delay)
        job_func()

    # 1. Weekly Digest
    digest_config = pipelines.get('weekly_digest', {})
    if digest_config.get('enabled'):
        schedule = digest_config.get('schedule', {})
        day = schedule.get('day_of_week', 'sun')
        hour = schedule.get('hour', 20)
        
        logger.info(f"Scheduling Weekly Digest: Day={day}, Hour={hour} (+0-15m jitter)")
        scheduler.add_job(
            lambda: run_with_jitter(run_digest),
            CronTrigger(day_of_week=day, hour=hour),
            id='weekly_digest'
        )

    # 2. Real-time Alerts
    alerts_config = pipelines.get('realtime_alerts', {})
    if alerts_config.get('enabled'):
        interval = alerts_config.get('schedule', {}).get('interval_minutes', 30)
        
        logger.info(f"Scheduling Real-time Alerts: Interval={interval} mins")
        # Alerts are time sensitive, maybe less jitter or none?
        # User asked about "Fixed time being valid". 
        # For alerts, speed matters. But maybe 1-2 min jitter helps?
        # Let's add small jitter (0-2 mins) for alerts
        scheduler.add_job(
            lambda: run_with_jitter(run_alerts) if interval > 10 else run_alerts, # strict speed if very frequent
            IntervalTrigger(minutes=interval),
            id='realtime_alerts'
        )

    try:
        logger.info("Scheduler started. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")

if __name__ == "__main__":
    start_scheduler()
