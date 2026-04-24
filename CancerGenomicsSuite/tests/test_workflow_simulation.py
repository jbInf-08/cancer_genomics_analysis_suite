"""
Tests for workflow simulation module
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from simulate_workflow import WorkflowSimulator, WorkflowStep, WorkflowEngine


class TestWorkflowStep:
    """Test WorkflowStep class"""
    
    def test_init(self):
        """Test WorkflowStep initialization"""
        step = WorkflowStep(
            step_id="step1",
            name="Data Loading",
            step_type="data_loading",
            parameters={"input_file": "test.csv"}
        )
        
        assert step.step_id == "step1"
        assert step.name == "Data Loading"
        assert step.step_type == "data_loading"
        assert step.parameters == {"input_file": "test.csv"}
        assert step.status == "pending"
        assert step.start_time is None
        assert step.end_time is None
        assert step.error_message is None
    
    def test_start_execution(self):
        """Test starting step execution"""
        step = WorkflowStep("step1", "Test Step", "test")
        
        step.start_execution()
        
        assert step.status == "running"
        assert step.start_time is not None
    
    def test_complete_execution(self):
        """Test completing step execution"""
        step = WorkflowStep("step1", "Test Step", "test")
        step.start_execution()
        
        result = {"output": "test_result"}
        step.complete_execution(result)
        
        assert step.status == "completed"
        assert step.end_time is not None
        assert step.result == result
    
    def test_fail_execution(self):
        """Test failing step execution"""
        step = WorkflowStep("step1", "Test Step", "test")
        step.start_execution()
        
        error_msg = "Test error"
        step.fail_execution(error_msg)
        
        assert step.status == "failed"
        assert step.end_time is not None
        assert step.error_message == error_msg
    
    def test_get_duration(self):
        """Test getting step duration"""
        step = WorkflowStep("step1", "Test Step", "test")
        
        # Test with no execution
        assert step.get_duration() is None
        
        # Test with completed execution
        step.start_execution()
        step.complete_execution({"result": "test"})
        
        duration = step.get_duration()
        assert duration is not None
        assert duration >= 0
    
    def test_to_dict(self):
        """Test converting step to dictionary"""
        step = WorkflowStep("step1", "Test Step", "test", {"param": "value"})
        step.start_execution()
        step.complete_execution({"result": "test"})
        
        step_dict = step.to_dict()
        
        assert step_dict["step_id"] == "step1"
        assert step_dict["name"] == "Test Step"
        assert step_dict["step_type"] == "test"
        assert step_dict["parameters"] == {"param": "value"}
        assert step_dict["status"] == "completed"
        assert "start_time" in step_dict
        assert "end_time" in step_dict
        assert "duration" in step_dict


class TestWorkflowSimulator:
    """Test WorkflowSimulator class"""
    
    def test_init(self):
        """Test WorkflowSimulator initialization"""
        simulator = WorkflowSimulator()
        
        assert simulator.workflow_id is not None
        assert simulator.steps == []
        assert simulator.status == "pending"
        assert simulator.start_time is None
        assert simulator.end_time is None
    
    def test_add_step(self):
        """Test adding workflow steps"""
        simulator = WorkflowSimulator()
        
        step = WorkflowStep("step1", "Test Step", "test")
        simulator.add_step(step)
        
        assert len(simulator.steps) == 1
        assert simulator.steps[0] == step
    
    def test_add_multiple_steps(self):
        """Test adding multiple workflow steps"""
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step2 = WorkflowStep("step2", "Step 2", "test2")
        
        simulator.add_step(step1)
        simulator.add_step(step2)
        
        assert len(simulator.steps) == 2
        assert simulator.steps[0] == step1
        assert simulator.steps[1] == step2
    
    def test_get_step_by_id(self):
        """Test getting step by ID"""
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step2 = WorkflowStep("step2", "Step 2", "test2")
        
        simulator.add_step(step1)
        simulator.add_step(step2)
        
        found_step = simulator.get_step_by_id("step1")
        assert found_step == step1
        
        not_found = simulator.get_step_by_id("nonexistent")
        assert not_found is None
    
    def test_get_steps_by_status(self):
        """Test getting steps by status"""
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step2 = WorkflowStep("step2", "Step 2", "test2")
        step3 = WorkflowStep("step3", "Step 3", "test3")
        
        step1.start_execution()
        step1.complete_execution({"result": "test"})
        
        step2.start_execution()
        step2.fail_execution("Test error")
        
        simulator.add_step(step1)
        simulator.add_step(step2)
        simulator.add_step(step3)
        
        completed_steps = simulator.get_steps_by_status("completed")
        assert len(completed_steps) == 1
        assert completed_steps[0] == step1
        
        failed_steps = simulator.get_steps_by_status("failed")
        assert len(failed_steps) == 1
        assert failed_steps[0] == step2
        
        pending_steps = simulator.get_steps_by_status("pending")
        assert len(pending_steps) == 1
        assert pending_steps[0] == step3
    
    def test_get_workflow_progress(self):
        """Test getting workflow progress"""
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step2 = WorkflowStep("step2", "Step 2", "test2")
        step3 = WorkflowStep("step3", "Step 3", "test3")
        
        step1.start_execution()
        step1.complete_execution({"result": "test"})
        
        step2.start_execution()
        step2.fail_execution("Test error")
        
        simulator.add_step(step1)
        simulator.add_step(step2)
        simulator.add_step(step3)
        
        progress = simulator.get_workflow_progress()
        
        assert progress["total_steps"] == 3
        assert progress["completed_steps"] == 1
        assert progress["failed_steps"] == 1
        assert progress["pending_steps"] == 1
        assert progress["running_steps"] == 0
        assert progress["completion_percentage"] == 33.33
    
    def test_to_dict(self):
        """Test converting workflow to dictionary"""
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step1.start_execution()
        step1.complete_execution({"result": "test"})
        
        simulator.add_step(step1)
        simulator.start_workflow()
        simulator.complete_workflow()
        
        workflow_dict = simulator.to_dict()
        
        assert workflow_dict["workflow_id"] == simulator.workflow_id
        assert workflow_dict["status"] == "completed"
        assert len(workflow_dict["steps"]) == 1
        assert "start_time" in workflow_dict
        assert "end_time" in workflow_dict
        assert "duration" in workflow_dict


class TestWorkflowEngine:
    """Test WorkflowEngine class"""
    
    def test_init(self):
        """Test WorkflowEngine initialization"""
        engine = WorkflowEngine()
        
        assert engine.workflows == {}
        assert engine.max_concurrent_workflows == 5
    
    def test_init_with_max_concurrent(self):
        """Test WorkflowEngine initialization with max concurrent workflows"""
        engine = WorkflowEngine(max_concurrent_workflows=10)
        
        assert engine.max_concurrent_workflows == 10
    
    def test_create_workflow(self):
        """Test creating a new workflow"""
        engine = WorkflowEngine()
        
        workflow_id = engine.create_workflow()
        
        assert workflow_id in engine.workflows
        assert isinstance(engine.workflows[workflow_id], WorkflowSimulator)
    
    def test_get_workflow(self):
        """Test getting a workflow by ID"""
        engine = WorkflowEngine()
        
        workflow_id = engine.create_workflow()
        workflow = engine.get_workflow(workflow_id)
        
        assert workflow is not None
        assert isinstance(workflow, WorkflowSimulator)
        
        # Test getting non-existent workflow
        non_existent = engine.get_workflow("nonexistent")
        assert non_existent is None
    
    def test_list_workflows(self):
        """Test listing all workflows"""
        engine = WorkflowEngine()
        
        # Create multiple workflows
        workflow1 = engine.create_workflow()
        workflow2 = engine.create_workflow()
        
        workflows = engine.list_workflows()
        
        assert len(workflows) == 2
        assert workflow1 in workflows
        assert workflow2 in workflows
    
    def test_delete_workflow(self):
        """Test deleting a workflow"""
        engine = WorkflowEngine()
        
        workflow_id = engine.create_workflow()
        
        # Verify workflow exists
        assert workflow_id in engine.workflows
        
        # Delete workflow
        result = engine.delete_workflow(workflow_id)
        assert result is True
        
        # Verify workflow is deleted
        assert workflow_id not in engine.workflows
        
        # Test deleting non-existent workflow
        result = engine.delete_workflow("nonexistent")
        assert result is False
    
    def test_get_workflow_status(self):
        """Test getting workflow status"""
        engine = WorkflowEngine()
        
        workflow_id = engine.create_workflow()
        workflow = engine.get_workflow(workflow_id)
        
        status = engine.get_workflow_status(workflow_id)
        assert status == "pending"
        
        workflow.start_workflow()
        status = engine.get_workflow_status(workflow_id)
        assert status == "running"
        
        workflow.complete_workflow()
        status = engine.get_workflow_status(workflow_id)
        assert status == "completed"
    
    def test_get_workflow_progress(self):
        """Test getting workflow progress"""
        engine = WorkflowEngine()
        
        workflow_id = engine.create_workflow()
        workflow = engine.get_workflow(workflow_id)
        
        # Add some steps
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step2 = WorkflowStep("step2", "Step 2", "test2")
        
        step1.start_execution()
        step1.complete_execution({"result": "test"})
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        
        progress = engine.get_workflow_progress(workflow_id)
        
        assert progress["total_steps"] == 2
        assert progress["completed_steps"] == 1
        assert progress["pending_steps"] == 1
        assert progress["completion_percentage"] == 50.0


class TestWorkflowSimulation:
    """Test workflow simulation functionality"""
    
    def test_simulate_data_loading_workflow(self):
        """Test simulating a data loading workflow"""
        simulator = WorkflowSimulator()
        
        # Add data loading steps
        step1 = WorkflowStep("load_data", "Load Data", "data_loading", {"file": "data.csv"})
        step2 = WorkflowStep("validate_data", "Validate Data", "data_validation", {"schema": "clinical"})
        step3 = WorkflowStep("transform_data", "Transform Data", "data_transformation", {"format": "standard"})
        
        simulator.add_step(step1)
        simulator.add_step(step2)
        simulator.add_step(step3)
        
        # Simulate workflow execution
        simulator.start_workflow()
        
        # Simulate step execution
        step1.start_execution()
        step1.complete_execution({"rows_loaded": 1000})
        
        step2.start_execution()
        step2.complete_execution({"validation_passed": True})
        
        step3.start_execution()
        step3.complete_execution({"transformation_complete": True})
        
        simulator.complete_workflow()
        
        assert simulator.status == "completed"
        assert len(simulator.get_steps_by_status("completed")) == 3
    
    def test_simulate_analysis_workflow(self):
        """Test simulating an analysis workflow"""
        simulator = WorkflowSimulator()
        
        # Add analysis steps
        step1 = WorkflowStep("preprocess", "Preprocess Data", "preprocessing", {"method": "normalize"})
        step2 = WorkflowStep("analyze", "Run Analysis", "analysis", {"algorithm": "differential_expression"})
        step3 = WorkflowStep("visualize", "Create Visualizations", "visualization", {"charts": ["heatmap", "volcano"]})
        
        simulator.add_step(step1)
        simulator.add_step(step2)
        simulator.add_step(step3)
        
        # Simulate workflow execution
        simulator.start_workflow()
        
        # Simulate step execution with some failure
        step1.start_execution()
        step1.complete_execution({"preprocessing_complete": True})
        
        step2.start_execution()
        step2.fail_execution("Analysis failed due to insufficient data")
        
        simulator.fail_workflow("Analysis step failed")
        
        assert simulator.status == "failed"
        assert len(simulator.get_steps_by_status("completed")) == 1
        assert len(simulator.get_steps_by_status("failed")) == 1
        assert len(simulator.get_steps_by_status("pending")) == 1
    
    def test_simulate_ml_workflow(self):
        """Test simulating a machine learning workflow"""
        simulator = WorkflowSimulator()
        
        # Add ML steps
        step1 = WorkflowStep("feature_selection", "Feature Selection", "feature_selection", {"method": "variance_threshold"})
        step2 = WorkflowStep("train_model", "Train Model", "model_training", {"algorithm": "random_forest"})
        step3 = WorkflowStep("evaluate_model", "Evaluate Model", "model_evaluation", {"metrics": ["accuracy", "precision", "recall"]})
        step4 = WorkflowStep("predict", "Make Predictions", "prediction", {"test_data": "test.csv"})
        
        simulator.add_step(step1)
        simulator.add_step(step2)
        simulator.add_step(step3)
        simulator.add_step(step4)
        
        # Simulate workflow execution
        simulator.start_workflow()
        
        # Simulate successful execution
        for step in simulator.steps:
            step.start_execution()
            step.complete_execution({"result": f"Step {step.step_id} completed"})
        
        simulator.complete_workflow()
        
        assert simulator.status == "completed"
        assert len(simulator.get_steps_by_status("completed")) == 4
        
        # Check workflow duration
        duration = simulator.get_workflow_duration()
        assert duration is not None
        assert duration >= 0


class TestWorkflowPersistence:
    """Test workflow persistence functionality"""
    
    def test_save_workflow_to_file(self, temp_dir):
        """Test saving workflow to file"""
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step1.start_execution()
        step1.complete_execution({"result": "test"})
        
        simulator.add_step(step1)
        simulator.start_workflow()
        simulator.complete_workflow()
        
        file_path = os.path.join(temp_dir, "workflow.json")
        result = simulator.save_to_file(file_path)
        
        assert result is True
        assert os.path.exists(file_path)
        
        # Verify file content
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        assert data["workflow_id"] == simulator.workflow_id
        assert data["status"] == "completed"
        assert len(data["steps"]) == 1
    
    def test_load_workflow_from_file(self, temp_dir):
        """Test loading workflow from file"""
        # Create a workflow and save it
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step1.start_execution()
        step1.complete_execution({"result": "test"})
        
        simulator.add_step(step1)
        simulator.start_workflow()
        simulator.complete_workflow()
        
        file_path = os.path.join(temp_dir, "workflow.json")
        simulator.save_to_file(file_path)
        
        # Load workflow from file
        loaded_simulator = WorkflowSimulator.load_from_file(file_path)
        
        assert loaded_simulator.workflow_id == simulator.workflow_id
        assert loaded_simulator.status == simulator.status
        assert len(loaded_simulator.steps) == len(simulator.steps)
        assert loaded_simulator.steps[0].step_id == simulator.steps[0].step_id
    
    def test_workflow_serialization(self):
        """Test workflow serialization"""
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1", {"param": "value"})
        step1.start_execution()
        step1.complete_execution({"result": "test"})
        
        simulator.add_step(step1)
        simulator.start_workflow()
        simulator.complete_workflow()
        
        # Test JSON serialization
        json_str = simulator.to_json()
        assert isinstance(json_str, str)
        
        # Test deserialization
        loaded_simulator = WorkflowSimulator.from_json(json_str)
        
        assert loaded_simulator.workflow_id == simulator.workflow_id
        assert loaded_simulator.status == simulator.status
        assert len(loaded_simulator.steps) == len(simulator.steps)


class TestWorkflowErrorHandling:
    """Test workflow error handling"""
    
    def test_step_execution_error(self):
        """Test step execution error handling"""
        step = WorkflowStep("step1", "Test Step", "test")
        
        # Test normal execution
        step.start_execution()
        step.complete_execution({"result": "success"})
        
        assert step.status == "completed"
        assert step.error_message is None
        
        # Test error execution
        step2 = WorkflowStep("step2", "Test Step 2", "test")
        step2.start_execution()
        step2.fail_execution("Test error message")
        
        assert step2.status == "failed"
        assert step2.error_message == "Test error message"
    
    def test_workflow_error_handling(self):
        """Test workflow error handling"""
        simulator = WorkflowSimulator()
        
        step1 = WorkflowStep("step1", "Step 1", "test1")
        step2 = WorkflowStep("step2", "Step 2", "test2")
        
        simulator.add_step(step1)
        simulator.add_step(step2)
        
        # Start workflow
        simulator.start_workflow()
        
        # Complete first step
        step1.start_execution()
        step1.complete_execution({"result": "success"})
        
        # Fail second step
        step2.start_execution()
        step2.fail_execution("Step 2 failed")
        
        # Fail entire workflow
        simulator.fail_workflow("Workflow failed due to step failure")
        
        assert simulator.status == "failed"
        assert simulator.error_message == "Workflow failed due to step failure"
        assert len(simulator.get_steps_by_status("completed")) == 1
        assert len(simulator.get_steps_by_status("failed")) == 1
    
    def test_invalid_step_operations(self):
        """Test invalid step operations"""
        step = WorkflowStep("step1", "Test Step", "test")
        
        # Test completing without starting
        with pytest.raises(ValueError):
            step.complete_execution({"result": "test"})
        
        # Test failing without starting
        with pytest.raises(ValueError):
            step.fail_execution("Test error")
        
        # Test starting already started step
        step.start_execution()
        with pytest.raises(ValueError):
            step.start_execution()
        
        # Test completing already completed step
        step.complete_execution({"result": "test"})
        with pytest.raises(ValueError):
            step.complete_execution({"result": "test2"})


@pytest.mark.integration
class TestWorkflowIntegration:
    """Integration tests for workflow simulation"""
    
    @pytest.mark.slow
    def test_full_workflow_simulation(self):
        """Test complete workflow simulation"""
        engine = WorkflowEngine()
        
        # Create workflow
        workflow_id = engine.create_workflow()
        workflow = engine.get_workflow(workflow_id)
        
        # Add comprehensive workflow steps
        steps = [
            WorkflowStep("load_data", "Load Data", "data_loading", {"file": "data.csv"}),
            WorkflowStep("validate_data", "Validate Data", "data_validation", {"schema": "clinical"}),
            WorkflowStep("preprocess", "Preprocess Data", "preprocessing", {"method": "normalize"}),
            WorkflowStep("analyze", "Run Analysis", "analysis", {"algorithm": "differential_expression"}),
            WorkflowStep("visualize", "Create Visualizations", "visualization", {"charts": ["heatmap"]}),
            WorkflowStep("generate_report", "Generate Report", "reporting", {"format": "html"})
        ]
        
        for step in steps:
            workflow.add_step(step)
        
        # Execute workflow
        workflow.start_workflow()
        
        # Simulate step execution
        for i, step in enumerate(workflow.steps):
            step.start_execution()
            
            # Simulate some processing time
            import time
            time.sleep(0.01)  # Small delay for realistic simulation
            
            if i == 2:  # Fail preprocessing step
                step.fail_execution("Preprocessing failed due to data quality issues")
                workflow.fail_workflow("Workflow failed at preprocessing step")
                break
            else:
                step.complete_execution({"result": f"Step {step.step_id} completed successfully"})
        
        # Check final state
        if workflow.status == "failed":
            assert len(workflow.get_steps_by_status("completed")) == 2
            assert len(workflow.get_steps_by_status("failed")) == 1
            assert len(workflow.get_steps_by_status("pending")) == 3
        else:
            workflow.complete_workflow()
            assert workflow.status == "completed"
            assert len(workflow.get_steps_by_status("completed")) == 6
        
        # Test workflow persistence
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            workflow.save_to_file(temp_file)
            loaded_workflow = WorkflowSimulator.load_from_file(temp_file)
            
            assert loaded_workflow.workflow_id == workflow.workflow_id
            assert loaded_workflow.status == workflow.status
            assert len(loaded_workflow.steps) == len(workflow.steps)
        finally:
            os.unlink(temp_file)
