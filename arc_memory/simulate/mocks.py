"""Mock implementations for testing simulation components."""

import os
import random
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union


class MockE2BHandle:
    """Mock implementation of the E2B handle for testing."""

    def __init__(self, should_fail: bool = False):
        """Initialize the mock E2B handle.

        Args:
            should_fail: Whether commands should fail
        """
        self.is_mock = True
        self.commands = []
        self.files = {}
        self.directories = []
        self.should_fail = should_fail
        self.is_closed = False

    def run_command(self, command: str) -> Dict[str, Any]:
        """Run a command in the sandbox.

        Args:
            command: The command to run

        Returns:
            A dictionary with the command output
        """
        self.commands.append(command)
        
        if self.should_fail:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Mock error: {command}"
            }
        
        return {
            "exit_code": 0,
            "stdout": f"Mock output for: {command}",
            "stderr": ""
        }

    def write_file(self, path: str, content: str) -> None:
        """Write a file in the sandbox.

        Args:
            path: The path to write to
            content: The content to write
        """
        self.files[path] = content

    def read_file(self, path: str) -> str:
        """Read a file from the sandbox.

        Args:
            path: The path to read from

        Returns:
            The file content

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if path not in self.files:
            raise FileNotFoundError(f"Mock file not found: {path}")
        
        return self.files[path]

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in the sandbox.

        Args:
            path: The path to check

        Returns:
            True if the file exists, False otherwise
        """
        return path in self.files

    def list_files(self, directory: str) -> List[str]:
        """List files in a directory.

        Args:
            directory: The directory to list

        Returns:
            A list of file paths
        """
        return [path for path in self.files.keys() if path.startswith(directory)]

    def create_directory(self, path: str) -> None:
        """Create a directory in the sandbox.

        Args:
            path: The directory path to create
        """
        self.directories.append(path)

    def close(self) -> None:
        """Close the sandbox."""
        self.is_closed = True


class MockFaultDriver:
    """Mock implementation of the fault driver for testing."""

    def __init__(self, custom_metrics: Optional[Dict[str, Any]] = None):
        """Initialize the mock fault driver.

        Args:
            custom_metrics: Custom metrics to include in the results
        """
        self.is_mock = True
        self.experiments = []
        self.metrics = custom_metrics or {}

    def apply_network_latency(
        self,
        target_services: List[str],
        latency_ms: int,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Apply network latency to target services.

        Args:
            target_services: The services to target
            latency_ms: The latency to apply in milliseconds
            duration_seconds: The duration of the experiment in seconds

        Returns:
            A dictionary with the experiment details
        """
        experiment = {
            "type": "network_latency",
            "target_services": target_services,
            "latency_ms": latency_ms,
            "duration_seconds": duration_seconds,
            "timestamp": time.time()
        }
        self.experiments.append(experiment)
        
        # Update metrics
        self.metrics["latency_ms"] = latency_ms
        self.metrics["error_rate"] = round(latency_ms / 10000, 3)  # Simulate error rate based on latency
        
        return {
            "status": "success",
            "experiment_name": f"network-latency-{uuid.uuid4().hex[:8]}"
        }

    def apply_cpu_stress(
        self,
        target_services: List[str],
        cpu_load: int,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Apply CPU stress to target services.

        Args:
            target_services: The services to target
            cpu_load: The CPU load percentage to apply
            duration_seconds: The duration of the experiment in seconds

        Returns:
            A dictionary with the experiment details
        """
        experiment = {
            "type": "cpu_stress",
            "target_services": target_services,
            "cpu_load": cpu_load,
            "duration_seconds": duration_seconds,
            "timestamp": time.time()
        }
        self.experiments.append(experiment)
        
        # Update metrics
        self.metrics["cpu_usage"] = {
            service: cpu_load / 100 for service in target_services
        }
        
        return {
            "status": "success",
            "experiment_name": f"cpu-stress-{uuid.uuid4().hex[:8]}"
        }

    def apply_memory_stress(
        self,
        target_services: List[str],
        memory_mb: int,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Apply memory stress to target services.

        Args:
            target_services: The services to target
            memory_mb: The memory to consume in MB
            duration_seconds: The duration of the experiment in seconds

        Returns:
            A dictionary with the experiment details
        """
        experiment = {
            "type": "memory_stress",
            "target_services": target_services,
            "memory_mb": memory_mb,
            "duration_seconds": duration_seconds,
            "timestamp": time.time()
        }
        self.experiments.append(experiment)
        
        # Update metrics
        self.metrics["memory_usage"] = {
            service: memory_mb for service in target_services
        }
        
        return {
            "status": "success",
            "experiment_name": f"memory-stress-{uuid.uuid4().hex[:8]}"
        }

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from the cluster.

        Returns:
            A dictionary with the metrics
        """
        # Generate some basic metrics if not already set
        if "node_count" not in self.metrics:
            self.metrics["node_count"] = 1
        
        if "pod_count" not in self.metrics:
            self.metrics["pod_count"] = random.randint(3, 10)
        
        if "service_count" not in self.metrics:
            self.metrics["service_count"] = random.randint(2, 5)
        
        if "cpu_usage" not in self.metrics:
            self.metrics["cpu_usage"] = {
                f"service{i}": round(random.uniform(0.1, 0.9), 2)
                for i in range(1, self.metrics["service_count"] + 1)
            }
        
        if "memory_usage" not in self.metrics:
            self.metrics["memory_usage"] = {
                f"service{i}": random.randint(100, 500)
                for i in range(1, self.metrics["service_count"] + 1)
            }
        
        if "latency_ms" not in self.metrics:
            self.metrics["latency_ms"] = random.randint(50, 1000)
        
        if "error_rate" not in self.metrics:
            self.metrics["error_rate"] = round(random.uniform(0.01, 0.1), 3)
        
        return self.metrics.copy()

    def cleanup(self) -> None:
        """Clean up all experiments."""
        self.experiments = []


def create_mock_simulation_results(
    experiment_name: Optional[str] = None,
    duration_seconds: int = 60,
    scenario: str = "network_latency",
    severity: int = 50,
    affected_services: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create mock simulation results for testing.

    Args:
        experiment_name: The experiment name
        duration_seconds: The duration of the experiment in seconds
        scenario: The fault scenario
        severity: The severity level
        affected_services: The affected services

    Returns:
        A dictionary with the simulation results
    """
    if affected_services is None:
        affected_services = ["service1", "service2"]
    
    if experiment_name is None:
        experiment_name = f"{scenario}-{uuid.uuid4().hex[:8]}"
    
    # Generate metrics based on scenario and severity
    if scenario == "network_latency":
        latency_ms = severity * 10
        error_rate = round(severity / 1000, 3)
    elif scenario == "cpu_stress":
        latency_ms = severity * 5
        error_rate = round(severity / 2000, 3)
    else:  # memory_stress or other
        latency_ms = severity * 3
        error_rate = round(severity / 3000, 3)
    
    # Generate CPU and memory usage for each service
    cpu_usage = {
        service: round(random.uniform(0.3, 0.8), 2)
        for service in affected_services
    }
    
    memory_usage = {
        service: random.randint(100, 500)
        for service in affected_services
    }
    
    # Create metrics history
    metrics_history = [
        {
            "timestamp": f"2023-01-01T00:00:{i*30:02d}Z",
            "cpu_usage": {
                service: round(random.uniform(0.2, 0.6), 2)
                for service in affected_services
            },
            "memory_usage": {
                service: random.randint(80, 400)
                for service in affected_services
            }
        }
        for i in range(duration_seconds // 30)
    ]
    
    # Add final metrics
    metrics_history.append({
        "timestamp": f"2023-01-01T00:{duration_seconds//60:02d}:{duration_seconds%60:02d}Z",
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage
    })
    
    return {
        "experiment_name": experiment_name,
        "duration_seconds": duration_seconds,
        "initial_metrics": {
            "node_count": 1,
            "pod_count": len(affected_services) + 2,
            "service_count": len(affected_services)
        },
        "final_metrics": {
            "node_count": 1,
            "pod_count": len(affected_services) + 2,
            "service_count": len(affected_services),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "latency_ms": latency_ms,
            "error_rate": error_rate
        },
        "metrics_history": metrics_history,
        "is_mock": True
    }
