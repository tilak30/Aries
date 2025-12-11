# 🔮 Aries - Real-Time Brand Intelligence Platform

> **A production-ready data engineering platform for real-time sentiment analysis and brand intelligence**

![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.0-blue)

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Quick Start](#quick-start)
- [Files Included](#files-included)
- [Installation](#installation)
- [Usage](#usage)
- [Dashboard](#dashboard)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

**Aries** is a real-time brand intelligence platform that ingests, processes, and analyzes millions of data points from social media, forums, and news articles. It provides executives, marketers, and PR teams with a live, quantitative "pulse" of brand health.

### Problem Statement
- Brand reputation crises unfold in minutes, not days
- Executives rely on slow, after-the-fact reports
- Real-time monitoring at scale requires sophisticated infrastructure

### Solution
Aries solves this with:
- ✅ **Real-time data ingestion** from multiple sources
- ✅ **Distributed processing** with Apache Spark
- ✅ **Sentiment analysis** using VADER NLP
- ✅ **Anomaly detection** for crisis alerts
- ✅ **Beautiful dashboard** for instant insights
- ✅ **Scalable architecture** ready for millions of records

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ARIES ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────┘

                            DATA INGESTION LAYER
                                   │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
            ┌─────▼─────┐   ┌──────▼──────┐   ┌─────▼─────┐
            │   Reddit   │   │   Twitter   │   │  News API │
            │  (PRAW)    │   │  (Tweepy)   │   │ (NewsAPI) │
            └─────┬─────┘   └──────┬──────┘   └─────┬─────┘
                  │                 │                 │
                  └─────────────────┼─────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  Apache Kafka       │
                         │  (Message Queue)    │
                         └──────────┬──────────┘
                                    │
                       ┌────────────▼────────────┐
                       │ STREAM & BATCH LAYER    │
                       │                         │
                       │ ┌──────────────────┐    │
                       │ │ Spark Streaming  │    │
                       │ │ Real-time        │    │
                       │ │ Sentiment (VADER)│    │
                       │ └──────────────────┘    │
                       │                         │
                       │ ┌──────────────────┐    │
                       │ │ Spark Batch      │    │
                       │ │ Topic Modeling   │    │
                       │ │ NLP Analysis     │    │ 
                       │ └──────────────────┘    │
                       └────────────┬────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
        ┌───────────▼───────┐   ┌───▼──────┐   ┌──▼──────────┐
        │ MinIO Data Lake   │   │PostgreSQL│   │ MongoDB     │
        │ (Raw + Processed) │   │(Serving) │   │(Backups)    │
        └───────────────────┘   └───┬──────┘   └─────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   Streamlit App     │
                         │   Beautiful UI      │
                         │   Real-time Charts  │
                         └─────────────────────┘
```

## ✨ Features

### 📊 Real-Time Monitoring
- Live sentiment scores (0.0 - 1.0 scale)
- Positive/Neutral/Negative classification
- Per-source analytics

### 🔥 Trending Topics
- Automatic keyword extraction
- Topic-level sentiment analysis
- Trend detection

### 🚨 Anomaly Detection
- Automatic sentiment drop detection
- Severity classification (LOW, MEDIUM, HIGH, CRITICAL)
- PR alert feed for top negative mentions

### 📈 Interactive Dashboard
- Dark theme with gradient cards
- Real-time KPI metrics
- Multiple chart types (pie, line, bar)
- Mobile-responsive design
- Demo mode (works without database)

### 🔧 Production Ready
- Docker containerization
- Scalable architecture
- Error handling & logging
- Database schema with indexes
- Connection pooling

## 🚀 Quick Start

### 5-Minute Demo (No Setup)
```bash
# Install dependencies
pip install streamlit plotly pandas

# Run dashboard with demo data
cd streamlit-app
streamlit run streamlit_dashboard.py

# Visit http://localhost:8501
```

### 30-Minute Full Setup
```bash
# 1. Start infrastructure
cd docker
docker-compose up -d
cd ..

# 2. Install Python packages
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Initialize database
psql -h localhost -U aries_user -d aries_db < configs/schema.sql

# 4. Run dashboard
cd streamlit-app
streamlit run streamlit_dashboard.py
```

## 📦 Files Included

### Core Files
| File | Purpose |
|------|---------|
| `streamlit_dashboard.py` | Beautiful interactive dashboard |
| `spark_streaming_job.py` | Real-time sentiment analysis |
| `reddit_producer.py` | Reddit data ingestion |
| `schema.sql` | PostgreSQL database schema |
| `docker-compose.yml` | Infrastructure as code |
| `requirements.txt` | Python dependencies |

### Documentation
| File | Purpose |
|------|---------|
| `QUICK_START.md` | Getting started guide |
| `ARIES_SETUP_GUIDE.md` | Comprehensive reference |
| `FILES_SUMMARY.md` | File overview & checklist |
| `README.md` | This file |

### Scripts
| File | Purpose |
|------|---------|
| `install.sh` | Automated installation |

## 📥 Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.8+
- 8GB+ RAM
- 10GB+ disk space

### Automated Installation
```bash
bash install.sh
```

### Manual Installation
See `QUICK_START.md` for step-by-step instructions.

## 💻 Usage

### Running the Dashboard
```bash
cd streamlit-app
streamlit run streamlit_dashboard.py
```

**Access**: http://localhost:8501

### Demo Mode
The dashboard includes a **Demo Data** toggle in the sidebar. Enable it to use mock data without connecting to a database.

### Live Mode (Connect to Database)
1. Ensure PostgreSQL is running: `docker-compose ps`
2. Disable "Use Demo Data" in sidebar
3. Edit connection parameters in `streamlit_dashboard.py` if needed

### Running with Real Data
```bash
# Terminal 1: Spark Streaming Job (includes Kafka and PostgreSQL drivers)
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.1 \
  spark-jobs/spark_streaming_job.py

# Terminal 2: Reddit Producer
export REDDIT_CLIENT_ID="your_id"
export REDDIT_CLIENT_SECRET="your_secret"
python producers/reddit_producer.py

# Terminal 3: Dashboard
cd streamlit-app
streamlit run streamlit_dashboard.py
```

## 📊 Dashboard Walkthrough

### Metrics Section
- **Overall Sentiment**: Current brand sentiment score
- **Posts Analyzed**: Total posts processed in 24h
- **Positive Sentiment %**: Distribution of positive mentions
- **System Status**: LIVE or DEMO mode indicator

### Charts & Analytics
1. **Sentiment Distribution** (Pie Chart)
   - Breakdown of positive/neutral/negative
   - Color-coded for quick identification

2. **Sentiment Trend** (Line Chart)
   - 24-hour trend visualization
   - Shows sentiment evolution over time

3. **Trending Topics** (Bar Chart)
   - Most mentioned topics
   - Color intensity based on sentiment
   - Interactive hover details

### Alerts & Monitoring
- **Anomalies**: Sudden sentiment drops with severity
- **Top Negative Mentions**: PR alert feed
- **System Metrics**: Kafka topics, Spark jobs, data volume

## 🎨 Customization

### Change Sentiment Model
Replace VADER with BERT or RoBERTa for better accuracy:
```python
from transformers import pipeline

sentiment_pipeline = pipeline("sentiment-analysis")

def analyze_sentiment_bert(text):
    result = sentiment_pipeline(text[:512])[0]
    return (result['label'], result['score'], 0.95)
```

### Add More Data Sources
```python
# In producers/:
# - twitter_producer.py (X/Twitter API)
# - hackernews_producer.py (HN API)
# - productHunt_producer.py (PH API)
```

### Change Aggregation Window
In `spark_streaming_job.py`:
```python
.groupBy(
    window(col("created_at"), "5 minutes"),  # Was "1 minute"
    ...
)
```

### Customize Colors
In `streamlit_dashboard.py`, modify the color scheme:
```python
colors_map = {
    'POSITIVE': '#00ff00',
    'NEUTRAL': '#cccccc', 
    'NEGATIVE': '#ff0000'
}
```

## 🐛 Troubleshooting

### Docker Issues
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f [service_name]

# Restart specific service
docker-compose restart [service_name]
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql -h localhost -U aries_user -d aries_db -c "SELECT 1"

# Check data in database
psql -h localhost -U aries_user -d aries_db -c \
  "SELECT COUNT(*) FROM raw.posts;"
```

### Kafka Issues
```bash
# List topics
docker exec aries-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check messages
docker exec aries-kafka kafka-console-consumer \
  --topic reddit-raw \
  --from-beginning \
  --bootstrap-server localhost:9092 | head -5
```

### Streamlit Issues
```bash
# Clear cache
rm -rf ~/.streamlit/cache

# Restart
pkill -f streamlit
streamlit run streamlit_dashboard.py
```

See `QUICK_START.md` for more troubleshooting tips.

## 🚀 Deployment

### Local Deployment (Development)
Already included! Just run Docker containers locally.

### Cloud Deployment (AWS/GCP/Azure)
```bash
# 1. Containerize Spark jobs
docker build -t aries-spark:1.0 -f Dockerfile.spark .

# 2. Deploy to Kubernetes
kubectl apply -f k8s/kafka.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/spark.yaml
kubectl apply -f k8s/streamlit.yaml

# 3. Use managed services
# - Kafka → Confluent Cloud
# - PostgreSQL → AWS RDS / Google Cloud SQL
# - MinIO → AWS S3 / Google Cloud Storage
```

## 📚 Learning Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **PySpark Guide**: https://spark.apache.org/docs/latest/api/python/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Apache Kafka**: https://kafka.apache.org/documentation
- **VADER Sentiment**: https://github.com/cjhutto/vaderSentiment

## 🤝 Contributing

Contributions welcome! Areas to expand:
- [ ] Additional data sources (Twitter, Hacker News, etc.)
- [ ] Advanced NLP models (BERT, GPT-based)
- [ ] Real-time alerting (Slack, Email, SMS)
- [ ] Machine learning predictions
- [ ] Advanced UI features
- [ ] Mobile app
- [ ] API layer

## 📄 License

MIT License - See LICENSE file for details

## 👨‍💻 Author

Built as a comprehensive data engineering project showcasing:
- Real-time streaming architecture
- Distributed processing with Spark
- Database design & optimization
- Interactive dashboard development
- DevOps & containerization

## ⭐ Key Learnings

After building this project, you'll understand:
1. Real-time streaming pipelines (Kafka)
2. Distributed data processing (Spark)
3. NLP & sentiment analysis
4. Data visualization (Streamlit, Plotly)
5. Database design & optimization
6. Docker & container orchestration
7. Production deployment strategies

## 📞 Support

- **Questions?** Check the documentation files
- **Issues?** See QUICK_START.md troubleshooting
- **Contributions?** Submit a PR!

---

**Version**: 1.0.0  
**Last Updated**: January 2025  
**Status**: ✅ Production Ready

**Happy building! 🚀**
