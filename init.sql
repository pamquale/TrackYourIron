
-- 1. Схема для парсера (Scraper)
CREATE SCHEMA IF NOT EXISTS scraper;

CREATE TABLE IF NOT EXISTS scraper.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    link TEXT UNIQUE NOT NULL,
    price DECIMAL(10,2),
    sale_price DECIMAL(10,2),
    last_checked TIMESTAMP DEFAULT NOW()
);

-- 2. Схема для уведомлений (Notifier)
CREATE SCHEMA IF NOT EXISTS notifier;

CREATE TABLE IF NOT EXISTS notifier.users (
    telegram_id BIGINT PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifier.follows (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES notifier.users(telegram_id) ON DELETE CASCADE,
    product_id INT NOT NULL,
    mode VARCHAR(50) NOT NULL,
    set_price DECIMAL(10,2)
);

-- Индекс для ускорения работы бота
CREATE INDEX IF NOT EXISTS idx_follows_product ON notifier.follows(product_id);