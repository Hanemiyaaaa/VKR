-- 1. Таблица для регистрации загруженных файлов
CREATE TABLE IF NOT EXISTS file_registry (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Таблица для логов ETL
CREATE TABLE IF NOT EXISTS etl_logs (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    data_type VARCHAR(50),
    status VARCHAR(20),
    rows_read INTEGER,
    rows_written INTEGER,
    errors TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

-- 3. Таблица для детальных ошибок строк
CREATE TABLE IF NOT EXISTS etl_errors (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    data_type VARCHAR(50),
    row_data TEXT,
    error_reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Staging-таблицы (повторяют структуру основных таблиц)
CREATE TABLE IF NOT EXISTS staging_accounts (LIKE accounts INCLUDING ALL);
CREATE TABLE IF NOT EXISTS staging_loans (LIKE loans INCLUDING ALL);
CREATE TABLE IF NOT EXISTS staging_deposits (LIKE deposits INCLUDING ALL);
CREATE TABLE IF NOT EXISTS staging_bonds (LIKE bonds INCLUDING ALL);
CREATE TABLE IF NOT EXISTS staging_exchange_rates (LIKE exchange_rates INCLUDING ALL);
CREATE TABLE IF NOT EXISTS staging_capital (LIKE capital_components INCLUDING ALL);
CREATE TABLE IF NOT EXISTS staging_initial_balances (LIKE initial_balances INCLUDING ALL);
CREATE TABLE IF NOT EXISTS staging_transactions (LIKE transactions INCLUDING ALL);
CREATE TABLE IF NOT EXISTS staging_main (LIKE data_table INCLUDING ALL);

-- 5. Индексы
CREATE INDEX IF NOT EXISTS idx_file_registry_status ON file_registry(status);
CREATE INDEX IF NOT EXISTS idx_etl_logs_file_id ON etl_logs(file_id);
CREATE INDEX IF NOT EXISTS idx_etl_errors_file_id ON etl_errors(file_id);