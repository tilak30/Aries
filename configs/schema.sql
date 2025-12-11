-- ============================================================================
-- ARIES PLATFORM - PostgreSQL Schema
-- ============================================================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS processed;
CREATE SCHEMA IF NOT EXISTS analytics;

-- ============================================================================
-- RAW DATA LAYER
-- ============================================================================

-- Raw posts table (ingested from Kafka)
CREATE TABLE IF NOT EXISTS raw.posts (
    post_id VARCHAR(255) PRIMARY KEY,
    source VARCHAR(50) NOT NULL,  -- 'reddit', 'twitter', 'news', etc.
    title VARCHAR(500),
    content TEXT NOT NULL,
    author VARCHAR(255),
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    ingested_at TIMESTAMP DEFAULT NOW(),
    raw_metadata JSONB,
    INDEX idx_source_created (source, created_at DESC),
    INDEX idx_created_at (created_at DESC)
);

-- ============================================================================
-- PROCESSED DATA LAYER
-- ============================================================================

-- Sentiment analysis results (post-level)
CREATE TABLE IF NOT EXISTS processed.sentiment_analysis (
    analysis_id SERIAL PRIMARY KEY,
    post_id VARCHAR(255) REFERENCES raw.posts(post_id),
    content TEXT,
    sentiment_label VARCHAR(20) NOT NULL,  -- 'POSITIVE', 'NEUTRAL', 'NEGATIVE'
    sentiment_score FLOAT NOT NULL,  -- 0.0 to 1.0
    confidence FLOAT,  -- Model confidence score
    analyzed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    source VARCHAR(50),
    brand VARCHAR(100), -- Added for brand intelligence
    INDEX idx_sentiment_label (sentiment_label),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_source_sentiment (source, sentiment_label),
    INDEX idx_brand_created_at (brand, created_at DESC) -- Added for dashboard performance
);

-- Topic extraction results
CREATE TABLE IF NOT EXISTS processed.topic_analysis (
    topic_id SERIAL PRIMARY KEY,
    post_id VARCHAR(255) REFERENCES raw.posts(post_id),
    topic VARCHAR(255) NOT NULL,  -- 'Customer Service', 'Pricing', etc.
    confidence FLOAT,
    sentiment_score FLOAT,
    analyzed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_topic (topic),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_topic_created (topic, created_at DESC)
);

-- ============================================================================
-- ANALYTICS LAYER (Aggregated Data)
-- ============================================================================

-- Hourly sentiment aggregates
CREATE TABLE IF NOT EXISTS analytics.sentiment_aggregates (
    agg_id SERIAL PRIMARY KEY,
    hour_bucket TIMESTAMP NOT NULL,
    sentiment_label VARCHAR(20),
    count INT,
    avg_sentiment_score FLOAT,
    min_sentiment_score FLOAT,
    max_sentiment_score FLOAT,
    source VARCHAR(50),
    UNIQUE (hour_bucket, sentiment_label, source),
    INDEX idx_hour_bucket (hour_bucket DESC),
    INDEX idx_sentiment_label (sentiment_label)
);

-- Top topics per day
CREATE TABLE IF NOT EXISTS analytics.topic_daily_stats (
    stat_id SERIAL PRIMARY KEY,
    date_bucket DATE NOT NULL,
    topic VARCHAR(255),
    mention_count INT,
    avg_sentiment FLOAT,
    sentiment_trend VARCHAR(20),  -- 'IMPROVING', 'STABLE', 'DECLINING'
    UNIQUE (date_bucket, topic),
    INDEX idx_date_bucket (date_bucket DESC),
    INDEX idx_topic (topic)
);

-- Sentiment anomalies (detected drops)
CREATE TABLE IF NOT EXISTS analytics.anomalies (
    anomaly_id SERIAL PRIMARY KEY,
    detected_at TIMESTAMP DEFAULT NOW(),
    anomaly_type VARCHAR(50),  -- 'SENTIMENT_DROP', 'VOLUME_SPIKE', etc.
    severity VARCHAR(20),  -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    sentiment_drop_percentage FLOAT,
    affected_topic VARCHAR(255),
    description TEXT,
    affected_records INT,
    recommended_action TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    INDEX idx_detected_at (detected_at DESC),
    INDEX idx_severity (severity),
    INDEX idx_acknowledged (acknowledged)
);

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- Real-time sentiment summary (last 24 hours)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.v_sentiment_last24h AS
SELECT 
    sentiment_label,
    COUNT(*) as count,
    ROUND(AVG(sentiment_score)::numeric, 3) as avg_score,
    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER())::numeric, 1) as percentage,
    NOW() as computed_at
FROM processed.sentiment_analysis
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY sentiment_label;

-- Top 10 trending topics (last 7 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.v_top_topics_7d AS
SELECT 
    topic,
    COUNT(*) as mentions,
    ROUND(AVG(sentiment_score)::numeric, 3) as avg_sentiment,
    COUNT(CASE WHEN sentiment_score > 0.6 THEN 1 END) as positive_mentions,
    COUNT(CASE WHEN sentiment_score < 0.4 THEN 1 END) as negative_mentions,
    NOW() as computed_at
FROM processed.topic_analysis
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY topic
ORDER BY mentions DESC
LIMIT 10;

-- ============================================================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- ============================================================================

-- Function to calculate hourly sentiment aggregates
CREATE OR REPLACE FUNCTION analytics.calculate_hourly_aggregates()
RETURNS TABLE (inserted_count INT) AS $$
DECLARE
    v_inserted_count INT;
BEGIN
    INSERT INTO analytics.sentiment_aggregates 
    (hour_bucket, sentiment_label, count, avg_sentiment_score, min_sentiment_score, max_sentiment_score, source)
    SELECT 
        DATE_TRUNC('hour', created_at) as hour_bucket,
        sentiment_label,
        COUNT(*),
        ROUND(AVG(sentiment_score)::numeric, 3),
        MIN(sentiment_score),
        MAX(sentiment_score),
        source
    FROM processed.sentiment_analysis
    WHERE created_at >= NOW() - INTERVAL '2 hours'
        AND created_at < DATE_TRUNC('hour', NOW())
    GROUP BY DATE_TRUNC('hour', created_at), sentiment_label, source
    ON CONFLICT (hour_bucket, sentiment_label, source) DO UPDATE
    SET count = EXCLUDED.count,
        avg_sentiment_score = EXCLUDED.avg_sentiment_score,
        min_sentiment_score = EXCLUDED.min_sentiment_score,
        max_sentiment_score = EXCLUDED.max_sentiment_score;
    
    GET DIAGNOSTICS v_inserted_count = ROW_COUNT;
    RETURN QUERY SELECT v_inserted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to detect sentiment anomalies
CREATE OR REPLACE FUNCTION analytics.detect_anomalies()
RETURNS TABLE (anomaly_count INT) AS $$
DECLARE
    v_count INT;
BEGIN
    -- Detect sudden sentiment drops
    INSERT INTO analytics.anomalies 
    (anomaly_type, severity, sentiment_drop_percentage, affected_topic, description, affected_records)
    SELECT 
        'SENTIMENT_DROP' as anomaly_type,
        CASE 
            WHEN pct_change > 30 THEN 'CRITICAL'
            WHEN pct_change > 20 THEN 'HIGH'
            WHEN pct_change > 10 THEN 'MEDIUM'
            ELSE 'LOW'
        END as severity,
        ABS(pct_change) as sentiment_drop_percentage,
        topic,
        'Significant drop in ' || topic || ' sentiment',
        affected_count
    FROM (
        SELECT 
            t1.topic,
            COUNT(*) as affected_count,
            ROUND(
                ((AVG(t2.sentiment_score) - AVG(t1.sentiment_score)) / AVG(t2.sentiment_score) * 100)::numeric, 
                2
            ) as pct_change
        FROM processed.topic_analysis t1
        JOIN processed.topic_analysis t2 ON t1.topic = t2.topic
        WHERE t1.created_at >= NOW() - INTERVAL '1 hour'
            AND t1.created_at < NOW() - INTERVAL '30 minutes'
            AND t2.created_at >= NOW() - INTERVAL '2 hours'
            AND t2.created_at < NOW() - INTERVAL '1 hour'
        GROUP BY t1.topic
        HAVING ABS(((AVG(t2.sentiment_score) - AVG(t1.sentiment_score)) / AVG(t2.sentiment_score) * 100)) > 15
    ) anomaly_data
    WHERE NOT EXISTS (
        SELECT 1 FROM analytics.anomalies a
        WHERE a.affected_topic = anomaly_data.topic
            AND a.detected_at >= NOW() - INTERVAL '30 minutes'
    );
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN QUERY SELECT v_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INDEXING FOR QUERY OPTIMIZATION
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_raw_posts_source_created ON raw.posts(source, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_label_created ON processed.sentiment_analysis(sentiment_label, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_topic_analysis_topic_created ON processed.topic_analysis(topic, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON analytics.anomalies(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_agg_hour_bucket ON analytics.sentiment_aggregates(hour_bucket DESC);

-- ============================================================================
-- INITIAL DATA FOR TESTING (Comment out after first run)
-- ============================================================================

-- Insert sample data for dashboard testing
INSERT INTO raw.posts (post_id, source, title, content, author, created_at) VALUES
('reddit_001', 'reddit', 'Great product quality', 'This product exceeded my expectations! Excellent customer service too.', 'user123', NOW() - INTERVAL '2 hours'),
('reddit_002', 'reddit', 'Disappointed with purchase', 'Terrible quality. Broke after one week. Waste of money.', 'user456', NOW() - INTERVAL '1.5 hours'),
('reddit_003', 'reddit', 'Average experience', 'Product is okay. Nothing special but does the job.', 'user789', NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

INSERT INTO processed.sentiment_analysis (post_id, content, sentiment_label, sentiment_score, source, created_at) VALUES
('reddit_001', 'This product exceeded my expectations! Excellent customer service too.', 'POSITIVE', 0.92, 'reddit', NOW() - INTERVAL '2 hours'),
('reddit_002', 'Terrible quality. Broke after one week. Waste of money.', 'NEGATIVE', 0.08, 'reddit', NOW() - INTERVAL '1.5 hours'),
('reddit_003', 'Product is okay. Nothing special but does the job.', 'NEUTRAL', 0.52, 'reddit', NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

INSERT INTO processed.topic_analysis (post_id, topic, sentiment_score, created_at) VALUES
('reddit_001', 'Customer Service', 0.92, NOW() - INTERVAL '2 hours'),
('reddit_002', 'Product Quality', 0.08, NOW() - INTERVAL '1.5 hours'),
('reddit_003', 'Product Quality', 0.52, NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- PERMISSIONS & SECURITY
-- ============================================================================

-- Create read-only role for Streamlit
CREATE ROLE aries_readonly WITH LOGIN PASSWORD 'aries_readonly_pass';
GRANT CONNECT ON DATABASE aries_db TO aries_readonly;
GRANT USAGE ON SCHEMA raw, processed, analytics TO aries_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA raw, processed, analytics TO aries_readonly;

-- Ensure future tables are readable
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO aries_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA processed GRANT SELECT ON TABLES TO aries_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO aries_readonly;
