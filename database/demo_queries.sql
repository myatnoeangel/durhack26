
-- =====================================================
-- DURHACK 2026
-- TIGERDATA DATABASE DEMONSTRATION
-- =====================================================


-- =====================================================
-- 1. DATABASE CONNECTION INFORMATION
-- =====================================================

SELECT
    current_database() AS database_name,
    current_user AS connected_user,
    version() AS postgres_version,
    NOW() AS current_time;


-- =====================================================
-- 2. DATABASE TABLES
-- =====================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;


-- =====================================================
-- 3. TABLE STRUCTURES
-- =====================================================

SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;


-- =====================================================
-- 4. WEATHER DATA VERIFICATION
-- =====================================================

-- Total weather records

SELECT COUNT(*) AS total_weather_records
FROM weather_observations;


-- Weather records by city
-- Assumes the location column is named city.
-- Adjust if your actual schema differs.

SELECT
    city,
    COUNT(*) AS total_records,
    MIN(time) AS first_record,
    MAX(time) AS latest_record
FROM weather_observations
GROUP BY city
ORDER BY city;


-- View latest weather records

SELECT *
FROM weather_observations
ORDER BY time DESC
LIMIT 10;


-- =====================================================
-- 5. STOCK DATA VERIFICATION
-- =====================================================

-- Total stock records

SELECT COUNT(*) AS total_stock_records
FROM stock_prices;


-- Stock records by company

SELECT
    symbol,
    COUNT(*) AS total_records,
    MIN(time) AS first_record,
    MAX(time) AS latest_record
FROM stock_prices
GROUP BY symbol
ORDER BY symbol;


-- View latest stock records

SELECT *
FROM stock_prices
ORDER BY time DESC
LIMIT 10;


-- Check duplicate stock records

SELECT
    symbol,
    time,
    COUNT(*) AS duplicate_count
FROM stock_prices
GROUP BY symbol, time
HAVING COUNT(*) > 1;


-- =====================================================
-- 6. TIMESCALEDB HYPERTABLES
-- =====================================================

SELECT *
FROM timescaledb_information.hypertables;


-- =====================================================
-- 7. TIMESCALEDB CHUNKS
-- =====================================================

SELECT
    hypertable_name,
    COUNT(*) AS total_chunks
FROM timescaledb_information.chunks
GROUP BY hypertable_name;


-- Inspect individual chunks

SELECT
    hypertable_name,
    chunk_name,
    range_start,
    range_end
FROM timescaledb_information.chunks
ORDER BY hypertable_name, range_start;


-- =====================================================
-- 8. BACKGROUND JOBS
-- =====================================================

SELECT *
FROM timescaledb_information.jobs;


-- Background job execution statistics

SELECT *
FROM timescaledb_information.job_stats;


-- =====================================================
-- 9. DATABASE SIZE AND STORAGE
-- =====================================================

SELECT
    pg_size_pretty(
        pg_database_size(current_database())
    ) AS database_size;


-- Table storage sizes

SELECT
    relname AS table_name,
    pg_size_pretty(
        pg_total_relation_size(relid)
    ) AS total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;


-- =====================================================
-- 10. DATABASE MONITORING
-- =====================================================

-- Database activity statistics

SELECT
    datname,
    numbackends AS active_connections,
    xact_commit AS committed_transactions,
    xact_rollback AS rolled_back_transactions,
    blks_read,
    blks_hit
FROM pg_stat_database
WHERE datname = current_database();


-- Current database activity

SELECT
    pid,
    usename,
    state,
    query_start,
    query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY query_start DESC;


-- Table-level statistics

SELECT
    relname AS table_name,
    seq_scan,
    idx_scan,
    n_live_tup AS estimated_rows,
    n_dead_tup AS estimated_dead_rows
FROM pg_stat_user_tables
ORDER BY relname;


-- =====================================================
-- END OF DATABASE DEMONSTRATION
-- =====================================================
