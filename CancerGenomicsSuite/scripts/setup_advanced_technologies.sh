#!/bin/bash

# Advanced Technologies Setup Script
# This script sets up all the advanced technologies for the Cancer Genomics Analysis Suite

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
check_system_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python version
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_success "Python $PYTHON_VERSION found"
    else
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check pip
    if command_exists pip3; then
        log_success "pip3 found"
    else
        log_error "pip3 is required but not installed"
        exit 1
    fi
    
    # Check Docker
    if command_exists docker; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        log_success "Docker $DOCKER_VERSION found"
    else
        log_warning "Docker not found. Some services will not be available"
    fi
    
    # Check Docker Compose
    if command_exists docker-compose; then
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
        log_success "Docker Compose $COMPOSE_VERSION found"
    else
        log_warning "Docker Compose not found. Some services will not be available"
    fi
    
    # Check Java (for Neo4j)
    if command_exists java; then
        JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2)
        log_success "Java $JAVA_VERSION found"
    else
        log_warning "Java not found. Neo4j may not work properly"
    fi
}

# Install Python dependencies
install_python_dependencies() {
    log_info "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_error "requirements.txt not found"
        exit 1
    fi
}

# Setup environment configuration
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f "environment.advanced.template" ]; then
            cp environment.advanced.template .env
            log_success "Environment configuration created from template"
            log_warning "Please edit .env file with your specific configuration"
        else
            log_error "environment.advanced.template not found"
            exit 1
        fi
    else
        log_info "Environment configuration already exists"
    fi
}

# Setup directories
setup_directories() {
    log_info "Creating necessary directories..."
    
    mkdir -p data/{samples,results,exports}
    mkdir -p results/{pipelines,graphs,reports}
    mkdir -p logs/{app,pipelines,graphs,kafka,oauth2}
    mkdir -p nextflow_work
    mkdir -p snakemake_work
    mkdir -p neo4j_import
    mkdir -p kafka_data
    mkdir -p ssl
    mkdir -p monitoring/{prometheus,grafana,logstash}
    
    log_success "Directories created"
}

# Setup Neo4j
setup_neo4j() {
    log_info "Setting up Neo4j..."
    
    if command_exists docker; then
        # Start Neo4j with Docker
        docker run -d \
            --name neo4j \
            -p 7474:7474 \
            -p 7687:7687 \
            -e NEO4J_AUTH=neo4j/password \
            -e NEO4J_PLUGINS='["apoc"]' \
            -e NEO4J_dbms_security_procedures_unrestricted=apoc.* \
            -v neo4j_data:/data \
            -v neo4j_logs:/logs \
            -v neo4j_import:/var/lib/neo4j/import \
            neo4j:5.15-community
        
        log_success "Neo4j started with Docker"
        log_info "Neo4j Web UI: http://localhost:7474"
        log_info "Username: neo4j, Password: password"
    else
        log_warning "Docker not available. Please install Neo4j manually"
    fi
}

# Setup Kafka
setup_kafka() {
    log_info "Setting up Apache Kafka..."
    
    if command_exists docker-compose; then
        # Create Kafka Docker Compose file
        cat > docker-compose.kafka.yml << EOF
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: true

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    depends_on:
      - kafka
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
EOF
        
        docker-compose -f docker-compose.kafka.yml up -d
        log_success "Kafka started with Docker Compose"
        log_info "Kafka UI: http://localhost:8080"
    else
        log_warning "Docker Compose not available. Please install Kafka manually"
    fi
}

# Setup Keycloak
setup_keycloak() {
    log_info "Setting up Keycloak..."
    
    if command_exists docker; then
        # Start Keycloak with Docker
        docker run -d \
            --name keycloak \
            -p 8081:8080 \
            -e KEYCLOAK_ADMIN=admin \
            -e KEYCLOAK_ADMIN_PASSWORD=admin \
            quay.io/keycloak/keycloak:23.0 \
            start-dev
        
        log_success "Keycloak started with Docker"
        log_info "Keycloak Admin Console: http://localhost:8081"
        log_info "Username: admin, Password: admin"
    else
        log_warning "Docker not available. Please install Keycloak manually"
    fi
}

# Setup Nextflow
setup_nextflow() {
    log_info "Setting up Nextflow..."
    
    if ! command_exists nextflow; then
        # Install Nextflow
        curl -s https://get.nextflow.io | bash
        sudo mv nextflow /usr/local/bin/
        log_success "Nextflow installed"
    else
        log_success "Nextflow already installed"
    fi
    
    # Verify installation
    nextflow -version
}

# Setup Snakemake
setup_snakemake() {
    log_info "Setting up Snakemake..."
    
    if ! command_exists snakemake; then
        # Install Snakemake
        pip3 install snakemake
        log_success "Snakemake installed"
    else
        log_success "Snakemake already installed"
    fi
    
    # Verify installation
    snakemake --version
}

# Create sample data
create_sample_data() {
    log_info "Creating sample data..."
    
    # Create sample gene expression data
    cat > data/samples/gene_expression.csv << EOF
gene,BRCA1,BRCA2,TP53,EGFR,MYC
BRCA1,1.0,0.8,0.6,0.3,0.2
BRCA2,0.8,1.0,0.7,0.4,0.3
TP53,0.6,0.7,1.0,0.5,0.4
EGFR,0.3,0.4,0.5,1.0,0.6
MYC,0.2,0.3,0.4,0.6,1.0
EOF
    
    # Create sample gene interactions
    cat > data/samples/gene_interactions.csv << EOF
source,target,interaction_type,confidence
BRCA1,BRCA2,protein_protein,0.9
BRCA1,TP53,protein_protein,0.8
BRCA2,TP53,protein_protein,0.7
TP53,EGFR,regulates,0.6
EGFR,MYC,regulates,0.5
EOF
    
    # Create sample mutation data
    cat > data/samples/mutations.csv << EOF
sample_id,gene,variant,type,pathogenicity
S001,BRCA1,c.5266dupC,frameshift,pathogenic
S001,BRCA2,c.5946delT,frameshift,pathogenic
S002,TP53,c.524G>A,missense,pathogenic
S002,EGFR,c.2573T>G,missense,benign
S003,MYC,c.1234C>T,synonymous,benign
EOF
    
    log_success "Sample data created"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."
    
    # Create Prometheus configuration
    cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'cancer-genomics-app'
    static_configs:
      - targets: ['localhost:5000']
  
  - job_name: 'neo4j'
    static_configs:
      - targets: ['localhost:7474']
  
  - job_name: 'kafka'
    static_configs:
      - targets: ['localhost:9092']
  
  - job_name: 'keycloak'
    static_configs:
      - targets: ['localhost:8081']
EOF
    
    # Create Grafana datasource configuration
    mkdir -p monitoring/grafana/datasources
    cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
    
    log_success "Monitoring configuration created"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    # Test Python imports
    python3 -c "
import sys
try:
    from modules.pipeline_orchestration.nextflow_manager import NextflowManager
    from modules.pipeline_orchestration.snakemake_manager import SnakemakeManager
    from modules.graph_analytics.neo4j_manager import Neo4jManager
    from modules.graph_analytics.networkx_analyzer import NetworkXAnalyzer
    from modules.real_time_processing.kafka_manager import KafkaManager
    from modules.oauth2_auth.keycloak_client import KeycloakClient
    from modules.oauth2_auth.auth0_client import Auth0Client
    print('All modules imported successfully')
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "All modules imported successfully"
    else
        log_error "Module import test failed"
        exit 1
    fi
}

# Main setup function
main() {
    log_info "Starting Advanced Technologies Setup for Cancer Genomics Analysis Suite"
    
    check_system_requirements
    install_python_dependencies
    setup_environment
    setup_directories
    setup_neo4j
    setup_kafka
    setup_keycloak
    setup_nextflow
    setup_snakemake
    create_sample_data
    setup_monitoring
    run_tests
    
    log_success "Advanced Technologies Setup Completed!"
    
    echo ""
    log_info "Services available:"
    echo "  - Neo4j Web UI: http://localhost:7474 (neo4j/password)"
    echo "  - Kafka UI: http://localhost:8080"
    echo "  - Keycloak Admin: http://localhost:8081 (admin/admin)"
    echo "  - Grafana: http://localhost:3000 (admin/admin)"
    echo "  - Prometheus: http://localhost:9090"
    
    echo ""
    log_info "Next steps:"
    echo "  1. Edit .env file with your specific configuration"
    echo "  2. Run the application: python3 run_flask_app.py"
    echo "  3. Run the example: python3 examples/advanced_technologies_example.py"
    echo "  4. Check the documentation: ADVANCED_TECHNOLOGIES_INTEGRATION.md"
}

# Run main function
main "$@"
