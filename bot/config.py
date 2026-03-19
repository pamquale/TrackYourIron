import os


BOT_TOKEN: str = os.environ["BOT_TOKEN"]

DB_DSN: str = os.getenv(
    "DB_DSN",
    "postgresql://notifier:notifier@localhost:5432/notifier_db",
)

NATS_URL: str = os.getenv("NATS_URL", "nats://localhost:4222")

SCRAPER_BASE_URL: str = os.getenv("SCRAPER_BASE_URL", "http://scraper:8080")
