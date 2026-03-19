-- Create logical schemas to simulate database-per-service pattern within a single PostgreSQL instance
CREATE SCHEMA IF NOT EXISTS scraper_db;
CREATE SCHEMA IF NOT EXISTS notifier_db;

-- Scraper Service Tables
CREATE TABLE IF NOT EXISTS scraper_db.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(512) NOT NULL,
    link TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);

-- Notification Service Tables
CREATE TABLE IF NOT EXISTS notifier_db.users (
    telegram_id BIGINT PRIMARY KEY,
    name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS notifier_db.follows (
    user_id BIGINT REFERENCES notifier_db.users(telegram_id) ON DELETE CASCADE,
    product_id INTEGER, -- Soft link to scraper_db.products.id, no hard foreign key
    product_name VARCHAR(512),
    product_link TEXT,
    mode VARCHAR(50) DEFAULT 'auto',
    set_price NUMERIC(10, 2),
    PRIMARY KEY (user_id, product_id)
);
