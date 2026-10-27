-- Схема бази даних кав’ярні.
-- Усі таблиці створюються з IF NOT EXISTS, тому init_db() безпечно викликати при кожному запуску.
-- Якщо змінюєте СТРУКТУРУ вже існуючої таблиці, видаліть локальний db.sqlite і перезапустіть застосунок.

-- Відгуки користувачів
CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Товари меню
CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    price        REAL NOT NULL CHECK (price >= 0),
    category     TEXT NOT NULL DEFAULT 'Десерти',
    is_available INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0, 1))
);

-- Клієнти
CREATE TABLE IF NOT EXISTS customers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    phone      TEXT NOT NULL UNIQUE,
    email      TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Замовлення
-- Клієнта з замовленнями видалити не можна (RESTRICT): це захищає цілісність даних.
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status      TEXT NOT NULL DEFAULT 'new'
                CHECK (status IN ('new', 'preparing', 'delivering', 'done', 'cancelled')),
    address     TEXT NOT NULL DEFAULT '',
    comment     TEXT NOT NULL DEFAULT '',
    total       REAL NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Позиції замовлення: зв’язок «багато-до-багатьох» між orders і products.
-- Замовлення видаляє свої позиції (CASCADE); товар, який є в замовленнях, видалити не можна (RESTRICT):
-- такий товар краще вимикати через is_available = 0.
CREATE TABLE IF NOT EXISTS order_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id       INTEGER NOT NULL REFERENCES orders(id)   ON DELETE CASCADE,
    product_id     INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    price_at_order REAL NOT NULL
);
