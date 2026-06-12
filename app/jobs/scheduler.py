from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from app.jobs.scraper_job import run_scraper
from app.jobs.sender_job import run_sender_sync
import pytz

BRASILIA = pytz.timezone("America/Sao_Paulo")

def start():
    scheduler = BlockingScheduler(timezone=BRASILIA)

    # Scraper roda às 7h horário de Brasília
    scheduler.add_job(
        run_scraper,
        CronTrigger(hour=7, minute=0, timezone=BRASILIA),
        id="scraper",
        name="Scraper Amazon"
    )

    # Sender roda nos 4 horários de Brasília
    for time_str in ["07:30", "12:00", "18:30", "21:00"]:
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            run_sender_sync,
            CronTrigger(hour=hour, minute=minute, timezone=BRASILIA),
            id=f"sender_{time_str}",
            name=f"Sender {time_str}"
        )

    print("⏰ Scheduler iniciado — Horário de Brasília (America/Sao_Paulo)")
    print("  📦 Scraper:  07:00")
    print("  📤 Sender:   07:30 | 12:00 | 18:30 | 21:00")
    scheduler.start()