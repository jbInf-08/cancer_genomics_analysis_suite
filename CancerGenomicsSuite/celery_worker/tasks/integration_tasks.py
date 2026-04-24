"""
Integration Tasks

This module contains Celery tasks for external integrations,
API calls, and system monitoring in the cancer genomics analysis suite.
"""

import logging
import requests
import time
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from celery import current_task
from celery_worker import celery
import json
import os

logger = logging.getLogger(__name__)

@celery.task(bind=True, name="celery_worker.tasks.integration_tasks.system_health_check")
def system_health_check(self) -> Dict[str, Any]:
    """
    Perform comprehensive system health check.
    
    Returns:
        Dict containing system health status and metrics
    """
    try:
        logger.info("Starting system health check")
        
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Checking system resources"})
        
        # Check system resources
        system_metrics = _check_system_resources()
        
        self.update_state(state="PROGRESS", meta={"current": 25, "total": 100, "status": "Checking services"})
        
        # Check external services
        service_status = _check_external_services()
        
        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100, "status": "Checking database"})
        
        # Check database connectivity
        database_status = _check_database_connectivity()
        
        self.update_state(state="PROGRESS", meta={"current": 75, "total": 100, "status": "Checking queues"})
        
        # Check Celery queues
        queue_status = _check_celery_queues()
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        # Determine overall health status
        overall_status = _determine_overall_health(system_metrics, service_status, database_status, queue_status)
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "system_metrics": system_metrics,
            "service_status": service_status,
            "database_status": database_status,
            "queue_status": queue_status,
            "recommendations": _generate_health_recommendations(system_metrics, service_status)
        }
        
        logger.info(f"System health check completed: {overall_status}")
        return {
            "health_report": health_report,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"System health check failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

@celery.task(bind=True, name="celery_worker.tasks.integration_tasks.sync_external_databases")
def sync_external_databases(self, databases: List[str] = None) -> Dict[str, Any]:
    """
    Synchronize with external genomic databases.
    
    Args:
        databases: List of databases to sync (ensembl, uniprot, clinvar, cosmic)
    
    Returns:
        Dict containing synchronization results
    """
    try:
        if databases is None:
            databases = ["ensembl", "uniprot", "clinvar", "cosmic"]
        
        logger.info(f"Starting external database sync: {databases}")
        
        sync_results = {}
        total_databases = len(databases)
        
        for i, database in enumerate(databases):
            self.update_state(state="PROGRESS", meta={
                "current": (i / total_databases) * 100, 
                "total": 100, 
                "status": f"Syncing {database}"
            })
            
            # Sync individual database
            db_result = _sync_database(database)
            sync_results[database] = db_result
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        # Calculate overall sync statistics
        total_records = sum(result.get("records_synced", 0) for result in sync_results.values())
        successful_syncs = sum(1 for result in sync_results.values() if result.get("success", False))
        
        stats = {
            "databases_synced": len(databases),
            "successful_syncs": successful_syncs,
            "failed_syncs": len(databases) - successful_syncs,
            "total_records": total_records,
            "sync_time": datetime.now().isoformat()
        }
        
        logger.info(f"External database sync completed: {stats}")
        return {
            "sync_results": sync_results,
            "statistics": stats,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"External database sync failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

@celery.task(bind=True, name="celery_worker.tasks.integration_tasks.fetch_publication_data")
def fetch_publication_data(self, search_terms: List[str], max_results: int = 100) -> Dict[str, Any]:
    """
    Fetch publication data from external APIs.
    
    Args:
        search_terms: List of search terms for publications
        max_results: Maximum number of results to fetch
    
    Returns:
        Dict containing fetched publication data
    """
    try:
        logger.info(f"Starting publication data fetch: {search_terms}")
        
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Preparing search"})
        
        # Prepare search queries
        search_queries = _prepare_search_queries(search_terms)
        
        self.update_state(state="PROGRESS", meta={"current": 25, "total": 100, "status": "Fetching from PubMed"})
        
        # Fetch from PubMed
        pubmed_results = _fetch_from_pubmed(search_queries, max_results // 2)
        
        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100, "status": "Fetching from arXiv"})
        
        # Fetch from arXiv
        arxiv_results = _fetch_from_arxiv(search_queries, max_results // 2)
        
        self.update_state(state="PROGRESS", meta={"current": 75, "total": 100, "status": "Processing results"})
        
        # Process and deduplicate results
        processed_results = _process_publication_results(pubmed_results, arxiv_results)
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        stats = {
            "search_terms": search_terms,
            "total_results": len(processed_results),
            "pubmed_results": len(pubmed_results),
            "arxiv_results": len(arxiv_results),
            "fetch_time": datetime.now().isoformat()
        }
        
        logger.info(f"Publication data fetch completed: {stats}")
        return {
            "publications": processed_results,
            "statistics": stats,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"Publication data fetch failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

@celery.task(bind=True, name="celery_worker.tasks.integration_tasks.update_drug_database")
def update_drug_database(self, drug_sources: List[str] = None) -> Dict[str, Any]:
    """
    Update drug database from external sources.
    
    Args:
        drug_sources: List of drug data sources (dgidb, drugbank, oncokb)
    
    Returns:
        Dict containing update results
    """
    try:
        if drug_sources is None:
            drug_sources = ["dgidb", "drugbank", "oncokb"]
        
        logger.info(f"Starting drug database update: {drug_sources}")
        
        update_results = {}
        total_sources = len(drug_sources)
        
        for i, source in enumerate(drug_sources):
            self.update_state(state="PROGRESS", meta={
                "current": (i / total_sources) * 100, 
                "total": 100, 
                "status": f"Updating {source}"
            })
            
            # Update individual source
            source_result = _update_drug_source(source)
            update_results[source] = source_result
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        # Calculate update statistics
        total_drugs = sum(result.get("drugs_updated", 0) for result in update_results.values())
        successful_updates = sum(1 for result in update_results.values() if result.get("success", False))
        
        stats = {
            "sources_updated": len(drug_sources),
            "successful_updates": successful_updates,
            "failed_updates": len(drug_sources) - successful_updates,
            "total_drugs": total_drugs,
            "update_time": datetime.now().isoformat()
        }
        
        logger.info(f"Drug database update completed: {stats}")
        return {
            "update_results": update_results,
            "statistics": stats,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"Drug database update failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

@celery.task(bind=True, name="celery_worker.tasks.integration_tasks.monitor_analysis_pipeline")
def monitor_analysis_pipeline(self, pipeline_id: str = None) -> Dict[str, Any]:
    """
    Monitor analysis pipeline status and performance.
    
    Args:
        pipeline_id: Specific pipeline ID to monitor (optional)
    
    Returns:
        Dict containing pipeline monitoring results
    """
    try:
        logger.info(f"Starting pipeline monitoring: {pipeline_id}")
        
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Checking pipeline status"})
        
        # Check pipeline status
        pipeline_status = _check_pipeline_status(pipeline_id)
        
        self.update_state(state="PROGRESS", meta={"current": 25, "total": 100, "status": "Analyzing performance"})
        
        # Analyze pipeline performance
        performance_metrics = _analyze_pipeline_performance(pipeline_id)
        
        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100, "status": "Checking resource usage"})
        
        # Check resource usage
        resource_usage = _check_pipeline_resources(pipeline_id)
        
        self.update_state(state="PROGRESS", meta={"current": 75, "total": 100, "status": "Generating alerts"})
        
        # Generate alerts if needed
        alerts = _generate_pipeline_alerts(pipeline_status, performance_metrics, resource_usage)
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        monitoring_report = {
            "pipeline_id": pipeline_id,
            "timestamp": datetime.now().isoformat(),
            "pipeline_status": pipeline_status,
            "performance_metrics": performance_metrics,
            "resource_usage": resource_usage,
            "alerts": alerts
        }
        
        stats = {
            "pipeline_id": pipeline_id,
            "monitoring_time": datetime.now().isoformat(),
            "alerts_generated": len(alerts),
            "status": pipeline_status.get("status", "unknown")
        }
        
        logger.info(f"Pipeline monitoring completed: {stats}")
        return {
            "monitoring_report": monitoring_report,
            "statistics": stats,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"Pipeline monitoring failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

# Helper functions
def _check_system_resources() -> Dict[str, Any]:
    """Check system resource usage."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
        "timestamp": datetime.now().isoformat()
    }

def _check_external_services() -> Dict[str, Any]:
    """Check status of external services."""
    services = {
        "ensembl_api": "https://rest.ensembl.org/info/ping",
        "uniprot_api": "https://www.uniprot.org/uniprot/P12345.json",
        "pubmed_api": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    }
    
    service_status = {}
    
    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            service_status[service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code
            }
        except Exception as e:
            service_status[service_name] = {
                "status": "unreachable",
                "error": str(e),
                "response_time": None
            }
    
    return service_status

def _check_database_connectivity() -> Dict[str, Any]:
    """Check database connectivity."""
    # Mock database connectivity check
    return {
        "status": "connected",
        "response_time": 0.05,
        "active_connections": 5,
        "database_size": "1.2 GB",
        "last_backup": (datetime.now() - timedelta(hours=6)).isoformat()
    }

def _check_celery_queues() -> Dict[str, Any]:
    """Check Celery queue status."""
    # Mock queue status check
    return {
        "active_tasks": 3,
        "scheduled_tasks": 5,
        "reserved_tasks": 2,
        "queue_lengths": {
            "default": 1,
            "expression": 2,
            "mutation": 1,
            "ml": 0,
            "reporting": 1
        }
    }

def _determine_overall_health(system_metrics: Dict, service_status: Dict, 
                            database_status: Dict, queue_status: Dict) -> str:
    """Determine overall system health status."""
    # Check system resources
    if system_metrics["cpu_percent"] > 90 or system_metrics["memory_percent"] > 90:
        return "critical"
    
    # Check external services
    unhealthy_services = sum(1 for status in service_status.values() 
                           if status["status"] != "healthy")
    if unhealthy_services > len(service_status) / 2:
        return "warning"
    
    # Check database
    if database_status["status"] != "connected":
        return "critical"
    
    # Check queues
    if queue_status["active_tasks"] > 100:
        return "warning"
    
    return "healthy"

def _generate_health_recommendations(system_metrics: Dict, service_status: Dict) -> List[str]:
    """Generate health recommendations."""
    recommendations = []
    
    if system_metrics["cpu_percent"] > 80:
        recommendations.append("High CPU usage detected. Consider scaling up resources.")
    
    if system_metrics["memory_percent"] > 80:
        recommendations.append("High memory usage detected. Consider increasing memory allocation.")
    
    unhealthy_services = [name for name, status in service_status.items() 
                         if status["status"] != "healthy"]
    if unhealthy_services:
        recommendations.append(f"Unhealthy services detected: {', '.join(unhealthy_services)}")
    
    return recommendations

def _sync_database(database: str) -> Dict[str, Any]:
    """Sync individual database."""
    # Mock database sync
    sync_operations = {
        "ensembl": {"records_synced": 1500, "success": True},
        "uniprot": {"records_synced": 800, "success": True},
        "clinvar": {"records_synced": 200, "success": True},
        "cosmic": {"records_synced": 1200, "success": True}
    }
    
    result = sync_operations.get(database, {"records_synced": 0, "success": False})
    result["sync_time"] = datetime.now().isoformat()
    result["database"] = database
    
    return result

def _prepare_search_queries(search_terms: List[str]) -> List[str]:
    """Prepare search queries for publication APIs."""
    return [f"cancer genomics {term}" for term in search_terms]

def _fetch_from_pubmed(search_queries: List[str], max_results: int) -> List[Dict[str, Any]]:
    """Fetch publications from PubMed."""
    # Mock PubMed fetch
    publications = []
    for i in range(min(max_results, 10)):
        publications.append({
            "pmid": f"1234567{i}",
            "title": f"Cancer genomics study {i}",
            "authors": f"Author {i}, et al.",
            "journal": "Nature Genetics",
            "year": 2023,
            "abstract": f"Abstract for study {i}",
            "source": "pubmed"
        })
    
    return publications

def _fetch_from_arxiv(search_queries: List[str], max_results: int) -> List[Dict[str, Any]]:
    """Fetch publications from arXiv."""
    # Mock arXiv fetch
    publications = []
    for i in range(min(max_results, 10)):
        publications.append({
            "arxiv_id": f"2301.0000{i}",
            "title": f"Machine learning in cancer genomics {i}",
            "authors": f"Researcher {i}, et al.",
            "year": 2023,
            "abstract": f"Preprint abstract {i}",
            "source": "arxiv"
        })
    
    return publications

def _process_publication_results(pubmed_results: List[Dict], arxiv_results: List[Dict]) -> List[Dict[str, Any]]:
    """Process and deduplicate publication results."""
    all_publications = pubmed_results + arxiv_results
    
    # Simple deduplication based on title similarity
    processed = []
    seen_titles = set()
    
    for pub in all_publications:
        title_key = pub["title"].lower().replace(" ", "")
        if title_key not in seen_titles:
            processed.append(pub)
            seen_titles.add(title_key)
    
    return processed

def _update_drug_source(source: str) -> Dict[str, Any]:
    """Update drug data from specific source."""
    # Mock drug source update
    update_operations = {
        "dgidb": {"drugs_updated": 500, "success": True},
        "drugbank": {"drugs_updated": 1200, "success": True},
        "oncokb": {"drugs_updated": 300, "success": True}
    }
    
    result = update_operations.get(source, {"drugs_updated": 0, "success": False})
    result["update_time"] = datetime.now().isoformat()
    result["source"] = source
    
    return result

def _check_pipeline_status(pipeline_id: str = None) -> Dict[str, Any]:
    """Check pipeline status."""
    # Mock pipeline status check
    return {
        "pipeline_id": pipeline_id or "default",
        "status": "running",
        "progress": 75,
        "current_step": "mutation_analysis",
        "start_time": (datetime.now() - timedelta(hours=2)).isoformat(),
        "estimated_completion": (datetime.now() + timedelta(minutes=30)).isoformat()
    }

def _analyze_pipeline_performance(pipeline_id: str = None) -> Dict[str, Any]:
    """Analyze pipeline performance metrics."""
    # Mock performance analysis
    return {
        "throughput": 50,  # analyses per hour
        "average_processing_time": 120,  # minutes
        "success_rate": 0.95,
        "error_rate": 0.05,
        "resource_efficiency": 0.85
    }

def _check_pipeline_resources(pipeline_id: str = None) -> Dict[str, Any]:
    """Check pipeline resource usage."""
    # Mock resource usage check
    return {
        "cpu_usage": 65,
        "memory_usage": 70,
        "disk_usage": 45,
        "network_io": 100,  # MB/s
        "active_workers": 4
    }

def _generate_pipeline_alerts(pipeline_status: Dict, performance_metrics: Dict, 
                            resource_usage: Dict) -> List[Dict[str, Any]]:
    """Generate pipeline alerts based on status and metrics."""
    alerts = []
    
    # Check performance metrics
    if performance_metrics["success_rate"] < 0.9:
        alerts.append({
            "type": "warning",
            "message": "Low success rate detected",
            "metric": "success_rate",
            "value": performance_metrics["success_rate"]
        })
    
    # Check resource usage
    if resource_usage["cpu_usage"] > 80:
        alerts.append({
            "type": "warning",
            "message": "High CPU usage detected",
            "metric": "cpu_usage",
            "value": resource_usage["cpu_usage"]
        })
    
    if resource_usage["memory_usage"] > 85:
        alerts.append({
            "type": "critical",
            "message": "High memory usage detected",
            "metric": "memory_usage",
            "value": resource_usage["memory_usage"]
        })
    
    return alerts
