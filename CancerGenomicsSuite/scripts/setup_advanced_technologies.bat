@echo off
REM Advanced Technologies Setup Script for Windows
REM This script sets up all the advanced technologies for the Cancer Genomics Analysis Suite

setlocal enabledelayedexpansion

echo [INFO] Starting Advanced Technologies Setup for Cancer Genomics Analysis Suite

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is required but not installed
    exit /b 1
)
echo [SUCCESS] Python found

REM Check if pip is installed
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is required but not installed
    exit /b 1
)
echo [SUCCESS] pip found

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Docker not found. Some services will not be available
) else (
    echo [SUCCESS] Docker found
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Docker Compose not found. Some services will not be available
) else (
    echo [SUCCESS] Docker Compose found
)

REM Install Python dependencies
echo [INFO] Installing Python dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
    echo [SUCCESS] Python dependencies installed
) else (
    echo [ERROR] requirements.txt not found
    exit /b 1
)

REM Setup environment configuration
echo [INFO] Setting up environment configuration...
if not exist .env (
    if exist environment.advanced.template (
        copy environment.advanced.template .env
        echo [SUCCESS] Environment configuration created from template
        echo [WARNING] Please edit .env file with your specific configuration
    ) else (
        echo [ERROR] environment.advanced.template not found
        exit /b 1
    )
) else (
    echo [INFO] Environment configuration already exists
)

REM Setup directories
echo [INFO] Creating necessary directories...
if not exist data mkdir data
if not exist data\samples mkdir data\samples
if not exist data\results mkdir data\results
if not exist data\exports mkdir data\exports
if not exist results mkdir results
if not exist results\pipelines mkdir results\pipelines
if not exist results\graphs mkdir results\graphs
if not exist results\reports mkdir results\reports
if not exist logs mkdir logs
if not exist logs\app mkdir logs\app
if not exist logs\pipelines mkdir logs\pipelines
if not exist logs\graphs mkdir logs\graphs
if not exist logs\kafka mkdir logs\kafka
if not exist logs\oauth2 mkdir logs\oauth2
if not exist nextflow_work mkdir nextflow_work
if not exist snakemake_work mkdir snakemake_work
if not exist neo4j_import mkdir neo4j_import
if not exist kafka_data mkdir kafka_data
if not exist ssl mkdir ssl
if not exist monitoring mkdir monitoring
if not exist monitoring\prometheus mkdir monitoring\prometheus
if not exist monitoring\grafana mkdir monitoring\grafana
if not exist monitoring\logstash mkdir monitoring\logstash
echo [SUCCESS] Directories created

REM Setup Neo4j with Docker
echo [INFO] Setting up Neo4j...
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password -e NEO4J_PLUGINS=["apoc"] -e NEO4J_dbms_security_procedures_unrestricted=apoc.* -v neo4j_data:/data -v neo4j_logs:/logs -v neo4j_import:/var/lib/neo4j/import neo4j:5.15-community
    echo [SUCCESS] Neo4j started with Docker
    echo [INFO] Neo4j Web UI: http://localhost:7474
    echo [INFO] Username: neo4j, Password: password
) else (
    echo [WARNING] Docker not available. Please install Neo4j manually
)

REM Setup Kafka with Docker Compose
echo [INFO] Setting up Apache Kafka...
docker-compose --version >nul 2>&1
if %errorlevel% equ 0 (
    echo version: '3.8' > docker-compose.kafka.yml
    echo services: >> docker-compose.kafka.yml
    echo   zookeeper: >> docker-compose.kafka.yml
    echo     image: confluentinc/cp-zookeeper:7.4.0 >> docker-compose.kafka.yml
    echo     environment: >> docker-compose.kafka.yml
    echo       ZOOKEEPER_CLIENT_PORT: 2181 >> docker-compose.kafka.yml
    echo       ZOOKEEPER_TICK_TIME: 2000 >> docker-compose.kafka.yml
    echo. >> docker-compose.kafka.yml
    echo   kafka: >> docker-compose.kafka.yml
    echo     image: confluentinc/cp-kafka:7.4.0 >> docker-compose.kafka.yml
    echo     depends_on: >> docker-compose.kafka.yml
    echo       - zookeeper >> docker-compose.kafka.yml
    echo     ports: >> docker-compose.kafka.yml
    echo       - "9092:9092" >> docker-compose.kafka.yml
    echo     environment: >> docker-compose.kafka.yml
    echo       KAFKA_BROKER_ID: 1 >> docker-compose.kafka.yml
    echo       KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181 >> docker-compose.kafka.yml
    echo       KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092 >> docker-compose.kafka.yml
    echo       KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT >> docker-compose.kafka.yml
    echo       KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT >> docker-compose.kafka.yml
    echo       KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1 >> docker-compose.kafka.yml
    echo       KAFKA_AUTO_CREATE_TOPICS_ENABLE: true >> docker-compose.kafka.yml
    echo. >> docker-compose.kafka.yml
    echo   kafka-ui: >> docker-compose.kafka.yml
    echo     image: provectuslabs/kafka-ui:latest >> docker-compose.kafka.yml
    echo     depends_on: >> docker-compose.kafka.yml
    echo       - kafka >> docker-compose.kafka.yml
    echo     ports: >> docker-compose.kafka.yml
    echo       - "8080:8080" >> docker-compose.kafka.yml
    echo     environment: >> docker-compose.kafka.yml
    echo       KAFKA_CLUSTERS_0_NAME: local >> docker-compose.kafka.yml
    echo       KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092 >> docker-compose.kafka.yml
    
    docker-compose -f docker-compose.kafka.yml up -d
    echo [SUCCESS] Kafka started with Docker Compose
    echo [INFO] Kafka UI: http://localhost:8080
) else (
    echo [WARNING] Docker Compose not available. Please install Kafka manually
)

REM Setup Keycloak with Docker
echo [INFO] Setting up Keycloak...
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    docker run -d --name keycloak -p 8081:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:23.0 start-dev
    echo [SUCCESS] Keycloak started with Docker
    echo [INFO] Keycloak Admin Console: http://localhost:8081
    echo [INFO] Username: admin, Password: admin
) else (
    echo [WARNING] Docker not available. Please install Keycloak manually
)

REM Setup Nextflow
echo [INFO] Setting up Nextflow...
where nextflow >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing Nextflow...
    curl -s https://get.nextflow.io | bash
    if exist nextflow.exe (
        move nextflow.exe C:\Windows\System32\
    ) else (
        echo [WARNING] Nextflow installation failed
    )
) else (
    echo [SUCCESS] Nextflow already installed
)

REM Setup Snakemake
echo [INFO] Setting up Snakemake...
pip show snakemake >nul 2>&1
if %errorlevel% neq 0 (
    pip install snakemake
    echo [SUCCESS] Snakemake installed
) else (
    echo [SUCCESS] Snakemake already installed
)

REM Create sample data
echo [INFO] Creating sample data...
echo gene,BRCA1,BRCA2,TP53,EGFR,MYC > data\samples\gene_expression.csv
echo BRCA1,1.0,0.8,0.6,0.3,0.2 >> data\samples\gene_expression.csv
echo BRCA2,0.8,1.0,0.7,0.4,0.3 >> data\samples\gene_expression.csv
echo TP53,0.6,0.7,1.0,0.5,0.4 >> data\samples\gene_expression.csv
echo EGFR,0.3,0.4,0.5,1.0,0.6 >> data\samples\gene_expression.csv
echo MYC,0.2,0.3,0.4,0.6,1.0 >> data\samples\gene_expression.csv

echo source,target,interaction_type,confidence > data\samples\gene_interactions.csv
echo BRCA1,BRCA2,protein_protein,0.9 >> data\samples\gene_interactions.csv
echo BRCA1,TP53,protein_protein,0.8 >> data\samples\gene_interactions.csv
echo BRCA2,TP53,protein_protein,0.7 >> data\samples\gene_interactions.csv
echo TP53,EGFR,regulates,0.6 >> data\samples\gene_interactions.csv
echo EGFR,MYC,regulates,0.5 >> data\samples\gene_interactions.csv

echo sample_id,gene,variant,type,pathogenicity > data\samples\mutations.csv
echo S001,BRCA1,c.5266dupC,frameshift,pathogenic >> data\samples\mutations.csv
echo S001,BRCA2,c.5946delT,frameshift,pathogenic >> data\samples\mutations.csv
echo S002,TP53,c.524G>A,missense,pathogenic >> data\samples\mutations.csv
echo S002,EGFR,c.2573T>G,missense,benign >> data\samples\mutations.csv
echo S003,MYC,c.1234C>T,synonymous,benign >> data\samples\mutations.csv

echo [SUCCESS] Sample data created

REM Setup monitoring
echo [INFO] Setting up monitoring...
echo global: > monitoring\prometheus.yml
echo   scrape_interval: 15s >> monitoring\prometheus.yml
echo. >> monitoring\prometheus.yml
echo scrape_configs: >> monitoring\prometheus.yml
echo   - job_name: 'cancer-genomics-app' >> monitoring\prometheus.yml
echo     static_configs: >> monitoring\prometheus.yml
echo       - targets: ['localhost:5000'] >> monitoring\prometheus.yml
echo. >> monitoring\prometheus.yml
echo   - job_name: 'neo4j' >> monitoring\prometheus.yml
echo     static_configs: >> monitoring\prometheus.yml
echo       - targets: ['localhost:7474'] >> monitoring\prometheus.yml
echo. >> monitoring\prometheus.yml
echo   - job_name: 'kafka' >> monitoring\prometheus.yml
echo     static_configs: >> monitoring\prometheus.yml
echo       - targets: ['localhost:9092'] >> monitoring\prometheus.yml
echo. >> monitoring\prometheus.yml
echo   - job_name: 'keycloak' >> monitoring\prometheus.yml
echo     static_configs: >> monitoring\prometheus.yml
echo       - targets: ['localhost:8081'] >> monitoring\prometheus.yml

if not exist monitoring\grafana mkdir monitoring\grafana
if not exist monitoring\grafana\datasources mkdir monitoring\grafana\datasources
echo apiVersion: 1 > monitoring\grafana\datasources\prometheus.yml
echo. >> monitoring\grafana\datasources\prometheus.yml
echo datasources: >> monitoring\grafana\datasources\prometheus.yml
echo   - name: Prometheus >> monitoring\grafana\datasources\prometheus.yml
echo     type: prometheus >> monitoring\grafana\datasources\prometheus.yml
echo     access: proxy >> monitoring\grafana\datasources\prometheus.yml
echo     url: http://prometheus:9090 >> monitoring\grafana\datasources\prometheus.yml
echo     isDefault: true >> monitoring\grafana\datasources\prometheus.yml

echo [SUCCESS] Monitoring configuration created

REM Run tests
echo [INFO] Running tests...
python -c "from modules.pipeline_orchestration.nextflow_manager import NextflowManager; from modules.pipeline_orchestration.snakemake_manager import SnakemakeManager; from modules.graph_analytics.neo4j_manager import Neo4jManager; from modules.graph_analytics.networkx_analyzer import NetworkXAnalyzer; from modules.real_time_processing.kafka_manager import KafkaManager; from modules.oauth2_auth.keycloak_client import KeycloakClient; from modules.oauth2_auth.auth0_client import Auth0Client; print('All modules imported successfully')"
if %errorlevel% equ 0 (
    echo [SUCCESS] All modules imported successfully
) else (
    echo [ERROR] Module import test failed
    exit /b 1
)

echo.
echo [SUCCESS] Advanced Technologies Setup Completed!
echo.
echo [INFO] Services available:
echo   - Neo4j Web UI: http://localhost:7474 (neo4j/password)
echo   - Kafka UI: http://localhost:8080
echo   - Keycloak Admin: http://localhost:8081 (admin/admin)
echo.
echo [INFO] Next steps:
echo   1. Edit .env file with your specific configuration
echo   2. Run the application: python run_flask_app.py
echo   3. Run the example: python examples/advanced_technologies_example.py
echo   4. Check the documentation: ADVANCED_TECHNOLOGIES_INTEGRATION.md

pause
