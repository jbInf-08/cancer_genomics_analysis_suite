"""
Galaxy API Client

Provides functionality to interact with Galaxy instances for workflow execution,
data management, and tool access.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class GalaxyWorkflow:
    """Represents a Galaxy workflow"""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    tags: List[str]

@dataclass
class GalaxyDataset:
    """Represents a Galaxy dataset"""
    id: str
    name: str
    file_size: int
    file_type: str
    state: str
    download_url: Optional[str] = None

class GalaxyClient:
    """Client for interacting with Galaxy instances"""
    
    def __init__(self, base_url: str = "https://usegalaxy.org", api_key: Optional[str] = None):
        """
        Initialize Galaxy client
        
        Args:
            base_url: Galaxy instance URL
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({
                'X-API-Key': api_key,
                'Content-Type': 'application/json'
            })
    
    def get_workflows(self) -> List[GalaxyWorkflow]:
        """Get available workflows from Galaxy"""
        try:
            response = self.session.get(f"{self.api_url}/workflows")
            response.raise_for_status()
            
            workflows = []
            for workflow_data in response.json():
                workflow = GalaxyWorkflow(
                    id=workflow_data['id'],
                    name=workflow_data['name'],
                    description=workflow_data.get('description', ''),
                    steps=workflow_data.get('steps', []),
                    tags=workflow_data.get('tags', [])
                )
                workflows.append(workflow)
            
            return workflows
        except Exception as e:
            logger.error(f"Error fetching workflows: {e}")
            return []
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from Galaxy"""
        try:
            response = self.session.get(f"{self.api_url}/tools")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching tools: {e}")
            return []
    
    def upload_file(self, file_path: str, file_type: str = "auto") -> Optional[str]:
        """
        Upload a file to Galaxy
        
        Args:
            file_path: Path to file to upload
            file_type: Galaxy file type
            
        Returns:
            Dataset ID if successful, None otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'file_type': file_type}
                
                response = self.session.post(
                    f"{self.api_url}/tools/fetch",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get('outputs', [{}])[0].get('id')
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None
    
    def run_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Optional[str]:
        """
        Run a workflow with given inputs
        
        Args:
            workflow_id: ID of workflow to run
            inputs: Input parameters for workflow
            
        Returns:
            Job ID if successful, None otherwise
        """
        try:
            payload = {
                'workflow_id': workflow_id,
                'inputs': inputs
            }
            
            response = self.session.post(
                f"{self.api_url}/workflows/{workflow_id}/invocations",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('id')
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a running job"""
        try:
            response = self.session.get(f"{self.api_url}/jobs/{job_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {}
    
    def download_dataset(self, dataset_id: str, output_path: str) -> bool:
        """
        Download a dataset from Galaxy
        
        Args:
            dataset_id: ID of dataset to download
            output_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(f"{self.api_url}/datasets/{dataset_id}/display")
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            logger.error(f"Error downloading dataset: {e}")
            return False
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get user's analysis history"""
        try:
            response = self.session.get(f"{self.api_url}/histories")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            return []
    
    def create_history(self, name: str) -> Optional[str]:
        """Create a new analysis history"""
        try:
            payload = {'name': name}
            response = self.session.post(f"{self.api_url}/histories", json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get('id')
        except Exception as e:
            logger.error(f"Error creating history: {e}")
            return None
