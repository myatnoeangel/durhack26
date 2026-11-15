-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- WEATHER OBSERVATIONS
CREATE TABLE IF NOT EXISTS weather_observations (
    time TIMESTAMPTZ NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    precipitation DOUBLE PRECISION,
    cloud_cover DOUBLE PRECISION,

    PRIMARY KEY (time, city)
);

-- Add missing columns to existing databases
ALTER TABLE weather_observations
ADD COLUMN IF NOT EXISTS precipitation DOUBLE PRECISION;

ALTER TABLE weather_observations
ADD COLUMN IF NOT EXISTS cloud_cover DOUBLE PRECISION;

-- Convert weather table into hypertable
SELECT create_hypertable(
    'weather_observations',
    'time',
    if_not_exists => TRUE
);


-- STOCK PRICES
CREATE TABLE IF NOT EXISTS stock_prices (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,

    PRIMARY KEY (time, symbol)
);

-- Convert stock table into hypertable
SELECT create_hypertable(
    'stock_prices',
    'time',
    if_not_exists => TRUE
);


-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_weather_city_time
ON weather_observations (city, time DESC);

CREATE INDEX IF NOT EXISTS idx_stock_symbol_time
ON stock_prices (symbol, time DESC);
