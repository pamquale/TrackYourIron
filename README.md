# TrackYourIron

TrackYourIron is an event-driven price monitoring system for PC components.

## Services

- `gateway` (Rust, axum): receives Telegram webhook updates and publishes events to NATS.
- `scraper` (Rust): parses products and publishes `events.price_dropped`.
- `bot` (Python, aiogram): handles user interactions and notifications.
- `site` (FastAPI + static UI): live website that shows real events from NATS.
- `db` (PostgreSQL): stores products and subscriptions.
- `nats`: message broker.

## One-command startup

From project root:

```bash
docker compose up -d --build
```

This command builds and starts all services, including DB initialization.

## URLs

- Site: http://localhost:8085
- Gateway: http://localhost:8000
- Scraper API: http://localhost:3000
- NATS monitoring: http://localhost:8222

## Stop stack

```bash
docker compose down
```

## Notes

- The site shows only real events consumed from NATS (`events.price_dropped`, `events.telegram_update`).
- If no events exist, the site displays an idle state.
