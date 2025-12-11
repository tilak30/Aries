# ============================================================================
# ARIES PLATFORM - QUICK START GUIDE
# ============================================================================

## 🚀 GET STARTED IN 15 MINUTES

### Step 1: Clone/Download the Project
```bash
cd ~/projects
mkdir aries-platform
cd aries-platform
```

### Step 2: Set Up Environment Variables
Create a `.env` file in the project root:
```bash
cat > .env << 'EOF'
# Reddit API (Get from https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=Aries:1.0 (by /u/your_username)

# PostgreSQL
POSTGRES_USER=aries_user
POSTGRES_PASSWORD=aries_password
POSTGRES_DB=aries_db

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Streamlit
STREAMLIT_PORT=8501
EOF
```

### Step 3: Start Docker Services
```bash
# Navigate to docker directory
cd docker

# Start all services (Kafka, PostgreSQL, MinIO, Zookeeper)
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps

# Check logs if needed
docker-compose logs -f postgres
```

### Step 4: Create Virtual Environment & Install Dependencies
```bash
# Go back to project root
cd ..

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Initialize PostgreSQL Schema
```bash
# Option A: Schema was auto-loaded from docker-compose.yml
# Just verify:
psql -h localhost -U aries_user -d aries_db -c "SELECT COUNT(*) FROM raw.posts;"

# Option B: Manual initialization if needed
psql -h localhost -U aries_user -d aries_db < configs/schema.sql
```

### Step 6: Run Streamlit Dashboard (Demo Mode - No Code!)
```bash
# This works immediately with demo data
cd streamlit-app
streamlit run dashboard.py

# Open browser to http://localhost:8501
```

### Step 7: (Optional) Run Real Data Pipeline

#### Terminal 1: Spark Streaming Job
```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.1 \\
  spark-jobs/spark_streaming_job.py
```

#### Terminal 2: Reddit Producer
```bash
# Set your Reddit credentials
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USER_AGENT="Aries:1.0 (by /u/your_username)"

python producers/reddit_producer.py
```

#### Terminal 3: Streamlit Dashboard (Real Data)
```bash
cd streamlit-app

# Edit dashboard.py: change use_demo = False in sidebar
streamlit run dashboard.py
```

---

## 📊 PROJECT STRUCTURE

```
aries-platform/
├── docker/
│   └── docker-compose.yml          # Kafka, PostgreSQL, MinIO, Zookeeper
├── configs/
│   └── schema.sql                  # PostgreSQL schema & functions
├── spark-jobs/
│   ├── streaming_sentiment.py      # Real-time sentiment analysis
│   └── batch_processing.py         # Batch NLP & topic modeling
├── producers/
│   ├── reddit_producer.py          # Reddit data ingestion
│   ├── web_scraper.py              # News/web scraping
│   └── twitter_producer.py         # Twitter/X data ingestion (optional)
├── streamlit-app/
│   └── dashboard.py                # Beautiful dashboard UI
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables
├── .gitignore
└── README.md
```

---

## 🎯 KEY FEATURES

### ✅ Demo Mode (Works Immediately)
```bash
streamlit run streamlit-app/dashboard.py
# Checkbox "Use Demo Data" enabled = mock data loaded
# Works without database/Kafka
```

### ✅ Real-Time Sentiment Analysis
- VADER sentiment analysis (0.0-1.0 scale)
- Positive/Neutral/Negative classification
- Confidence scores

### ✅ Topic Extraction
- Automatic keyword-based topic detection
- Tracks sentiment by topic
- Trending topics identification

### ✅ Anomaly Detection
- Automatic sentiment drop detection
- Severity classification (LOW, MEDIUM, HIGH, CRITICAL)
- PR alert feed for top negative mentions

### ✅ Beautiful Dashboard
- Dark theme with gradient cards
- Real-time metrics cards (KPIs)
- Interactive Plotly charts
- Sentiment distribution & trends
- Top negative mentions feed

---

## 🔌 HOW TO CONNECT YOUR OWN DATA

### Option 1: Connect to PostgreSQL Database
In `streamlit-app/dashboard.py`, the demo mode is toggled via sidebar checkbox:
```python
use_demo = st.checkbox("Use Demo Data", value=False)  # Set to False
```

Then edit connection parameters:
```python
conn = psycopg2.connect(
    host="localhost",
    database="aries_db",
    user="aries_user",
    password="aries_password",
    port=5432
)
```

### Option 2: Connect to Different Data Source
Modify the fetch functions in dashboard.py:
```python
@st.cache_data(ttl=60)
def fetch_sentiment_overview(conn):
    # Replace with your custom query
    cur.execute("SELECT * FROM your_table")
    return pd.DataFrame(cur.fetchall())
```

---

## 🚨 TROUBLESHOOTING

### Issue: "Cannot connect to Kafka"
```bash
# Check if Kafka container is running
docker ps | grep kafka

# Check logs
docker logs aries-kafka

# Restart services
cd docker && docker-compose restart kafka
```

### Issue: "PostgreSQL connection refused"
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check postgres password is correct in .env
psql -h localhost -U aries_user -d aries_db
```

### Issue: "Streamlit not loading dashboard"
```bash
# Clear Streamlit cache
rm -rf ~/.streamlit/cache

# Verify localhost:8501 is accessible
curl http://localhost:8501

# Restart Streamlit
pkill -f streamlit
streamlit run streamlit-app/dashboard.py
```

### Issue: Reddit API credentials not working
```bash
# Verify credentials are set
echo $REDDIT_CLIENT_ID
echo $REDDIT_CLIENT_SECRET

# If empty, re-export
export REDDIT_CLIENT_ID="your_id"
export REDDIT_CLIENT_SECRET="your_secret"

# Test PRAW
python -c "import praw; print('PRAW OK')"
```

---

## 📈 PRODUCTION DEPLOYMENT

### Using Docker for All Components
```bash
# Build custom Docker image with Spark
docker build -t aries:latest .

# Run all in containers
docker-compose -f docker-compose.prod.yml up -d
```

### Using Kubernetes
```bash
# Deploy to K8s cluster
kubectl apply -f k8s/kafka.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/spark.yaml
kubectl apply -f k8s/streamlit.yaml
```

### Using Airflow for Scheduling
```bash
# Initialize Airflow
airflow db init

# Create DAG for batch jobs
cp dags/aries_dag.py ~/airflow/dags/

# Start scheduler
airflow scheduler
```

---

## 📚 RESOURCES

- **Streamlit Docs**: https://docs.streamlit.io
- **PySpark Guide**: https://spark.apache.org/docs/latest/api/python/
- **Kafka Documentation**: https://kafka.apache.org/documentation
- **PostgreSQL**: https://www.postgresql.org/docs/
- **MinIO**: https://min.io/docs/minio/linux/index.html
- **VADER Sentiment**: https://github.com/cjhutto/vaderSentiment
- **PRAW (Reddit API)**: https://praw.readthedocs.io

---

## 🆘 NEED HELP?

### Check Log Files
```bash
# Spark logs
tail -f spark-logs/streaming_sentiment.log

# Producer logs
tail -f logs/reddit_producer.log

# Streamlit logs
tail -f logs/streamlit.log
```

### Verify Data Flow
```bash
# Check Kafka topics
docker exec aries-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check messages in topic
docker exec aries-kafka kafka-console-consumer \
  --topic reddit-raw \
  --from-beginning \
  --bootstrap-server localhost:9092 | head -5

# Check PostgreSQL data volume
psql -h localhost -U aries_user -d aries_db -c \
  "SELECT table_name, COUNT(*) FROM information_schema.tables WHERE table_schema='raw' GROUP BY table_name;"
```

---

## 🎓 LEARNING PATH

1. **Week 1**: Set up infrastructure, run dashboard with demo data
2. **Week 2**: Connect real Reddit data, run streaming job
3. **Week 3**: Implement custom topic extraction, add more data sources
4. **Week 4**: Deploy to production, set up monitoring & alerting

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-01  
**Maintainer**: Data Engineering Team  
