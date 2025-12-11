import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np


# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================


st.set_page_config(
    page_title="Aries - Brand Intelligence Platform",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS for beautiful styling
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        --primary-color: #1f77b4;
        --secondary-color: #ff7f0e;
        --positive-color: #2ca02c;
        --danger-color: #d62728;
        --dark-bg: #0e1117;
        --card-bg: #1a1f36;
    }
    
    .main {
        background: linear-gradient(135deg, #0e1117 0%, #1a1f36 100%);
    }
    
    .metric-card {
        background: var(--card-bg);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #2a2f4d;
        color: white;
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .sentiment-positive { color: var(--positive-color); }
    .sentiment-neutral { color: #7f7f7f; }
    .sentiment-negative { color: var(--danger-color); }
    
    .chart-container {
        background: #1a1f36;
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #2a2f4d;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    h1, h2, h3 {
        color: #fafafa;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    
    .status-live {
        background: linear-gradient(135deg, var(--positive-color) 0%, #1f8020 100%);
        color: white;
    }
    
    .status-critical {
        background: linear-gradient(135deg, #d62728 0%, #a01f1f 100%);
        color: white;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# DATABASE CONNECTION (WITH CACHING)
# ============================================================================


def get_db_connection():
    """Create persistent database connection"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            dbname="aries_db",
            user="aries_user",
            password="aries_password",
            port=5432
        )
        return conn
    except psycopg2.Error as e:
        st.error(f"❌ Database Connection Error: {e}")
        return None


@st.cache_data(ttl=30)
def fetch_sentiment_overview(brand, hours=24):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT 
                    sentiment_label,
                    COUNT(*) AS count,
                    ROUND(AVG(sentiment_score)::numeric, 3) AS avg_score,
                    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER())::numeric, 1) AS percentage
                FROM processed.sentiment_analysis
                WHERE analyzed_at >= NOW() - INTERVAL '{hours} hours' AND brand = '{brand}'
                GROUP BY sentiment_label
                ORDER BY count DESC;
            """, (brand, hours))
            return pd.DataFrame(cur.fetchall())
    except Exception as e:
        st.warning(f"⚠️ Query failed: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()



@st.cache_data(ttl=30)
def fetch_sentiment_timeseries(brand, hours=24):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT 
                    DATE_TRUNC('hour', analyzed_at) as hour,
                    sentiment_label,
                    COUNT(*) as count,
                    ROUND(AVG(sentiment_score)::numeric, 3) as avg_score
                FROM processed.sentiment_analysis
                WHERE analyzed_at >= NOW() - INTERVAL '{hours} hours' AND brand = '{brand}'
                GROUP BY DATE_TRUNC('hour', analyzed_at), sentiment_label
                ORDER BY hour DESC;
            """, (brand, hours))
            return pd.DataFrame(cur.fetchall())
    except Exception as e:
        st.warning(f"⚠️ Time-series query failed: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=30)
def fetch_top_topics(brand, hours=24, limit=10):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    t.topic,
                    COUNT(t.post_id) as mentions,
                    ROUND(AVG(s.sentiment_score)::numeric, 3) as avg_sentiment
                FROM processed.topic_analysis t
                JOIN processed.sentiment_analysis s ON t.post_id = s.post_id
                WHERE s.analyzed_at >= NOW() - INTERVAL '%s hours' AND s.brand = %s
                GROUP BY t.topic
                ORDER BY mentions DESC
                LIMIT %s;
            """, (hours, brand, limit))
            return pd.DataFrame(cur.fetchall())
    except Exception as e:
        st.warning(f"⚠️ Topics query failed: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=30)
def fetch_anomalies(brand, hours=24, limit=5):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    detected_at,
                    sentiment_drop_percentage,
                    severity,
                    description
                FROM analytics.anomalies
                WHERE detected_at >= NOW() - INTERVAL '%s hours' AND affected_topic LIKE %s
                ORDER BY detected_at DESC
                LIMIT %s;
            """, (hours, f"%{brand}%", limit))
            return pd.DataFrame(cur.fetchall())
    except Exception as e:
        st.warning(f"⚠️ Anomalies query failed: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=30)
def fetch_negative_mentions(brand, hours=24, limit=10):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT post_id, content, sentiment_score, source, analyzed_at as created_at
                FROM processed.sentiment_analysis
                WHERE sentiment_label = 'NEGATIVE'
                    AND analyzed_at >= NOW() - INTERVAL '%s hours' AND brand = %s
                ORDER BY sentiment_score ASC, analyzed_at DESC
                LIMIT %s;
            """, (hours, brand, limit))

            return pd.DataFrame(cur.fetchall())
    except Exception as e:
        st.warning(f"⚠️ Negative mentions query failed: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

@st.cache_data(ttl=300)
def get_available_brands():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT brand FROM processed.sentiment_analysis
                WHERE brand IS NOT NULL ORDER BY brand;
            """)
            brands = [row[0] for row in cur.fetchall()]
            return brands if brands else ["Apple", "Tesla", "Amazon"] # Fallback for demo
    except Exception:
        return ["Apple", "Tesla", "Amazon"] # Fallback for demo
    finally:
        if conn:
            conn.close()

# ============================================================================
# DEMO DATA GENERATOR (For testing without real database)
# ============================================================================


def generate_demo_data():
    """Generate realistic demo data for testing"""
    np.random.seed(42)
    
    # Generate sentiment overview
    sentiment_data = pd.DataFrame({
        'sentiment_label': ['POSITIVE', 'NEUTRAL', 'NEGATIVE'],
        'count': [324, 156, 45],
        'avg_score': [0.89, 0.52, 0.12],
        'percentage': [62.3, 30.0, 8.7]
    })
    
    # Generate time-series data (last 24 hours)
    hours = pd.date_range(end=datetime.now(), periods=24, freq='H')
    timeseries_data = []
    for hour in hours:
        for sentiment in ['POSITIVE', 'NEUTRAL', 'NEGATIVE']:
            count = np.random.randint(10, 100)
            timeseries_data.append({
                'hour': hour,
                'sentiment_label': sentiment,
                'count': count,
                'avg_score': np.random.uniform(0.1, 0.9)
            })
    timeseries_df = pd.DataFrame(timeseries_data)
    
    # Generate topics
    topics_data = pd.DataFrame({
        'topic': ['Customer Service', 'Product Quality', 'Pricing', 'Shipping', 'Returns Policy', 'Battery Life', 'Design', 'Performance'],
        'mentions': [145, 98, 87, 65, 43, 52, 38, 29],
        'avg_sentiment': [0.45, 0.72, 0.38, 0.55, 0.62, 0.81, 0.88, 0.79]
    })
    
    # Generate anomalies
    anomalies_data = pd.DataFrame({
        'detected_at': pd.date_range(end=datetime.now(), periods=3, freq='6H'),
        'sentiment_drop_percentage': [15.3, 8.7, 22.1],
        'severity': ['MEDIUM', 'LOW', 'HIGH'],
        'description': [
            'Sudden drop in positive mentions on Reddit',
            'Slight decrease in sentiment for "Customer Service" topic',
            'Critical: Major complaint thread about product defects'
        ]
    })
    
    # Generate negative mentions
    negative_mentions = pd.DataFrame({
        'post_id': [f'post_{i}' for i in range(15)],
        'content': [
            'Absolutely disappointed with my purchase. Poor quality and broke within a week.',
            'Terrible customer service. Been waiting 3 weeks for a response.',
            'Price is way too high for what you get. Found better elsewhere.',
            'Shipping took forever and the product arrived damaged.',
            'The new update completely broke the app functionality.',
            'Worst experience ever. Never buying from them again.',
            'Battery dies in 2 hours. Not impressed at all.',
            'Misleading product description. Does not work as advertised.',
            'Refund process is a nightmare. They keep ignoring my requests.',
            'Design feels cheap and flimsy. Not worth the money.',
            'Multiple defects right out of the box. Quality control is non-existent.',
            'Customer support is useless. They don\'t actually help.',
            'Worse than the previous version. Why would they remove useful features?',
            'The app crashes constantly. Very frustrating.',
            'Paid premium price for what feels like a budget product.'
        ],
        'sentiment_score': np.random.uniform(0.05, 0.35, 15),
        'source': ['reddit'] * 15,
        'created_at': pd.date_range(end=datetime.now(), periods=15, freq='1H')
    })
    
    return sentiment_data, timeseries_df, topics_data, anomalies_data, negative_mentions


# ============================================================================
# MAIN APP
# ============================================================================


def main():
    # Header with branding
    col1, col2 = st.columns([1, 10])
    # with col1:
    #     st.image("your_logo.png", width=70) # Optional: Add a logo
    
    st.title("💡 Aries Brand Intelligence")

    st.markdown("---")
    
    # Sidebar - Controls
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Data source toggle
        use_demo = st.toggle("Use Demo Data", value=False, help="If enabled, uses pre-generated data instead of the live database.")
        
        # Brand selector
        available_brands = get_available_brands()
        selected_brand = st.selectbox(
            "Select a Brand to Analyze:",
            available_brands,
            index=0
        )
        
        # Time range selector
        time_range_map = {"Last 24 Hours": 24, "Last 7 Days": 168, "Last 30 Days": 720}
        time_range_label = st.selectbox(
            "Select Time Range:",
            time_range_map.keys()
        )
        time_range_hours = time_range_map[time_range_label]
        
        # System status
        st.markdown("---")
        st.subheader("System Status")
        
        # A simple check to see if we can connect to the DB
        conn = get_db_connection()
        if conn:
            st.success("● LIVE: Connected to Database")
            conn.close()
        else:
            st.error("● OFFLINE: Database Connection Failed")

        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    # ============================================================================
    # DATABASE CONNECTION & DATA LOADING - FIXED CALLS
    # ============================================================================
    
    if use_demo:
        st.info("📊 Running with **Demo Data**. Toggle off in the sidebar to connect to the live database.")
        sentiment_overview, timeseries_df, topics_df, anomalies_df, negative_mentions_df = generate_demo_data()
    else:
        sentiment_overview = fetch_sentiment_overview(selected_brand, time_range_hours)
        timeseries_df = fetch_sentiment_timeseries(selected_brand, time_range_hours)
        topics_df = fetch_top_topics(selected_brand, time_range_hours)
        anomalies_df = fetch_anomalies(selected_brand, time_range_hours)
        negative_mentions_df = fetch_negative_mentions(selected_brand, time_range_hours)
    
    st.header(f"Dashboard for: **{selected_brand}**")
    
    # ============================================================================
    # SECTION 1: KEY METRICS (KPI Cards)
    # ============================================================================
    
    if not sentiment_overview.empty:
        col1, col2, col3 = st.columns(3)
        
        # Overall Sentiment Score
        with col1:
            overall_score = sentiment_overview['avg_score'].mean()
            sentiment_color = "🟢" if overall_score > 0.6 else "🟡" if overall_score > 0.4 else "🔴"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Avg. Sentiment Score</div>
                <div class="metric-value">{sentiment_color} {overall_score:.2f}</div>
                <small>Scale: 0.0 (Negative) to 1.0 (Positive)</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Total Posts Analyzed
        with col2:
            total_posts = sentiment_overview['count'].sum()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Mentions Analyzed</div>
                <div class="metric-value">{total_posts:,}</div>
                <small>In the last {time_range_label.lower()}</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Positive Sentiment %
        with col3:
            positive_row = sentiment_overview[sentiment_overview['sentiment_label'] == 'POSITIVE']
            positive_pct = positive_row['percentage'].iloc[0] if not positive_row.empty else 0.0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Positive Sentiment</div>
                <div class="metric-value">{positive_pct:.1f}%</div>
                <small>Percentage of all mentions</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"No data found for **{selected_brand}** in the selected time range. Please select another brand or time range.")
    
    st.markdown("---")
    
    # ============================================================================
    # SECTION 2: SENTIMENT DISTRIBUTION & TRENDS
    # ============================================================================
    
    col1, col2 = st.columns(2)
    
    # Sentiment Distribution (Pie Chart)
    with col1:
        st.subheader(f"📊 Sentiment Distribution")
        if not sentiment_overview.empty:
            fig_pie = go.Figure(data=[go.Pie(
                labels=sentiment_overview['sentiment_label'],
                values=sentiment_overview['count'],
                marker=dict( # Use the CSS variables
                    colors=['#2ca02c', '#7f7f7f', '#d62728'],
                    line=dict(color='#0e1117', width=2)
                ),
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>',
                textinfo='label+percent'
            )])
            fig_pie.update_layout(
                template='plotly_dark',
                showlegend=True,
                paper_bgcolor='rgba(26, 31, 54, 0)',
                plot_bgcolor='rgba(26, 31, 54, 0)',
                font=dict(color='white', size=12),
                height=400
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No sentiment distribution data to display.")
    
    # Sentiment Trend Over Time (Line Chart)
    with col2:
        st.subheader(f"📈 Sentiment Trend")
        if not timeseries_df.empty:
            pivot_df = timeseries_df.pivot_table(
                index='hour',
                columns='sentiment_label',
                values='count',
                aggfunc='sum',
                fill_value=0
            )
            
            fig_line = go.Figure()
            
            colors_map = {'POSITIVE': '#2ca02c', 'NEUTRAL': '#7f7f7f', 'NEGATIVE': '#d62728'}
            for column in pivot_df.columns:
                fig_line.add_trace(go.Scatter(
                    x=pivot_df.index,
                    y=pivot_df[column],
                    mode='lines+markers',
                    name=column,
                    line=dict(color=colors_map.get(column, '#1f77b4'), width=3),
                    fill='tozeroy' if column == list(pivot_df.columns)[0] else None,
                    hovertemplate='<b>%{fullData.name}</b><br>Time: %{x}<br>Count: %{y}<extra></extra>'
                ))
            
            fig_line.update_layout(
                template='plotly_dark',
                title_x=0.5,
                paper_bgcolor='rgba(26, 31, 54, 0)',
                plot_bgcolor='rgba(26, 31, 54, 0)',
                font=dict(color='white', size=12),
                hovermode='x unified',
                height=400,
                xaxis_title='Time',
                yaxis_title='Count'
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No time-series data to display.")
    
    st.markdown("---")
    
    # ============================================================================
    # SECTION 3: TRENDING TOPICS & ANOMALIES
    # ============================================================================
    
    col1, col2 = st.columns([1.2, 0.8])
    
    # Top Topics
    with col1:
        st.subheader("🔥 Key Topics")
        if not topics_df.empty:
            topics_df_sorted = topics_df.sort_values('mentions', ascending=True)
            
            fig_topics = go.Figure(data=[
                go.Bar(
                    y=topics_df_sorted['topic'],
                    x=topics_df_sorted['mentions'],
                    orientation='h',
                    marker=dict(
                        color=topics_df_sorted['avg_sentiment'],
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title="Avg Sentiment", thickness=15)
                    ),
                    text=topics_df_sorted['mentions'],
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>Mentions: %{x}<br>Avg Sentiment: %{marker.color:.2f}<extra></extra>'
                )
            ])
            
            fig_topics.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(26, 31, 54, 0)',
                plot_bgcolor='rgba(26, 31, 54, 0)',
                font=dict(color='white', size=11),
                height=400,
                xaxis_title='Mention Count',
                margin=dict(l=150)
            )
            st.plotly_chart(fig_topics, use_container_width=True)
        else:
            st.info("No topic data to display.")
    
    # Anomalies Alert
    with col2:
        st.subheader("⚠️ Anomalies Detected")
        if not anomalies_df.empty:
            for idx, row in anomalies_df.head(5).iterrows():
                severity_emoji = "🔴" if row['severity'] == 'HIGH' else "🟡" if row['severity'] == 'MEDIUM' else "🟢"
                with st.container():
                    st.markdown(f"""
                    **{severity_emoji} {row['severity']} - {row['detected_at'].strftime('%H:%M')}**
                    
                    {row['description']}
                    
                    Drop: **{row['sentiment_drop_percentage']:.1f}%**
                    """)
                    st.divider()
        else:
            st.success("✅ No significant sentiment anomalies detected.")
    
    st.markdown("---")
    
    # ============================================================================
    # SECTION 4: TOP NEGATIVE MENTIONS (PR ALERT FEED)
    # ============================================================================
    
    st.subheader("🚨 Latest Negative Mentions")
    
    if not negative_mentions_df.empty:
        for idx, row in negative_mentions_df.head(10).iterrows():
            # Color intensity based on negativity
            severity = "CRITICAL" if row['sentiment_score'] < 0.2 else "HIGH" if row['sentiment_score'] < 0.3 else "MEDIUM"
            severity_emoji = "🔴" if severity == "CRITICAL" else "🟠" if severity == "HIGH" else "🟡"
            color_code = "#d62728" if severity == "CRITICAL" else "#ff7f0e" if severity == "HIGH" else "#ffcc00"
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, rgba(214, 39, 40, 0.1) 0%, rgba(214, 39, 40, 0.05) 100%);
                border-left: 4px solid {color_code};
                padding: 1rem;
                margin: 0.5rem 0;
                border-radius: 8px;
                backdrop-filter: blur(10px);
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <span style="font-weight: bold; color: white;">
                        {severity_emoji} {severity} - ID: {row['post_id']}
                    </span>
                    <span style="color: #888; font-size: 0.8rem;">
                        {row['created_at'].strftime('%Y-%m-%d %H:%M')} • {row['source'].upper()}
                    </span>
                </div>
                <div style="color: #ccc; font-size: 0.95rem; line-height: 1.5; margin: 0.5rem 0;">
                    "{row['content']}"
                </div>
                <div style="color: #888; font-size: 0.8rem; margin-top: 0.5rem;">
                    Sentiment Score: <span style="color: {color_code}; font-weight: bold;">{row['sentiment_score']:.3f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success(f"✅ No negative mentions found for **{selected_brand}** in the last {time_range_label.lower()}.")
    
    st.markdown("---")
    
    # Footer
    st.markdown("""
    <div style="text-align: center; color: #888; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #2a2f4d;">
        <small>🔮 <strong>Aries Platform v2.0</strong> • Real-Time Brand Intelligence</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
