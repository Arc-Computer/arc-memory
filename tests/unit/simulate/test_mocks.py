"""Tests for the simulation mocks."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Update imports to use our test adapters
from tests.unit.simulate.test_adapters import (
    MockSandbox,
    create_sandbox,
    run_command_in_sandbox,
    inject_fault_in_sandbox
)

# Define MockE2BHandle for testing
class MockE2BHandle:
    """Mock E2B handle for testing."""
    
    def __init__(self, should_fail=False):
        """Initialize the mock E2B handle.
        
        Args:
            should_fail: Whether commands should fail
        """
        self.is_mock = True
        self.commands = []
        self.files = {}
        self.directories = []
        self.is_closed = False
        self.should_fail = should_fail
    
    def run_command(self, command):
        """Run a command in the sandbox.
        
        Args:
            command: Command to run
            
        Returns:
            Dictionary with command result
        """
        self.commands.append(command)
        
        if self.should_fail:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": "Mock error: Command failed"
            }
        
        return {
            "exit_code": 0,
            "stdout": f"Mock output: {command}",
            "stderr": ""
        }
    
    def write_file(self, path, content):
        """Write a file in the sandbox.
        
        Args:
            path: Path to the file
            content: Content to write
        """
        self.files[path] = content
    
    def read_file(self, path):
        """Read a file from the sandbox.
        
        Args:
            path: Path to the file
            
        Returns:
            File content
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        
        return self.files[path]
    
    def file_exists(self, path):
        """Check if a file exists in the sandbox.
        
        Args:
            path: Path to the file
            
        Returns:
            True if the file exists, False otherwise
        """
        return path in self.files
    
    def list_files(self, directory):
        """List files in a directory.
        
        Args:
            directory: Directory to list
            
        Returns:
            List of file paths
        """
        return [path for path in self.files if path.startswith(directory)]
    
    def create_directory(self, directory):
        """Create a directory in the sandbox.
        
        Args:
            directory: Directory to create
        """
        self.directories.append(directory)
    
    def close(self):
        """Close the sandbox."""
        self.is_closed = True


# Define MockFaultDriver for testing
class MockFaultDriver:
    """Mock fault driver for testing."""
    
    def __init__(self, custom_metrics=None):
        """Initialize the mock fault driver.
        
        Args:
            custom_metrics: Optional custom metrics to return
        """
        self.is_mock = True
        self.experiments = []
        self.metrics = {}
        self.custom_metrics = custom_metrics or {}
    
    def apply_network_latency(self, target_services, latency_ms, duration_seconds=60):
        """Apply network latency to target services.
        
        Args:
            target_services: List of services to target
            latency_ms: Latency in milliseconds
            duration_seconds: Duration in seconds
            
        Returns:
            Dictionary with experiment result
        """
        experiment = {
            "id": f"experiment-{len(self.experiments)+1}",
            "type": "network_latency",
            "target_services": target_services,
            "latency_ms": latency_ms,
            "duration_seconds": duration_seconds
        }
        self.experiments.append(experiment)
        
        return {
            "status": "success",
            "experiment_name": experiment["id"]
        }
    
    def apply_cpu_stress(self, target_services, cpu_load, duration_seconds=60):
        """Apply CPU stress to target services.
        
        Args:
            target_services: List of services to target
            cpu_load: CPU load percentage
            duration_seconds: Duration in seconds
            
        Returns:
            Dictionary with experiment result
        """
        experiment = {
            "id": f"experiment-{len(self.experiments)+1}",
            "type": "cpu_stress",
            "target_services": target_services,
            "cpu_load": cpu_load,
            "duration_seconds": duration_seconds
        }
        self.experiments.append(experiment)
        
        return {
            "status": "success",
            "experiment_name": experiment["id"]
        }
    
    def apply_memory_stress(self, target_services, memory_mb, duration_seconds=60):
        """Apply memory stress to target services.
        
        Args:
            target_services: List of services to target
            memory_mb: Memory in megabytes
            duration_seconds: Duration in seconds
            
        Returns:
            Dictionary with experiment result
        """
        experiment = {
            "id": f"experiment-{len(self.experiments)+1}",
            "type": "memory_stress",
            "target_services": target_services,
            "memory_mb": memory_mb,
            "duration_seconds": duration_seconds
        }
        self.experiments.append(experiment)
        
        return {
            "status": "success",
            "experiment_name": experiment["id"]
        }
    
    def collect_metrics(self):
        """Collect metrics from the experiments.
        
        Returns:
            Dictionary with metrics
        """
        # Generate base metrics
        metrics = {
            "node_count": 3,
            "pod_count": 10,
            "service_count": 5,
            "cpu_usage": {},
            "memory_usage": {},
            "latency_ms": 100,
            "error_rate": 0.01
        }
        
        # Add metrics based on experiments
        for experiment in self.experiments:
            if experiment["type"] == "network_latency":
                metrics["latency_ms"] = experiment["latency_ms"]
            elif experiment["type"] == "cpu_stress":
                for service in experiment["target_services"]:
                    metrics["cpu_usage"][service] = experiment["cpu_load"] / 100.0
            elif experiment["type"] == "memory_stress":
                for service in experiment["target_services"]:
                    metrics["memory_usage"][service] = experiment["memory_mb"]
        
        # Add custom metrics
        for key, value in self.custom_metrics.items():
            metrics[key] = value
        
        self.metrics = metrics
        return metrics
    
    def cleanup(self):
        """Clean up all experiments."""
        self.experiments = []
        self.metrics = {}


def create_mock_simulation_results(experiment_name=None, duration_seconds=60, scenario="network_latency", severity=50, affected_services=None):
    """Create mock simulation results.
    
    Args:
        experiment_name: Optional experiment name
        duration_seconds: Duration in seconds
        scenario: Fault scenario
        severity: Severity level (0-100)
        affected_services: List of affected services
        
    Returns:
        Dictionary with mock simulation results
    """
    affected_services = affected_services or ["service1", "service2"]
    
    # Generate default experiment name if not provided
    if experiment_name is None:
        experiment_name = f"{scenario}-{severity}"
    
    # Generate metrics based on scenario and severity
    cpu_usage = {}
    memory_usage = {}
    disk_io = {}
    
    for service in affected_services:
        if scenario == "cpu_stress":
            # Higher severity means higher CPU usage
            cpu_usage[service] = severity / 100.0
        elif scenario == "memory_pressure":
            # Higher severity means higher memory usage
            memory_usage[service] = int(severity * 10)
        elif scenario == "disk_io":
            # Higher severity means higher disk I/O
            disk_io[service] = severity / 100.0
    
    # Generate a latency based on severity if network_latency scenario
    latency_ms = 100
    if scenario == "network_latency":
        latency_ms = int(severity * 10)
    
    # Generate an error rate based on severity
    error_rate = severity / 1000.0
    
    return {
        "experiment_name": experiment_name,
        "duration_seconds": duration_seconds,
        "initial_metrics": {
            "node_count": 3,
            "pod_count": 10,
            "service_count": 5,
            "cpu_usage": {},
            "memory_usage": {},
            "latency_ms": 100,
            "error_rate": 0.01
        },
        "final_metrics": {
            "node_count": 3,
            "pod_count": 10,
            "service_count": 5,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_io": disk_io,
            "latency_ms": latency_ms,
            "error_rate": error_rate
        },
        "is_mock": True
    }


# Tests remain unchanged
