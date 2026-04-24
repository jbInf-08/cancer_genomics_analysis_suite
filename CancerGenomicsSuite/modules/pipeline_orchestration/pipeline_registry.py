#!/usr/bin/env python3
"""
Pipeline Registry

This module provides a registry system for managing and discovering
cancer genomics analysis pipelines.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)


class PipelineRegistry:
    """
    Registry for managing cancer genomics analysis pipelines.
    
    Provides functionality to:
    - Register and discover pipelines
    - Manage pipeline metadata
    - Validate pipeline configurations
    - Search and filter pipelines
    """
    
    def __init__(self, registry_file: Optional[str] = None):
        """
        Initialize pipeline registry.
        
        Args:
            registry_file: Path to registry file for persistence
        """
        self.registry_file = Path(registry_file) if registry_file else Path("pipeline_registry.json")
        self.pipelines: Dict[str, Dict] = {}
        self.categories = {
            "variant_calling": "Variant calling and analysis",
            "expression_analysis": "Gene expression analysis",
            "multi_omics": "Multi-omics integration",
            "quality_control": "Data quality control",
            "alignment": "Sequence alignment",
            "annotation": "Variant and gene annotation",
            "pathway_analysis": "Pathway and functional analysis",
            "machine_learning": "Machine learning models",
            "visualization": "Data visualization",
            "reporting": "Report generation"
        }
        
        # Load existing registry
        self.load_registry()
    
    def register_pipeline(
        self,
        name: str,
        pipeline_type: str,
        description: str,
        script_path: str,
        config_template: Optional[Dict] = None,
        requirements: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        version: str = "1.0.0",
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Register a new pipeline in the registry.
        
        Args:
            name: Unique name for the pipeline
            description: Description of the pipeline
            pipeline_type: Type/category of the pipeline
            script_path: Path to the pipeline script
            config_template: Configuration template
            requirements: List of required tools/dependencies
            tags: List of tags for the pipeline
            author: Pipeline author
            version: Pipeline version
            metadata: Additional metadata
            
        Returns:
            True if registration was successful
        """
        if name in self.pipelines:
            logger.warning(f"Pipeline {name} already exists, updating...")
        
        pipeline_info = {
            "name": name,
            "pipeline_type": pipeline_type,
            "description": description,
            "script_path": script_path,
            "config_template": config_template or {},
            "requirements": requirements or [],
            "tags": tags or [],
            "author": author,
            "version": version,
            "metadata": metadata or {},
            "registered_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        # Validate pipeline
        if not self._validate_pipeline(pipeline_info):
            return False
        
        self.pipelines[name] = pipeline_info
        self.save_registry()
        
        logger.info(f"Pipeline {name} registered successfully")
        return True
    
    def unregister_pipeline(self, name: str) -> bool:
        """
        Unregister a pipeline from the registry.
        
        Args:
            name: Name of the pipeline to unregister
            
        Returns:
            True if unregistration was successful
        """
        if name not in self.pipelines:
            logger.warning(f"Pipeline {name} not found in registry")
            return False
        
        del self.pipelines[name]
        self.save_registry()
        
        logger.info(f"Pipeline {name} unregistered successfully")
        return True
    
    def get_pipeline(self, name: str) -> Optional[Dict]:
        """
        Get pipeline information by name.
        
        Args:
            name: Name of the pipeline
            
        Returns:
            Pipeline information dictionary or None if not found
        """
        return self.pipelines.get(name)
    
    def list_pipelines(
        self,
        pipeline_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None
    ) -> List[Dict]:
        """
        List pipelines with optional filtering.
        
        Args:
            pipeline_type: Filter by pipeline type
            tags: Filter by tags (any match)
            author: Filter by author
            
        Returns:
            List of pipeline information dictionaries
        """
        pipelines = list(self.pipelines.values())
        
        if pipeline_type:
            pipelines = [p for p in pipelines if p["pipeline_type"] == pipeline_type]
        
        if tags:
            pipelines = [p for p in pipelines if any(tag in p["tags"] for tag in tags)]
        
        if author:
            pipelines = [p for p in pipelines if p["author"] == author]
        
        return pipelines
    
    def search_pipelines(self, query: str) -> List[Dict]:
        """
        Search pipelines by name, description, or tags.
        
        Args:
            query: Search query
            
        Returns:
            List of matching pipeline information dictionaries
        """
        query_lower = query.lower()
        matching_pipelines = []
        
        for pipeline in self.pipelines.values():
            # Search in name, description, and tags
            if (query_lower in pipeline["name"].lower() or
                query_lower in pipeline["description"].lower() or
                any(query_lower in tag.lower() for tag in pipeline["tags"])):
                matching_pipelines.append(pipeline)
        
        return matching_pipelines
    
    def get_pipeline_types(self) -> Dict[str, str]:
        """
        Get available pipeline types and their descriptions.
        
        Returns:
            Dictionary mapping pipeline types to descriptions
        """
        return self.categories.copy()
    
    def validate_pipeline_config(self, pipeline_name: str, config: Dict) -> Dict[str, Any]:
        """
        Validate a pipeline configuration against its template.
        
        Args:
            pipeline_name: Name of the pipeline
            config: Configuration to validate
            
        Returns:
            Validation result with errors and warnings
        """
        pipeline = self.get_pipeline(pipeline_name)
        if not pipeline:
            return {"valid": False, "errors": [f"Pipeline {pipeline_name} not found"]}
        
        template = pipeline.get("config_template", {})
        result = {"valid": True, "errors": [], "warnings": []}
        
        # Check required fields
        required_fields = template.get("required", [])
        for field in required_fields:
            if field not in config:
                result["errors"].append(f"Required field '{field}' is missing")
                result["valid"] = False
        
        # Check field types
        field_types = template.get("field_types", {})
        for field, expected_type in field_types.items():
            if field in config:
                actual_type = type(config[field]).__name__
                if actual_type != expected_type:
                    result["warnings"].append(
                        f"Field '{field}' has type {actual_type}, expected {expected_type}"
                    )
        
        # Check field values
        field_values = template.get("field_values", {})
        for field, allowed_values in field_values.items():
            if field in config and config[field] not in allowed_values:
                result["errors"].append(
                    f"Field '{field}' has invalid value '{config[field]}', "
                    f"allowed values: {allowed_values}"
                )
                result["valid"] = False
        
        return result
    
    def create_pipeline_config(self, pipeline_name: str, **kwargs) -> Dict:
        """
        Create a configuration for a pipeline using its template.
        
        Args:
            pipeline_name: Name of the pipeline
            **kwargs: Configuration values
            
        Returns:
            Pipeline configuration dictionary
        """
        pipeline = self.get_pipeline(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_name} not found")
        
        template = pipeline.get("config_template", {})
        config = template.get("defaults", {}).copy()
        
        # Override with provided values
        config.update(kwargs)
        
        return config
    
    def get_pipeline_requirements(self, pipeline_name: str) -> List[str]:
        """
        Get requirements for a pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            List of required tools/dependencies
        """
        pipeline = self.get_pipeline(pipeline_name)
        if not pipeline:
            return []
        
        return pipeline.get("requirements", [])
    
    def update_pipeline(self, name: str, **updates) -> bool:
        """
        Update pipeline information.
        
        Args:
            name: Name of the pipeline
            **updates: Fields to update
            
        Returns:
            True if update was successful
        """
        if name not in self.pipelines:
            logger.warning(f"Pipeline {name} not found in registry")
            return False
        
        # Update fields
        for key, value in updates.items():
            if key in self.pipelines[name]:
                self.pipelines[name][key] = value
        
        # Update timestamp
        self.pipelines[name]["last_updated"] = datetime.now().isoformat()
        
        self.save_registry()
        logger.info(f"Pipeline {name} updated successfully")
        return True
    
    def export_pipeline(self, pipeline_name: str, export_path: str) -> bool:
        """
        Export pipeline information to a file.
        
        Args:
            pipeline_name: Name of the pipeline
            export_path: Path to export file
            
        Returns:
            True if export was successful
        """
        pipeline = self.get_pipeline(pipeline_name)
        if not pipeline:
            return False
        
        export_data = {
            "pipeline": pipeline,
            "exported_at": datetime.now().isoformat(),
            "registry_version": "1.0.0"
        }
        
        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        if export_path.suffix.lower() == '.yaml' or export_path.suffix.lower() == '.yml':
            with open(export_path, 'w') as f:
                yaml.dump(export_data, f, default_flow_style=False)
        else:
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        logger.info(f"Pipeline {pipeline_name} exported to {export_path}")
        return True
    
    def import_pipeline(self, import_path: str) -> bool:
        """
        Import pipeline information from a file.
        
        Args:
            import_path: Path to import file
            
        Returns:
            True if import was successful
        """
        import_path = Path(import_path)
        
        try:
            if import_path.suffix.lower() == '.yaml' or import_path.suffix.lower() == '.yml':
                with open(import_path, 'r') as f:
                    import_data = yaml.safe_load(f)
            else:
                with open(import_path, 'r') as f:
                    import_data = json.load(f)
            
            pipeline_info = import_data.get("pipeline")
            if not pipeline_info:
                logger.error("No pipeline information found in import file")
                return False
            
            # Validate pipeline
            if not self._validate_pipeline(pipeline_info):
                return False
            
            # Register pipeline
            return self.register_pipeline(**pipeline_info)
            
        except Exception as e:
            logger.error(f"Failed to import pipeline: {e}")
            return False
    
    def _validate_pipeline(self, pipeline_info: Dict) -> bool:
        """
        Validate pipeline information.
        
        Args:
            pipeline_info: Pipeline information dictionary
            
        Returns:
            True if validation passed
        """
        required_fields = ["name", "pipeline_type", "description", "script_path"]
        
        for field in required_fields:
            if field not in pipeline_info:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Check if script exists
        script_path = Path(pipeline_info["script_path"])
        if not script_path.exists():
            logger.error(f"Pipeline script not found: {script_path}")
            return False
        
        # Check pipeline type
        if pipeline_info["pipeline_type"] not in self.categories:
            logger.warning(f"Unknown pipeline type: {pipeline_info['pipeline_type']}")
        
        return True
    
    def save_registry(self):
        """Save registry to file."""
        registry_data = {
            "pipelines": self.pipelines,
            "categories": self.categories,
            "last_updated": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.registry_file, 'w') as f:
            json.dump(registry_data, f, indent=2)
        
        logger.debug(f"Registry saved to {self.registry_file}")
    
    def load_registry(self):
        """Load registry from file."""
        if not self.registry_file.exists():
            logger.info("No existing registry found, starting with empty registry")
            return
        
        try:
            with open(self.registry_file, 'r') as f:
                registry_data = json.load(f)
            
            self.pipelines = registry_data.get("pipelines", {})
            self.categories.update(registry_data.get("categories", {}))
            
            logger.info(f"Loaded {len(self.pipelines)} pipelines from registry")
            
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            self.pipelines = {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        stats = {
            "total_pipelines": len(self.pipelines),
            "pipeline_types": {},
            "authors": {},
            "recent_pipelines": [],
            "most_used_tags": {}
        }
        
        # Count by type
        for pipeline in self.pipelines.values():
            pipeline_type = pipeline["pipeline_type"]
            stats["pipeline_types"][pipeline_type] = stats["pipeline_types"].get(pipeline_type, 0) + 1
        
        # Count by author
        for pipeline in self.pipelines.values():
            author = pipeline.get("author", "Unknown")
            stats["authors"][author] = stats["authors"].get(author, 0) + 1
        
        # Recent pipelines (last 10)
        recent_pipelines = sorted(
            self.pipelines.values(),
            key=lambda x: x["registered_at"],
            reverse=True
        )[:10]
        stats["recent_pipelines"] = [
            {"name": p["name"], "registered_at": p["registered_at"]}
            for p in recent_pipelines
        ]
        
        # Most used tags
        tag_counts = {}
        for pipeline in self.pipelines.values():
            for tag in pipeline["tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        stats["most_used_tags"] = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return stats
