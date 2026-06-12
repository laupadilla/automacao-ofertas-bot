from app.db.database import init_db
from app.jobs.scheduler import start

if __name__ == "__main__":
    init_db()
    start()