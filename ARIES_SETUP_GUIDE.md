# Aries: Real-Time Brand Intelligence Platform
## Complete Setup & Implementation Guide

---

## Project Overview

**Aries** is a real-time brand intelligence platform that:
- Ingests data from Reddit, social media, and news sources via **Kafka**
- Processes unstructured text using **Apache Spark** (streaming + batch)
- Stores raw data in **MinIO** (S3-compatible object storage)
- Aggregates results in **PostgreSQL** (serving layer)
- Visualizes insights via **Streamlit** dashboard

---

## Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARIES ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Data Ingestion Layer                                          │
│  ├─ Reddit Producer (PRAW)                                    │
│  ├─ Web Scraper (Scrapy)                                      │
│  └─ → Apache Kafka (Message Buffer)                           │
│                                                                 │
│  Processing Layer                                              │
│  ├─ Spark Structured Streaming (Real-time, VADER)            │
│  └─ Spark Batch Job (NLP, Topic Modeling)                    │
│                                                                 │
│  Storage Layer                                                 │
│  ├─ MinIO (Data Lake - Raw/Processed)                        │
│  └─ PostgreSQL (Serving Layer - Aggregated)                  │
│                                                                 │
│  Visualization Layer                                           │
│  └─ Streamlit Dashboard                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Requirements

- **Docker & Docker Compose** (for Kafka, MinIO, PostgreSQL)
- **Python 3.8+**
- **Apache Spark 3.0+** (or PySpark via pip)
- **PostgreSQL client** tools
- **RAM**: 8GB+ recommended
- **Disk space**: 10GB+ for data lake

---

## Step-by-Step Implementation

### STEP 1: Environment Setup

#### 1.1 Create Project Directory
```bash
mkdir aries-platform
cd aries-platform

# Create subdirectories
mkdir -p docker configs data-lake notebooks spark-jobs producers streamlit-app
```

#### 1.2 Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip
```

#### 1.3 Install Python Dependencies
```bash
pip install \
    pyspark==3.5.0 \
    kafka-python==2.0.2 \
    psycopg2-binary==2.9.9 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    praw==7.7.0 \
    scrapy==2.11.0 \
    vaderSentiment==3.3.2 \
    streamlit==1.31.1 \
    plotly==5.17.0 \
    minio==7.2.0
```

---

### STEP 2: Docker Infrastructure (Kafka, MinIO, PostgreSQL)

#### 2.1 Create `docker-compose.yml`

See the Docker Compose file in the files section below.

#### 2.2 Start All Services
```bash
cd docker
docker-compose up -d

# Verify all services are running
docker-compose ps

# Check logs if needed
docker-compose logs -f kafka
```

#### 2.3 Verify Connections
```bash
# Test Kafka
docker exec -it aries-kafka kafka-topics --list --bootstrap-server localhost:9092

# Test PostgreSQL
psql -h localhost -U aries_user -d aries_db -c "SELECT version();"

# Test MinIO (visit http://localhost:9001)
# Default credentials: minioadmin / minioadmin
```

---

### STEP 3: PostgreSQL Schema Setup

#### 3.1 Create Database Schema
```bash
psql -h localhost -U aries_user -d aries_db -f configs/schema.sql
```

This creates tables:
- `raw_posts` - Raw data from sources
- `sentiment_analysis` - Per-post sentiment scores
- `sentiment_aggregates` - Hourly sentiment rollups
- `topic_analysis` - Extracted topics
- `anomalies` - Detected sentiment drops

---

### STEP 4: Data Ingestion (Kafka Producers)

#### 4.1 Reddit Producer (`producers/reddit_producer.py`)
- Fetches posts from specified subreddits
- Pushes to Kafka topic `reddit-raw`
- Runs continuously or on schedule

#### 4.2 Web Scraper Producer (`producers/web_scraper.py`)
- Scrapes news articles, blogs
- Pushes to Kafka topic `web-raw`
- Uses Scrapy for efficiency

#### 4.3 Run Producers
```bash
# Terminal 1: Reddit Producer
python producers/reddit_producer.py

# Terminal 2: Web Scraper
python producers/web_scraper.py
```

---

### STEP 5: Spark Jobs (Processing Layer)

#### 5.1 Real-Time Streaming Job (`spark-jobs/streaming_sentiment.py`)

Reads from Kafka → Sentiment Analysis (VADER) → 1-minute windows → PostgreSQL

```bash
# Run streaming job
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  spark-jobs/streaming_sentiment.py
```

#### 5.2 Batch Job (`spark-jobs/batch_processing.py`)

Reads from MinIO → NLP preprocessing → Topic modeling → PostgreSQL

```bash
# Run batch job (e.g., every hour via cron or Airflow)
spark-submit spark-jobs/batch_processing.py
```

---

### STEP 6: Streamlit Dashboard (`streamlit-app/dashboard.py`)

Beautiful, interactive visualization of:
- Real-time sentiment gauge
- Sentiment time-series chart
- Top trending topics
- Anomaly detection alerts
- Top negative mentions feed

#### 6.1 Run Streamlit App
```bash
cd streamlit-app
streamlit run dashboard.py
```

**Access dashboard at**: http://localhost:8501

---

### STEP 7: Full System Integration

#### 7.1 Run All Components

**Terminal 1: Kafka & Services**
```bash
cd docker
docker-compose up
```

**Terminal 2: Spark Streaming Job**
```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  spark-jobs/streaming_sentiment.py
```

**Terminal 3: Producers (optional for testing)**
```bash
python producers/reddit_producer.py
```

**Terminal 4: Streamlit Dashboard**
```bash
cd streamlit-app
streamlit run dashboard.py
```

#### 7.2 Monitor System Health
```bash
# Check Kafka topics
docker exec -it aries-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check PostgreSQL data volume
psql -h localhost -U aries_user -d aries_db -c \
  "SELECT table_name, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname='public';"

# Check MinIO buckets
# Visit http://localhost:9001 (minioadmin/minioadmin)
```

---

## Configuration Files Reference

### Kafka Topics
- `reddit-raw` - Raw Reddit posts
- `web-raw` - Raw web articles
- `processed-sentiment` - Post-sentiment data

### PostgreSQL Tables
- `raw_posts` - Raw ingested data
- `sentiment_analysis` - Per-post sentiment
- `sentiment_aggregates` - Hourly summaries
- `topic_analysis` - Topic extraction results
- `anomalies` - Detected anomalies

### MinIO Buckets
- `raw-data` - Raw ingested data
- `processed-data` - Post-Spark processed data
- `models` - ML model artifacts

---

## Testing & Troubleshooting

### Check Kafka Data Flow
```bash
docker exec -it aries-kafka kafka-console-consumer \
  --topic reddit-raw \
  --from-beginning \
  --bootstrap-server localhost:9092 | head -20
```

### Debug PostgreSQL Connections
```bash
# From within container
docker exec -it aries-postgres psql -U aries_user -d aries_db -c \
  "SELECT COUNT(*) FROM raw_posts;"
```

### Monitor Spark Jobs
```bash
# Spark UI available at http://localhost:4040 (while job running)
# Check logs
tail -f spark-logs/streaming_sentiment.log
```

### Verify Streamlit Connection
- Check PostgreSQL password in `.env`
- Ensure `sentiment_aggregates` table has data
- Try manual query: `psql -h localhost -U aries_user -d aries_db -c "SELECT * FROM sentiment_aggregates LIMIT 5;"`

---

## Performance Tuning

### Spark Configuration
```python
# In streaming_sentiment.py
spark_config = {
    "spark.sql.shuffle.partitions": "4",
    "spark.streaming.kafka.maxRatePerPartition": "100000",
    "spark.sql.streaming.checkpointLocation": "/tmp/checkpoint"
}
```

### PostgreSQL Connection Pooling
```python
# Use connection pooling for Streamlit
from psycopg2 import pool

connection_pool = pool.SimpleConnectionPool(1, 5, host="localhost", database="aries_db")
```

### MinIO Performance
- Use multi-part uploads for large files
- Enable compression for text data
- Use versioning for data lineage

---

## Production Deployment

### Using Airflow for Scheduling
```python
# dag.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-eng',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'aries-batch-job',
    default_args=default_args,
    schedule_interval='0 * * * *',  # Hourly
    start_date=datetime(2025, 1, 1),
)

batch_task = BashOperator(
    task_id='run-batch-processing',
    bash_command='spark-submit spark-jobs/batch_processing.py',
    dag=dag,
)
```

### Kubernetes Deployment
- Containerize each component (Dockerfile provided)
- Use Helm charts for orchestration
- Deploy Kafka on Confluent Cloud
- Use managed PostgreSQL (RDS, Cloud SQL)

---

## Next Steps

1. **Customize data sources**: Add Twitter/LinkedIn APIs, RSS feeds
2. **Enhance NLP**: Use transformers for better sentiment (BERT, DistilBERT)
3. **Add ML models**: Anomaly detection, predictive alerts
4. **Scale infrastructure**: Multi-node Spark cluster, distributed storage
5. **Monitoring**: Set up Prometheus + Grafana for metrics
6. **Alerting**: Integrate with Slack/Email for critical events

---

## Support & Resources

- **Kafka Documentation**: https://kafka.apache.org/documentation
- **PySpark Guide**: https://spark.apache.org/docs/latest/api/python/
- **Streamlit Docs**: https://docs.streamlit.io
- **PostgreSQL Guide**: https://www.postgresql.org/docs/
- **MinIO Docs**: https://min.io/docs/minio/linux/index.html

