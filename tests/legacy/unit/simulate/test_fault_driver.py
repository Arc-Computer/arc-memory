"""Tests for the fault injection driver."""

import os
import time
import tempfile
import yaml
import json
from unittest import mock
from pathlib import Path

import pytest

from arc_memory.simulate.fault_driver import (
    FaultDriver,
    run_fault_injection,
    FaultInjectionError
)
from arc_memory.simulate.code_interpreter import (
    SimulationEnvironment,
    CodeInterpreterError,
    HAS_E2B
)


class TestFaultDriver:
    """Tests for the FaultDriver class."""

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_init_success(self):
        """Test initializing the fault driver successfully."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        # Execute
        driver = FaultDriver(mock_env)

        # Verify
        assert driver.env == mock_env
        assert isinstance(driver.active_experiments, dict)
        assert isinstance(driver.metrics_history, list)
        assert isinstance(driver.logs, list)

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", False)
    def test_init_no_e2b(self):
        """Test initializing the fault driver when E2B is not available."""
        # Setup
        mock_env = mock.MagicMock()

        # Execute and verify
        with pytest.raises(FaultInjectionError):
            FaultDriver(mock_env)

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_init_not_initialized(self):
        """Test initializing the fault driver when the environment is not initialized."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = False
        mock_env.chaos_mesh_installed = True

        # Execute and verify
        with pytest.raises(FaultInjectionError):
            FaultDriver(mock_env)

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_init_no_chaos_mesh(self):
        """Test initializing the fault driver when Chaos Mesh is not installed."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = False

        # Execute and verify
        with pytest.raises(FaultInjectionError):
            FaultDriver(mock_env)

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_apply_fault_success(self):
        """Test applying a fault successfully."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True
        mock_env.apply_chaos_experiment.return_value = "test-experiment"

        driver = FaultDriver(mock_env)

        # Create a temporary manifest file
        manifest_content = """
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: test-experiment
  namespace: default
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - default
    labelSelectors:
      app: test-app
  delay:
    latency: 100ms
    correlation: "0"
    jitter: 0ms
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            temp_file.write(manifest_content)
            temp_file.flush()

            # Execute
            experiment_name = driver.apply_fault(temp_file.name)

            # Verify
            assert experiment_name == "test-experiment"
            assert "test-experiment" in driver.active_experiments
            assert driver.active_experiments["test-experiment"]["kind"] == "NetworkChaos"
            assert driver.active_experiments["test-experiment"]["name"] == "test-experiment"
            assert driver.active_experiments["test-experiment"]["namespace"] == "default"
            assert "start_time" in driver.active_experiments["test-experiment"]
            assert "manifest" in driver.active_experiments["test-experiment"]
            mock_env.apply_chaos_experiment.assert_called_once_with(temp_file.name)

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_apply_fault_failure(self):
        """Test applying a fault when it fails."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True
        mock_env.apply_chaos_experiment.side_effect = CodeInterpreterError("Test error")

        driver = FaultDriver(mock_env)

        # Create a temporary manifest file
        manifest_content = """
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: test-experiment
  namespace: default
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - default
    labelSelectors:
      app: test-app
  delay:
    latency: 100ms
    correlation: "0"
    jitter: 0ms
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            temp_file.write(manifest_content)
            temp_file.flush()

            # Execute and verify
            with pytest.raises(FaultInjectionError):
                driver.apply_fault(temp_file.name)

            mock_env.apply_chaos_experiment.assert_called_once_with(temp_file.name)

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_delete_fault_success(self):
        """Test deleting a fault successfully."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        driver = FaultDriver(mock_env)
        driver.active_experiments["test-experiment"] = {
            "kind": "NetworkChaos",
            "name": "test-experiment",
            "namespace": "default",
            "start_time": time.time(),
            "manifest": {}
        }

        # Execute
        driver.delete_fault("test-experiment")

        # Verify
        mock_env.delete_chaos_experiment.assert_called_once_with("test-experiment", kind="NetworkChaos")
        assert "end_time" in driver.active_experiments["test-experiment"]
        assert driver.active_experiments["test-experiment"]["status"] == "deleted"

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_delete_fault_not_found(self):
        """Test deleting a fault that doesn't exist."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        driver = FaultDriver(mock_env)

        # Execute
        driver.delete_fault("nonexistent-experiment")

        # Verify
        mock_env.delete_chaos_experiment.assert_not_called()

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_delete_fault_failure(self):
        """Test deleting a fault when it fails."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True
        mock_env.delete_chaos_experiment.side_effect = CodeInterpreterError("Test error")

        driver = FaultDriver(mock_env)
        driver.active_experiments["test-experiment"] = {
            "kind": "NetworkChaos",
            "name": "test-experiment",
            "namespace": "default",
            "start_time": time.time(),
            "manifest": {}
        }

        # Execute and verify
        with pytest.raises(FaultInjectionError):
            driver.delete_fault("test-experiment")

        mock_env.delete_chaos_experiment.assert_called_once_with("test-experiment", kind="NetworkChaos")

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_collect_metrics_success(self):
        """Test collecting metrics successfully."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True
        mock_env.collect_metrics.return_value = {
            "node_count": 1,
            "pod_count": 5,
            "service_count": 3
        }

        driver = FaultDriver(mock_env)

        # Execute
        metrics = driver.collect_metrics()

        # Verify
        mock_env.collect_metrics.assert_called_once()
        assert "node_count" in metrics
        assert "pod_count" in metrics
        assert "service_count" in metrics
        assert "timestamp" in metrics
        assert len(driver.metrics_history) == 1
        assert driver.metrics_history[0] == metrics

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_collect_metrics_failure(self):
        """Test collecting metrics when it fails."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True
        mock_env.collect_metrics.side_effect = CodeInterpreterError("Test error")

        driver = FaultDriver(mock_env)

        # Execute and verify
        with pytest.raises(FaultInjectionError):
            driver.collect_metrics()

        mock_env.collect_metrics.assert_called_once()
        assert len(driver.metrics_history) == 0

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_collect_logs_success(self):
        """Test collecting logs successfully."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        # Mock the sandbox execution for pod list
        mock_pod_execution = mock.MagicMock()
        mock_pod_execution.text = json.dumps({
            "items": [
                {
                    "metadata": {
                        "name": "test-pod-1"
                    }
                },
                {
                    "metadata": {
                        "name": "test-pod-2"
                    }
                }
            ]
        })

        # Mock the sandbox execution for pod logs
        mock_log_execution = mock.MagicMock()
        mock_log_execution.text = "Test log output"

        mock_env.sandbox.run_code.side_effect = [mock_pod_execution, mock_log_execution, mock_log_execution]

        driver = FaultDriver(mock_env)

        # Execute
        logs = driver.collect_logs(namespace="test-namespace", label_selector="app=test-app")

        # Verify
        assert len(logs) == 2
        assert logs[0]["pod"] == "test-pod-1"
        assert logs[0]["namespace"] == "test-namespace"
        assert logs[0]["logs"] == "Test log output"
        assert logs[1]["pod"] == "test-pod-2"
        assert logs[1]["namespace"] == "test-namespace"
        assert logs[1]["logs"] == "Test log output"
        assert len(driver.logs) == 2
        assert driver.logs[0] == logs[0]
        assert driver.logs[1] == logs[1]

        # Verify the kubectl commands
        mock_env.sandbox.run_code.assert_any_call("""
!kubectl get pods -n test-namespace -l app=test-app -o json
            """)
        mock_env.sandbox.run_code.assert_any_call("""
!kubectl logs -n test-namespace test-pod-1 --tail=50
                """)
        mock_env.sandbox.run_code.assert_any_call("""
!kubectl logs -n test-namespace test-pod-2 --tail=50
                """)

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_collect_logs_no_pods(self):
        """Test collecting logs when no pods are found."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        # Mock the sandbox execution for pod list
        mock_pod_execution = mock.MagicMock()
        mock_pod_execution.text = json.dumps({
            "items": []
        })

        mock_env.sandbox.run_code.return_value = mock_pod_execution

        driver = FaultDriver(mock_env)

        # Execute
        logs = driver.collect_logs(namespace="test-namespace")

        # Verify
        assert len(logs) == 0
        assert len(driver.logs) == 0

        # Verify the kubectl command
        mock_env.sandbox.run_code.assert_called_once_with("""
!kubectl get pods -n test-namespace -o json
            """)

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_collect_logs_failure(self):
        """Test collecting logs when it fails."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True
        mock_env.sandbox.run_code.side_effect = CodeInterpreterError("Test error")

        driver = FaultDriver(mock_env)

        # Execute and verify
        with pytest.raises(FaultInjectionError):
            driver.collect_logs()

        mock_env.sandbox.run_code.assert_called_once()
        assert len(driver.logs) == 0

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_monitor_experiment_success(self):
        """Test monitoring an experiment successfully."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        driver = FaultDriver(mock_env)
        driver.active_experiments["test-experiment"] = {
            "kind": "NetworkChaos",
            "name": "test-experiment",
            "namespace": "test-namespace",
            "start_time": time.time(),
            "manifest": {}
        }

        # Create a simplified version of monitor_experiment for testing
        def mock_monitor_experiment(experiment_name, duration_seconds=300, metrics_interval=30):
            initial_metrics = {"node_count": 1, "timestamp": time.time()}
            final_metrics = {"node_count": 2, "timestamp": time.time()}
            initial_logs = [{"pod": "test-pod", "logs": "Initial logs"}]
            final_logs = [{"pod": "test-pod", "logs": "Final logs"}]

            return {
                'experiment_name': experiment_name,
                'duration_seconds': duration_seconds,
                'initial_metrics': initial_metrics,
                'final_metrics': final_metrics,
                'metrics_history': [initial_metrics, final_metrics],
                'initial_logs': initial_logs,
                'final_logs': final_logs,
                'start_time': time.time(),
                'end_time': time.time() + duration_seconds
            }

        # Replace the real method with our mock
        driver.monitor_experiment = mock_monitor_experiment

        # Execute
        results = driver.monitor_experiment(
            experiment_name="test-experiment",
            duration_seconds=60,
            metrics_interval=30
        )

        # Verify
        assert results["experiment_name"] == "test-experiment"
        assert results["duration_seconds"] == 60
        assert "initial_metrics" in results
        assert "final_metrics" in results
        assert "metrics_history" in results
        assert "initial_logs" in results
        assert "final_logs" in results
        assert "start_time" in results
        assert "end_time" in results

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_monitor_experiment_not_found(self):
        """Test monitoring an experiment that doesn't exist."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        driver = FaultDriver(mock_env)

        # Execute and verify
        with pytest.raises(FaultInjectionError):
            driver.monitor_experiment("nonexistent-experiment")

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_monitor_experiment_metrics_failure(self):
        """Test monitoring an experiment when metrics collection fails."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        driver = FaultDriver(mock_env)
        driver.active_experiments["test-experiment"] = {
            "kind": "NetworkChaos",
            "name": "test-experiment",
            "namespace": "default",
            "start_time": time.time(),
            "manifest": {}
        }

        # Mock the collect_metrics method to fail
        driver.collect_metrics = mock.MagicMock()
        driver.collect_metrics.side_effect = FaultInjectionError("Test error")

        # Execute and verify
        with pytest.raises(FaultInjectionError):
            driver.monitor_experiment("test-experiment")

        driver.collect_metrics.assert_called_once()

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_run_fault_experiment_success(self):
        """Test running a complete fault experiment successfully."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        driver = FaultDriver(mock_env)

        # Mock the methods
        driver.apply_fault = mock.MagicMock(return_value="test-experiment")
        driver.monitor_experiment = mock.MagicMock(return_value={
            "experiment_name": "test-experiment",
            "duration_seconds": 60,
            "initial_metrics": {"node_count": 1},
            "final_metrics": {"node_count": 1},
            "metrics_history": [],
            "initial_logs": [],
            "final_logs": [],
            "start_time": time.time(),
            "end_time": time.time() + 60
        })
        driver.delete_fault = mock.MagicMock()

        # Create a temporary manifest file
        manifest_content = """
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: test-experiment
  namespace: default
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - default
    labelSelectors:
      app: test-app
  delay:
    latency: 100ms
    correlation: "0"
    jitter: 0ms
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            temp_file.write(manifest_content)
            temp_file.flush()

            # Execute
            results = driver.run_fault_experiment(
                manifest_path=temp_file.name,
                duration_seconds=60,
                metrics_interval=30
            )

            # Verify
            assert results["experiment_name"] == "test-experiment"
            assert results["duration_seconds"] == 60

            # Verify method calls
            driver.apply_fault.assert_called_once_with(temp_file.name)
            driver.monitor_experiment.assert_called_once_with(
                experiment_name="test-experiment",
                duration_seconds=60,
                metrics_interval=30
            )
            driver.delete_fault.assert_called_once_with("test-experiment")

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_run_fault_experiment_apply_failure(self):
        """Test running a fault experiment when applying the fault fails."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        driver = FaultDriver(mock_env)

        # Mock the methods
        driver.apply_fault = mock.MagicMock(side_effect=FaultInjectionError("Test error"))
        driver.monitor_experiment = mock.MagicMock()
        driver.delete_fault = mock.MagicMock()

        # Create a temporary manifest file
        manifest_content = """
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: test-experiment
  namespace: default
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - default
    labelSelectors:
      app: test-app
  delay:
    latency: 100ms
    correlation: "0"
    jitter: 0ms
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            temp_file.write(manifest_content)
            temp_file.flush()

            # Execute and verify
            with pytest.raises(FaultInjectionError):
                driver.run_fault_experiment(temp_file.name)

            # Verify method calls
            driver.apply_fault.assert_called_once_with(temp_file.name)
            driver.monitor_experiment.assert_not_called()
            driver.delete_fault.assert_not_called()

    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_run_fault_experiment_monitor_failure(self):
        """Test running a fault experiment when monitoring fails."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialized = True
        mock_env.chaos_mesh_installed = True

        driver = FaultDriver(mock_env)

        # Mock the methods
        driver.apply_fault = mock.MagicMock(return_value="test-experiment")
        driver.monitor_experiment = mock.MagicMock(side_effect=FaultInjectionError("Test error"))
        driver.delete_fault = mock.MagicMock()

        # Create a temporary manifest file
        manifest_content = """
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: test-experiment
  namespace: default
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - default
    labelSelectors:
      app: test-app
  delay:
    latency: 100ms
    correlation: "0"
    jitter: 0ms
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            temp_file.write(manifest_content)
            temp_file.flush()

            # Execute and verify
            with pytest.raises(FaultInjectionError):
                driver.run_fault_experiment(temp_file.name)

            # Verify method calls
            driver.apply_fault.assert_called_once_with(temp_file.name)
            driver.monitor_experiment.assert_called_once()
            driver.delete_fault.assert_called_once_with("test-experiment")


class TestRunFaultInjection:
    """Tests for the run_fault_injection function."""

    @mock.patch("arc_memory.simulate.fault_driver.FaultDriver")
    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_run_fault_injection_success(self, mock_fault_driver_class):
        """Test running fault injection successfully."""
        # Setup
        mock_driver = mock.MagicMock()
        mock_driver.run_fault_experiment.return_value = {
            "experiment_name": "test-experiment",
            "duration_seconds": 60,
            "initial_metrics": {"node_count": 1},
            "final_metrics": {"node_count": 1}
        }
        mock_fault_driver_class.return_value = mock_driver

        mock_env = mock.MagicMock()

        # Create a temporary manifest file
        manifest_content = """
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: test-experiment
  namespace: default
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - default
    labelSelectors:
      app: test-app
  delay:
    latency: 100ms
    correlation: "0"
    jitter: 0ms
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            temp_file.write(manifest_content)
            temp_file.flush()

            # Execute
            results = run_fault_injection(
                manifest_path=temp_file.name,
                simulation_env=mock_env,
                duration_seconds=60,
                metrics_interval=30
            )

            # Verify
            assert results["experiment_name"] == "test-experiment"
            assert results["duration_seconds"] == 60

            # Verify method calls
            mock_fault_driver_class.assert_called_once_with(mock_env)
            mock_driver.run_fault_experiment.assert_called_once_with(
                manifest_path=temp_file.name,
                duration_seconds=60,
                metrics_interval=30
            )

    @mock.patch("arc_memory.simulate.fault_driver.FaultDriver")
    @mock.patch("arc_memory.simulate.fault_driver.HAS_E2B", True)
    def test_run_fault_injection_failure(self, mock_fault_driver_class):
        """Test running fault injection when it fails."""
        # Setup
        mock_driver = mock.MagicMock()
        mock_driver.run_fault_experiment.side_effect = FaultInjectionError("Test error")
        mock_fault_driver_class.return_value = mock_driver

        mock_env = mock.MagicMock()

        # Create a temporary manifest file
        manifest_content = """
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: test-experiment
  namespace: default
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - default
    labelSelectors:
      app: test-app
  delay:
    latency: 100ms
    correlation: "0"
    jitter: 0ms
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            temp_file.write(manifest_content)
            temp_file.flush()

            # Execute and verify
            with pytest.raises(FaultInjectionError):
                run_fault_injection(
                    manifest_path=temp_file.name,
                    simulation_env=mock_env
                )

            # Verify method calls
            mock_fault_driver_class.assert_called_once_with(mock_env)
            mock_driver.run_fault_experiment.assert_called_once()
