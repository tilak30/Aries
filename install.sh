#!/bin/bash
# ============================================================================
# ARIES PLATFORM - AUTOMATED INSTALLATION SCRIPT
# ============================================================================
# This script automates the complete Aries setup process
# Usage: bash install.sh
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${BLUE}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================================
# SYSTEM CHECKS
# ============================================================================

check_requirements() {
    print_header "CHECKING SYSTEM REQUIREMENTS"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker found: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        echo "Install from: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_success "Docker Compose found: $(docker-compose --version)"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version)
    print_success "Python found: $PYTHON_VERSION"
    
    # Check git (optional)
    if command -v git &> /dev/null; then
        print_success "Git found: $(git --version)"
    else
        print_warning "Git not found (optional)"
    fi
    
    # Check if Docker daemon is running
    if ! docker ps &> /dev/null; then
        print_error "Docker daemon is not running"
        echo "Start Docker and try again"
        exit 1
    fi
    print_success "Docker daemon is running"
}

# ============================================================================
# PROJECT SETUP
# ============================================================================

setup_directories() {
    print_header "SETTING UP PROJECT DIRECTORIES"
    
    # Create main directories
    mkdir -p docker
    mkdir -p configs
    mkdir -p spark-jobs
    mkdir -p producers
    mkdir -p streamlit-app
    mkdir -p logs
    mkdir -p data-lake
    
    print_success "Project directories created"
}

setup_env_file() {
    print_header "SETTING UP ENVIRONMENT VARIABLES"
    
    if [ -f .env ]; then
        print_warning ".env file already exists, skipping..."
        return
    fi
    
    cat > .env << 'EOF'
# ============================================================================
# ARIES PLATFORM - ENVIRONMENT CONFIGURATION
# ============================================================================

# Reddit API Credentials
# Get from: https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=Aries:1.0 (by /u/your_username)

# PostgreSQL Configuration
POSTGRES_USER=aries_user
POSTGRES_PASSWORD=aries_password
POSTGRES_DB=aries_db
POSTGRES_PORT=5432

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_RAW=reddit-raw
KAFKA_TOPIC_PROCESSED=processed-sentiment

# MinIO Configuration
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001

# Spark Configuration
SPARK_MASTER=local[*]
SPARK_HOME=/usr/local/spark

# Streamlit Configuration
STREAMLIT_PORT=8501
STREAMLIT_SERVER_HEADLESS=true

# System Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
EOF
    
    print_success ".env file created"
    print_warning "IMPORTANT: Edit .env and add your Reddit API credentials!"
}

# ============================================================================
# DOCKER INFRASTRUCTURE
# ============================================================================

setup_docker() {
    print_header "STARTING DOCKER INFRASTRUCTURE"
    
    # Check if services are already running
    if docker ps | grep -q "aries-kafka"; then
        print_warning "Aries services already running"
        read -p "Restart them? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Restarting services..."
            cd docker
            docker-compose restart
            cd ..
        fi
    else
        print_info "Starting Docker services (this may take 1-2 minutes)..."
        cd docker
        docker-compose up -d
        cd ..
        
        # Wait for services to be healthy
        print_info "Waiting for services to be healthy..."
        sleep 10
        
        # Check service status
        print_info "Checking service status..."
        for i in {1..30}; do
            if docker exec aries-postgres pg_isready -U aries_user &> /dev/null; then
                print_success "PostgreSQL is ready!"
                break
            fi
            if [ $i -eq 30 ]; then
                print_error "PostgreSQL failed to start"
                exit 1
            fi
            echo -n "."
            sleep 1
        done
    fi
    
    print_success "All Docker services are running"
    docker-compose ps
}

# ============================================================================
# PYTHON ENVIRONMENT
# ============================================================================

setup_python_env() {
    print_header "SETTING UP PYTHON ENVIRONMENT"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --quiet --upgrade pip setuptools wheel
    
    # Install requirements
    print_info "Installing Python dependencies (this may take 2-3 minutes)..."
    pip install --quiet -r requirements.txt
    
    print_success "Python environment ready"
}

# ============================================================================
# DATABASE SETUP
# ============================================================================

setup_database() {
    print_header "INITIALIZING DATABASE"
    
    print_info "Creating PostgreSQL schema..."
    
    # Check if table already exists
    if docker exec aries-postgres psql -U aries_user -d aries_db \
        -c "SELECT to_regclass('raw.posts');" 2>/dev/null | grep -q "posts"; then
        print_warning "Database schema already exists"
    else
        # Load schema
        docker exec -i aries-postgres psql -U aries_user -d aries_db < configs/schema.sql
        print_success "Database schema created"
    fi
    
    # Verify
    RECORD_COUNT=$(docker exec aries-postgres psql -U aries_user -d aries_db \
        -tc "SELECT COUNT(*) FROM raw.posts;" 2>/dev/null | tr -d ' ')
    print_success "Database contains $RECORD_COUNT sample records"
}

# ============================================================================
# KAFKA SETUP
# ============================================================================

setup_kafka() {
    print_header "SETTING UP KAFKA TOPICS"
    
    print_info "Creating Kafka topics..."
    
    # Create topics
    docker exec aries-kafka kafka-topics \
        --create \
        --topic reddit-raw \
        --bootstrap-server localhost:9092 \
        --partitions 3 \
        --replication-factor 1 \
        --if-not-exists 2>/dev/null || true
    
    docker exec aries-kafka kafka-topics \
        --create \
        --topic processed-sentiment \
        --bootstrap-server localhost:9092 \
        --partitions 3 \
        --replication-factor 1 \
        --if-not-exists 2>/dev/null || true
    
    # List topics
    print_info "Available Kafka topics:"
    docker exec aries-kafka kafka-topics \
        --list \
        --bootstrap-server localhost:9092
    
    print_success "Kafka topics created"
}

# ============================================================================
# VERIFICATION
# ============================================================================

verify_installation() {
    print_header "VERIFYING INSTALLATION"
    
    local all_good=true
    
    # Check Docker containers
    print_info "Checking Docker containers..."
    if docker ps | grep -q "aries-kafka"; then
        print_success "Kafka is running"
    else
        print_error "Kafka is not running"
        all_good=false
    fi
    
    if docker ps | grep -q "aries-postgres"; then
        print_success "PostgreSQL is running"
    else
        print_error "PostgreSQL is not running"
        all_good=false
    fi
    
    if docker ps | grep -q "aries-minio"; then
        print_success "MinIO is running"
    else
        print_error "MinIO is not running"
        all_good=false
    fi
    
    # Check Python packages
    print_info "Checking Python packages..."
    if python3 -c "import streamlit" 2>/dev/null; then
        print_success "Streamlit is installed"
    else
        print_error "Streamlit is not installed"
        all_good=false
    fi
    
    if python3 -c "import pyspark" 2>/dev/null; then
        print_success "PySpark is installed"
    else
        print_error "PySpark is not installed"
        all_good=false
    fi
    
    # Check database
    print_info "Checking database..."
    if docker exec aries-postgres psql -U aries_user -d aries_db \
        -c "SELECT 1" &>/dev/null; then
        print_success "Database is accessible"
    else
        print_error "Database is not accessible"
        all_good=false
    fi
    
    if [ "$all_good" = true ]; then
        print_success "All checks passed!"
    else
        print_error "Some checks failed. See above for details."
        return 1
    fi
}

# ============================================================================
# FINAL INSTRUCTIONS
# ============================================================================

print_instructions() {
    print_header "INSTALLATION COMPLETE! 🎉"
    
    echo -e "${GREEN}"
    echo "Your Aries Platform is ready to use!"
    echo -e "${NC}"
    
    echo -e "${YELLOW}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "NEXT STEPS:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${NC}"
    
    echo -e "${BLUE}1. Update Reddit API Credentials:${NC}"
    echo "   Edit .env file with your Reddit credentials"
    echo "   Get from: https://www.reddit.com/prefs/apps"
    echo ""
    
    echo -e "${BLUE}2. Run the Dashboard (Demo Mode):${NC}"
    echo "   cd streamlit-app"
    echo "   streamlit run streamlit_dashboard.py"
    echo "   Open: http://localhost:8501"
    echo ""
    
    echo -e "${BLUE}3. (Optional) Run with Real Data:${NC}"
    echo "   Terminal 1: spark-submit \\"
    echo "     --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.1 \\"
    echo "     spark-jobs/spark_streaming_job.py"
    echo "   Terminal 2: python producers/reddit_producer.py"
    echo "   Terminal 3: streamlit run streamlit-app/streamlit_dashboard.py"
    echo ""
    
    echo -e "${BLUE}4. Useful Commands:${NC}"
    echo "   Check services: docker-compose ps"
    echo "   View logs: docker-compose logs -f postgres"
    echo "   Access pgAdmin: http://localhost:5050"
    echo "   Access MinIO: http://localhost:9001"
    echo ""
    
    echo -e "${YELLOW}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${NC}"
    
    echo -e "${GREEN}"
    echo "📚 Documentation:"
    echo "   - QUICK_START.md - Getting started guide"
    echo "   - ARIES_SETUP_GUIDE.md - Comprehensive reference"
    echo "   - FILES_SUMMARY.md - File overview"
    echo -e "${NC}"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    print_header "ARIES PLATFORM - INSTALLATION WIZARD"
    
    # Run installation steps
    check_requirements
    setup_directories
    setup_env_file
    setup_docker
    setup_python_env
    setup_database
    setup_kafka
    verify_installation
    print_instructions
}

# Run main function
main
