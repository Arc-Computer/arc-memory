"""Tests for the simulation mocks."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from arc_memory.simulate.mocks import (
    MockE2BHandle,
    MockFaultDriver,
    create_mock_simulation_results
)


class TestMockE2BHandle:
    """Tests for the MockE2BHandle class."""

    def test_init(self):
        """Test initialization."""
        handle = MockE2BHandle()
        assert handle.is_mock is True
        assert handle.commands == []
        assert handle.files == {}

    def test_run_command(self):
        """Test running a command."""
        handle = MockE2BHandle()
        result = handle.run_command("echo 'hello'")
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
        assert handle.commands == ["echo 'hello'"]

    def test_run_command_with_error(self):
        """Test running a command that returns an error."""
        handle = MockE2BHandle(should_fail=True)
        result = handle.run_command("echo 'hello'")
        assert result["exit_code"] == 1
        assert "Mock error" in result["stderr"]
        assert handle.commands == ["echo 'hello'"]

    def test_write_file(self):
        """Test writing a file."""
        handle = MockE2BHandle()
        handle.write_file("/path/to/file.txt", "hello world")
        assert handle.files["/path/to/file.txt"] == "hello world"

    def test_read_file(self):
        """Test reading a file."""
        handle = MockE2BHandle()
        handle.write_file("/path/to/file.txt", "hello world")
        content = handle.read_file("/path/to/file.txt")
        assert content == "hello world"

    def test_read_file_not_found(self):
        """Test reading a file that doesn't exist."""
        handle = MockE2BHandle()
        with pytest.raises(FileNotFoundError):
            handle.read_file("/path/to/nonexistent.txt")

    def test_file_exists(self):
        """Test checking if a file exists."""
        handle = MockE2BHandle()
        handle.write_file("/path/to/file.txt", "hello world")
        assert handle.file_exists("/path/to/file.txt") is True
        assert handle.file_exists("/path/to/nonexistent.txt") is False

    def test_list_files(self):
        """Test listing files in a directory."""
        handle = MockE2BHandle()
        handle.write_file("/path/to/file1.txt", "hello")
        handle.write_file("/path/to/file2.txt", "world")
        handle.write_file("/other/path/file3.txt", "!")
        files = handle.list_files("/path/to")
        assert len(files) == 2
        assert "/path/to/file1.txt" in files
        assert "/path/to/file2.txt" in files
        assert "/other/path/file3.txt" not in files

    def test_create_directory(self):
        """Test creating a directory."""
        handle = MockE2BHandle()
        handle.create_directory("/path/to/dir")
        assert handle.directories == ["/path/to/dir"]

    def test_close(self):
        """Test closing the handle."""
        handle = MockE2BHandle()
        handle.close()
        assert handle.is_closed is True


class TestMockFaultDriver:
    """Tests for the MockFaultDriver class."""

    def test_init(self):
        """Test initialization."""
        driver = MockFaultDriver()
        assert driver.is_mock is True
        assert driver.experiments == []
        assert driver.metrics == {}

    def test_apply_network_latency(self):
        """Test applying network latency."""
        driver = MockFaultDriver()
        result = driver.apply_network_latency(
            target_services=["service1", "service2"],
            latency_ms=500,
            duration_seconds=60
        )
        assert result["status"] == "success"
        assert result["experiment_name"] is not None
        assert len(driver.experiments) == 1
        assert driver.experiments[0]["type"] == "network_latency"
        assert driver.experiments[0]["target_services"] == ["service1", "service2"]
        assert driver.experiments[0]["latency_ms"] == 500
        assert driver.experiments[0]["duration_seconds"] == 60

    def test_apply_cpu_stress(self):
        """Test applying CPU stress."""
        driver = MockFaultDriver()
        result = driver.apply_cpu_stress(
            target_services=["service1"],
            cpu_load=80,
            duration_seconds=60
        )
        assert result["status"] == "success"
        assert result["experiment_name"] is not None
        assert len(driver.experiments) == 1
        assert driver.experiments[0]["type"] == "cpu_stress"
        assert driver.experiments[0]["target_services"] == ["service1"]
        assert driver.experiments[0]["cpu_load"] == 80
        assert driver.experiments[0]["duration_seconds"] == 60

    def test_apply_memory_stress(self):
        """Test applying memory stress."""
        driver = MockFaultDriver()
        result = driver.apply_memory_stress(
            target_services=["service1"],
            memory_mb=500,
            duration_seconds=60
        )
        assert result["status"] == "success"
        assert result["experiment_name"] is not None
        assert len(driver.experiments) == 1
        assert driver.experiments[0]["type"] == "memory_stress"
        assert driver.experiments[0]["target_services"] == ["service1"]
        assert driver.experiments[0]["memory_mb"] == 500
        assert driver.experiments[0]["duration_seconds"] == 60

    def test_collect_metrics(self):
        """Test collecting metrics."""
        driver = MockFaultDriver()
        # Apply an experiment to set up metrics
        driver.apply_network_latency(
            target_services=["service1", "service2"],
            latency_ms=500,
            duration_seconds=60
        )
        metrics = driver.collect_metrics()
        assert "node_count" in metrics
        assert "pod_count" in metrics
        assert "service_count" in metrics
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert "latency_ms" in metrics
        assert "error_rate" in metrics

    def test_collect_metrics_with_custom_metrics(self):
        """Test collecting metrics with custom metrics."""
        driver = MockFaultDriver(custom_metrics={
            "custom_metric": 42,
            "another_metric": "value"
        })
        metrics = driver.collect_metrics()
        assert "custom_metric" in metrics
        assert metrics["custom_metric"] == 42
        assert "another_metric" in metrics
        assert metrics["another_metric"] == "value"

    def test_cleanup(self):
        """Test cleaning up experiments."""
        driver = MockFaultDriver()
        # Apply some experiments
        driver.apply_network_latency(
            target_services=["service1", "service2"],
            latency_ms=500,
            duration_seconds=60
        )
        driver.apply_cpu_stress(
            target_services=["service1"],
            cpu_load=80,
            duration_seconds=60
        )
        assert len(driver.experiments) == 2
        # Clean up
        driver.cleanup()
        assert len(driver.experiments) == 0


def test_create_mock_simulation_results():
    """Test creating mock simulation results."""
    # Test with default parameters
    results = create_mock_simulation_results()
    assert "experiment_name" in results
    assert "duration_seconds" in results
    assert "initial_metrics" in results
    assert "final_metrics" in results
    assert "is_mock" in results
    assert results["is_mock"] is True

    # Test with custom parameters
    results = create_mock_simulation_results(
        experiment_name="custom-experiment",
        duration_seconds=120,
        scenario="cpu_stress",
        severity=75,
        affected_services=["service1", "service2", "service3"]
    )
    assert results["experiment_name"] == "custom-experiment"
    assert results["duration_seconds"] == 120
    # Don't check for scenario in experiment_name when a custom name is provided
    assert len(results["final_metrics"]["cpu_usage"]) == 3  # One for each service
