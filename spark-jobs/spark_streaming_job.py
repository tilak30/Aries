"""
Spark Structured Streaming Job for Real-Time Sentiment Analysis - FIXED VERSION
Reads from Kafka → VADER Sentiment → 1-minute windows → PostgreSQL
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, when, window, avg, count,
    to_timestamp, current_timestamp, explode, split, udf
)
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, ArrayType
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
import shutil

# ============================================================================
# CONFIGURATION
# ============================================================================

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "aries-raw-posts"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_DB = "aries_db"
POSTGRES_USER = "aries_user"
POSTGRES_PASSWORD = "aries_password"
CHECKPOINT_DIR = "/tmp/aries-checkpoint"

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZE SPARK SESSION
# ============================================================================

spark = SparkSession \
    .builder \
    .appName("AriesStreamingSentiment") \
    .config("spark.sql.shuffle.partitions", "4") \
    .config("spark.streaming.kafka.maxRatePerPartition", "100000") \
    .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR) \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# ============================================================================
# SENTIMENT ANALYSIS FUNCTION (VADER)
# ============================================================================

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    """
    Analyze sentiment using VADER (Valence Aware Dictionary and sEntiment Reasoner)
    Returns tuple: (sentiment_label, sentiment_score, confidence)
    """
    if text is None or len(str(text).strip()) == 0:
        return ("NEUTRAL", 0.5, 0.0)

    try:
        scores = analyzer.polarity_scores(str(text))
        compound = scores['compound']  # Range: -1 (negative) to +1 (positive)

        # Convert compound score (-1 to 1) to 0-1 scale
        normalized_score = (compound + 1) / 2

        # Classify sentiment
        if compound >= 0.05:
            label = "POSITIVE"
        elif compound <= -0.05:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        confidence = max(scores['pos'], scores['neu'], scores['neg'])

        return (label, normalized_score, confidence)

    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return ("NEUTRAL", 0.5, 0.0)

# Register as Spark UDF
sentiment_schema = StructType([
    StructField("sentiment_label", StringType()),
    StructField("sentiment_score", DoubleType()),
    StructField("confidence", DoubleType())
])

sentiment_udf = udf(analyze_sentiment, sentiment_schema)

# ============================================================================
# TOPIC EXTRACTION FUNCTION
# ============================================================================

topic_keywords = {
    "Customer Service": ["customer service", "support", "help", "response", "complaint"],
    "Pricing": ["price", "cost", "expensive", "affordable", "cheap"],
    "Product Quality": ["quality", "durability", "defect", "broken", "recall", "performance"],
    "Shipping": ["shipping", "delivery", "package", "arrived", "tracking"],
    "Innovation": ["innovation", "new feature", "update", "software", "design"],
    "Corporate": ["earnings", "stock", "CEO", "leadership", "acquisition"],
    "Marketing": ["advertisement", "campaign", "sponsorship", "brand image"],
    "Environment": ["sustainability", "green", "carbon", "environmental"]
}

def extract_topics(text):
    """Extract topics from text based on keywords"""
    if text is None:
        return []

    text_lower = str(text).lower()
    found_topics = []

    for topic, keywords in topic_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_topics.append(topic)
                break

    return found_topics

topics_udf = udf(extract_topics, ArrayType(StringType()))

# ============================================================================
# READ FROM KAFKA
# ============================================================================

logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")

kafka_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

logger.info("✅ Connected to Kafka")

# ============================================================================
# PARSE JSON MESSAGES
# ============================================================================

# Define schema for JSON messages from Kafka
message_schema = StructType([
    StructField("post_id", StringType()),
    StructField("source", StringType()),
    StructField("title", StringType()),
    StructField("content", StringType()),
    StructField("author", StringType()),
    StructField("url", StringType()),
    StructField("created_at", StringType()),
    StructField("raw_metadata", StructType([StructField("brand_monitored", StringType())]))
])

parsed_df = kafka_df \
    .select(from_json(col("value").cast("string"), message_schema).alias("data")) \
    .select("data.*") \
    .withColumn("created_at", to_timestamp(col("created_at"))) \
    .withColumn("ingested_at", current_timestamp())

parsed_df = parsed_df.withColumn("brand", col("raw_metadata.brand_monitored"))

# ============================================================================
# SENTIMENT ANALYSIS
# ============================================================================

sentiment_df = parsed_df \
    .withColumn("sentiment", sentiment_udf(col("content"))) \
    .select(
        col("post_id"),
        col("source"),
        col("title"),
        col("brand"),
        col("content"),
        col("author"),
        col("url"),
        col("created_at"),
        col("ingested_at"),
        col("sentiment.sentiment_label"),
        col("sentiment.sentiment_score"),
        col("sentiment.confidence")
    )

# ============================================================================
# AGGREGATED STATISTICS (1-minute windows) - FIXED: Added closing parenthesis
# ============================================================================

aggregated_df = sentiment_df \
    .withWatermark("created_at", "10 minutes") \
    .groupBy(
        window(col("created_at"), "1 minute"),
        col("sentiment_label"),
        col("source")
    ) \
    .agg(
        count("*").alias("count"),
        avg("sentiment_score").alias("avg_sentiment_score")
    ) \
    .select(
        col("window.start").alias("hour_bucket"),
        col("sentiment_label"),
        col("count"),
        col("avg_sentiment_score"),
        col("source")
    )  # ✅ FIXED: Added closing parenthesis

# ============================================================================
# WRITE TO POSTGRESQL (DETAILED RECORDS) - FIXED
# ============================================================================

def write_to_postgres_batch(df, epoch_id):
    """Write with DEDUPLICATION - handles Kafka retries"""
    try:
        if df.count() == 0:
            logger.info(f"Batch {epoch_id}: No data")
            return

        jdbc_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        
        # 1. Deduplicate
        dedup_df = df.dropDuplicates(["post_id"])
        
        # 2. Add Analysis Timestamp (This will be used for the topic and sentiment analysis time)
        final_df = dedup_df.withColumn("analyzed_at", current_timestamp())
        
        logger.info(f"Batch {epoch_id}: {df.count()} → {final_df.count()} unique posts")

        # --- SENTIMENT ANALYSIS WRITE (Table: processed.sentiment_analysis) ---
        # The column list matches the DB schema: post_id, content, ..., analyzed_at, created_at (Source Post Time)
        final_df.select(
            col("post_id"),
            col("content"),
            col("sentiment_label"),
            col("sentiment_score"),
            col("confidence"),
            col("source"),
            col("brand"),
            # col("analyzed_at").alias("analysis_timestamp"), # Alias to avoid confusion
            col("analyzed_at"),                              # Use the correct column name
            col("created_at")                               # ✅ This is the original 'created_at' (Post Creation Time)
        ).write.mode("append").format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "processed.sentiment_analysis") \
            .option("user", POSTGRES_USER) \
            .option("password", POSTGRES_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .save()

        # --- TOPIC ANALYSIS WRITE (Table: processed.topic_analysis) ---
        topic_df = final_df \
            .withColumn("extracted_topics", topics_udf(col("content"))) \
            .withColumn("topic", explode(col("extracted_topics"))) \
            .filter(col("topic").isNotNull())
        
        # The topic_df still contains 'created_at' and 'analyzed_at' from final_df
        if topic_df.count() > 0:
            topic_df.select(
                col("post_id"),
                col("topic"),
                col("brand"),
                col("sentiment_score"),
                col("confidence"),
                col("analyzed_at"),                      # ✅ Analysis time
                col("created_at")                        # ✅ Original post creation time
            ).write.mode("append").format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", "processed.topic_analysis") \
                .option("user", POSTGRES_USER) \
                .option("password", POSTGRES_PASSWORD) \
                .option("driver", "org.postgresql.Driver") \
                .save()

        logger.info(f"✅ Batch {epoch_id}: {final_df.count()} UNIQUE posts WRITTEN!")

    except Exception as e:
        logger.error(f"Batch {epoch_id}: Error: {e}")

# ============================================================================
# WRITE TO CONSOLE (FOR MONITORING)
# ============================================================================

console_query = sentiment_df \
    .select(
        col("post_id"),
        col("source"),
        col("title"),
        col("sentiment_label"),
        col("sentiment_score"),
        col("created_at")
    ) \
    .writeStream \
    .format("console") \
    .option("truncate", False) \
    .option("numRows", 5) \
    .start()

logger.info("✅ Started console stream")

# ============================================================================
# START STREAMING QUERY
# ============================================================================

logger.info("🚀 Starting Aries Streaming Sentiment Analysis...")
logger.info(f" Kafka Broker: {KAFKA_BOOTSTRAP_SERVERS}")
logger.info(f" Kafka Topic: {KAFKA_TOPIC}")
logger.info(f" PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

# Clear checkpoint directory to avoid schema mismatch issues
if os.path.exists(CHECKPOINT_DIR):
    logger.warning(f"Removing previous checkpoint directory: {CHECKPOINT_DIR}")
    try:
        shutil.rmtree(CHECKPOINT_DIR)
        logger.info("✅ Checkpoint directory removed.")
    except Exception as e:
        logger.error(f"Failed to remove checkpoint directory: {e}")

streaming_query = sentiment_df \
    .writeStream \
    .foreachBatch(write_to_postgres_batch) \
    .option("checkpointLocation", CHECKPOINT_DIR) \
    .start()

logger.info("✅ Streaming query started")
logger.info(" Listening for messages... (Ctrl+C to stop)")

# Wait for termination
try:
    streaming_query.awaitTermination()
except KeyboardInterrupt:
    logger.info("🛑 Stopping streaming query...")
    streaming_query.stop()
    logger.info("✅ Stopped")