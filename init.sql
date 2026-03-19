
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(512) NOT NULL,
    link TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS follows (
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    mode VARCHAR(50) DEFAULT 'auto',
    set_price NUMERIC(10, 2),
    PRIMARY KEY (user_id, product_id)
);
