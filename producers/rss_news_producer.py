#!/usr/bin/env python3
"""
ARIES RSS News Producer - Streams real-time news to Kafka
Replaces reddit_producer.py
"""
import feedparser
import json
import time
import logging
from kafka import KafkaProducer
from datetime import datetime
import signal
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

# List of brands to monitor via Google News RSS feeds
BRANDS_TO_MONITOR = ["Apple", "Tesla", "Amazon", "Nike", "Coca-Cola", "Samsung", "Microsoft"]

# Generate Google News RSS feeds for each brand
RSS_FEEDS = [
    f"https://news.google.com/rss/search?q={brand}&hl=en-US&gl=US&ceid=US:en"
    for brand in BRANDS_TO_MONITOR
]

# Kafka config
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
TOPIC = 'aries-raw-posts'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RSSNewsProducer:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3,
            acks='all'
        )
        self.processed_urls = set()
        
    
    def parse_rss_feed(self, feed_url):
        """Parse RSS feed and extract new articles"""
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            
            for entry in feed.entries[:10]:  # Latest 10 articles
                article_id = entry.get('id', entry.link)
                
                if article_id in self.processed_urls:
                    continue
                
                article = {
                    'post_id': article_id,
                    'source': feed.feed.get('title', 'google_news').split(' - ')[-1], # Extract source (e.g., 'Google News')
                    'title': entry.get('title', ''),
                    'content': entry.get('summary', entry.get('description', '')),
                    'author': entry.get('author', feed.feed.get('author', '')),
                    'url': entry.get('link', ''),
                    'created_at': entry.get('published', entry.get('updated', '')),
                    'ingested_at': datetime.now().isoformat(),
                    'raw_metadata': {
                        'feed_url': feed_url,
                        'feed_title': feed.feed.get('title', ''),
                        'brand_monitored': feed_url.split('q=')[1].split('&')[0] # Extract brand from URL
                    }
                }
                articles.append(article)
                self.processed_urls.add(article_id)
            
            return articles
        except Exception as e:
            logger.error(f"Error parsing {feed_url}: {e}")
            return []
    
    def send_to_kafka(self, articles):
        """Send articles to Kafka"""
        for article in articles:
            try:
                self.producer.send(TOPIC, value=article)
                logger.info(f"Sent: {article['title'][:50]}...")
            except Exception as e:
                logger.error(f"Kafka send error: {e}")
        
        self.producer.flush()
    
    def run(self):
        """Main polling loop"""
        logger.info("🚀 Starting RSS News Producer...")
        logger.info(f"Monitoring {len(RSS_FEEDS)} news feeds...")
        
        while True:
            all_articles = []
            
            for feed_url in RSS_FEEDS:
                articles = self.parse_rss_feed(feed_url)
                all_articles.extend(articles)
                time.sleep(0.5)  # Rate limiting
            
            if all_articles:
                self.send_to_kafka(all_articles)
                logger.info(f"Processed {len(all_articles)} new articles")
            else:
                logger.info("No new articles found")
            
            time.sleep(60)  # Poll every 60 seconds

def signal_handler(sig, frame):
    logger.info("Shutting down RSS producer...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    producer = RSSNewsProducer()
    try:
        producer.run()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
