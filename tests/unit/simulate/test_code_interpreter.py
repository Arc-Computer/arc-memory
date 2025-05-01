"""Tests for the E2B Code Interpreter wrapper."""

import os
import time
import tempfile
import yaml
from unittest import mock
from pathlib import Path

import pytest

from arc_memory.simulate.code_interpreter import (
    SimulationEnvironment,
    create_simulation_environment,
    run_simulation,
    CodeInterpreterError,
    HAS_E2B
)


class TestSimulationEnvironment:
    """Tests for the SimulationEnvironment class."""

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_init_success(self, mock_sandbox_class):
        """Test initializing the simulation environment successfully."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        # Mock environment variable
        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()

            # Verify
            mock_sandbox_class.assert_called_once_with(api_key="test-api-key")
            assert env.sandbox == mock_sandbox
            assert env.k3d_cluster_name.startswith("arc-sim-")
            assert not env.chaos_mesh_installed
            assert not env.initialized

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_init_with_api_key(self, mock_sandbox_class):
        """Test initializing the simulation environment with an API key."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        # Execute
        env = SimulationEnvironment(api_key="provided-api-key")

        # Verify
        mock_sandbox_class.assert_called_once_with(api_key="provided-api-key")
        assert env.sandbox == mock_sandbox

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_init_no_api_key(self, mock_sandbox_class):
        """Test initializing the simulation environment with no API key."""
        # Setup
        with mock.patch.dict(os.environ, {}, clear=True):
            # Execute and verify
            with pytest.raises(CodeInterpreterError):
                SimulationEnvironment()

        mock_sandbox_class.assert_not_called()

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_initialize_success(self, mock_sandbox_class):
        """Test initializing the environment with required dependencies."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()
            env.initialize()

            # Verify
            assert mock_sandbox.run_code.call_count > 0
            assert env.initialized

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_initialize_failure(self, mock_sandbox_class):
        """Test initializing the environment when it fails."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox.run_code.side_effect = Exception("Test error")
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()

            # Verify
            with pytest.raises(CodeInterpreterError):
                env.initialize()

            assert not env.initialized

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_setup_k3d_cluster_success(self, mock_sandbox_class):
        """Test setting up a k3d cluster successfully."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()
            env.initialized = True
            env.setup_k3d_cluster()

            # Verify
            assert mock_sandbox.run_code.call_count > 0

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_setup_k3d_cluster_not_initialized(self, mock_sandbox_class):
        """Test setting up a k3d cluster when not initialized."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()

            # Verify
            with pytest.raises(CodeInterpreterError):
                env.setup_k3d_cluster()

            assert not mock_sandbox.run_code.called

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_deploy_chaos_mesh_success(self, mock_sandbox_class):
        """Test deploying Chaos Mesh successfully."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_execution = mock.MagicMock()
        mock_execution.text = "Running"
        mock_sandbox.run_code.return_value = mock_execution
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()
            env.initialized = True
            env.deploy_chaos_mesh()

            # Verify
            assert mock_sandbox.run_code.call_count > 0
            assert env.chaos_mesh_installed

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_deploy_chaos_mesh_not_initialized(self, mock_sandbox_class):
        """Test deploying Chaos Mesh when not initialized."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()

            # Verify
            with pytest.raises(CodeInterpreterError):
                env.deploy_chaos_mesh()

            assert not mock_sandbox.run_code.called
            assert not env.chaos_mesh_installed

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_apply_chaos_experiment_success(self, mock_sandbox_class):
        """Test applying a Chaos Mesh experiment successfully."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

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

            with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
                # Execute
                env = SimulationEnvironment()
                env.initialized = True
                env.chaos_mesh_installed = True
                experiment_name = env.apply_chaos_experiment(temp_file.name)

                # Verify
                assert mock_sandbox.run_code.call_count > 0
                assert experiment_name == "test-experiment"

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_apply_chaos_experiment_not_initialized(self, mock_sandbox_class):
        """Test applying a Chaos Mesh experiment when not initialized."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()

            # Verify
            with pytest.raises(CodeInterpreterError):
                env.apply_chaos_experiment("test-manifest.yaml")

            assert not mock_sandbox.run_code.called

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_delete_chaos_experiment_success(self, mock_sandbox_class):
        """Test deleting a Chaos Mesh experiment successfully."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()
            env.initialized = True
            env.chaos_mesh_installed = True
            env.delete_chaos_experiment("test-experiment")

            # Verify
            assert mock_sandbox.run_code.call_count > 0

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_delete_chaos_experiment_not_initialized(self, mock_sandbox_class):
        """Test deleting a Chaos Mesh experiment when not initialized."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()

            # Verify
            with pytest.raises(CodeInterpreterError):
                env.delete_chaos_experiment("test-experiment")

            assert not mock_sandbox.run_code.called

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_collect_metrics_success(self, mock_sandbox_class):
        """Test collecting metrics successfully."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_execution1 = mock.MagicMock()
        mock_execution1.text = "2"
        mock_execution2 = mock.MagicMock()
        mock_execution2.text = "10"
        mock_execution3 = mock.MagicMock()
        mock_execution3.text = "5"
        mock_execution4 = mock.MagicMock()
        mock_execution4.text = "NAME CPU(cores) CPU% MEMORY(bytes) MEMORY%\nnode1 100m 5% 200Mi 10%"

        mock_sandbox.run_code.side_effect = [
            mock_execution1,  # node count
            mock_execution2,  # pod count
            mock_execution3,  # service count
            mock_execution4   # top nodes
        ]

        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()
            env.initialized = True
            metrics = env.collect_metrics()

            # Verify
            assert mock_sandbox.run_code.call_count == 4
            assert metrics["node_count"] == 2
            assert metrics["pod_count"] == 10
            assert metrics["service_count"] == 5
            assert "timestamp" in metrics

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_collect_metrics_not_initialized(self, mock_sandbox_class):
        """Test collecting metrics when not initialized."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()

            # Verify
            with pytest.raises(CodeInterpreterError):
                env.collect_metrics()

            assert not mock_sandbox.run_code.called

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_cleanup_success(self, mock_sandbox_class):
        """Test cleaning up resources successfully."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()
            env.initialized = True
            env.cleanup()

            # Verify
            assert mock_sandbox.run_code.call_count > 0
            assert mock_sandbox.close.call_count == 1

    @mock.patch("arc_memory.simulate.code_interpreter.Sandbox")
    def test_cleanup_not_initialized(self, mock_sandbox_class):
        """Test cleaning up resources when not initialized."""
        # Setup
        mock_sandbox = mock.MagicMock()
        mock_sandbox_class.return_value = mock_sandbox

        with mock.patch.dict(os.environ, {"E2B_API_KEY": "test-api-key"}):
            # Execute
            env = SimulationEnvironment()
            env.cleanup()

            # Verify
            assert not mock_sandbox.run_code.called
            assert mock_sandbox.close.call_count == 1


class TestSandboxFunctions:
    """Tests for the sandbox management functions."""

    @mock.patch("arc_memory.simulate.code_interpreter.HAS_E2B", True)
    @mock.patch("arc_memory.simulate.code_interpreter.SimulationEnvironment")
    def test_create_simulation_environment(self, mock_simulation_environment_class):
        """Test creating a simulation environment."""
        # Setup
        mock_env = mock.MagicMock()
        mock_simulation_environment_class.return_value = mock_env

        # Execute
        env = create_simulation_environment(api_key="test-api-key")

        # Verify
        mock_simulation_environment_class.assert_called_once_with(api_key="test-api-key")
        assert env == mock_env

    @mock.patch("arc_memory.simulate.code_interpreter.HAS_E2B", False)
    def test_create_simulation_environment_no_e2b(self):
        """Test creating a simulation environment when E2B is not available."""
        # Execute and verify
        with pytest.raises(CodeInterpreterError):
            create_simulation_environment(api_key="test-api-key")

    @mock.patch("arc_memory.simulate.code_interpreter.HAS_E2B", True)
    @mock.patch("arc_memory.simulate.code_interpreter.create_simulation_environment")
    def test_run_simulation_success(self, mock_create_simulation_environment):
        """Test running a simulation successfully."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.collect_metrics.return_value = {"timestamp": time.time()}
        mock_env.apply_chaos_experiment.return_value = "test-experiment"

        # Mock the sandbox execution for collect_logs
        mock_sandbox = mock.MagicMock()
        mock_execution = mock.MagicMock()
        # Return a valid JSON string for pods
        mock_execution.text = '{"items": [{"metadata": {"name": "test-pod"}}]}'
        mock_sandbox.run_code.return_value = mock_execution
        mock_env.sandbox = mock_sandbox

        mock_create_simulation_environment.return_value = mock_env

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
            results = run_simulation(temp_file.name, duration_seconds=1)

            # Verify
            mock_create_simulation_environment.assert_called_once()
            mock_env.initialize.assert_called_once()
            mock_env.setup_k3d_cluster.assert_called_once()
            mock_env.deploy_chaos_mesh.assert_called_once()
            mock_env.collect_metrics.assert_called()
            mock_env.apply_chaos_experiment.assert_called_once_with(temp_file.name)
            # Check that delete_chaos_experiment was called with the experiment name
            # (and any other parameters)
            assert mock_env.delete_chaos_experiment.call_count == 1
            assert mock_env.delete_chaos_experiment.call_args[0][0] == "test-experiment"
            mock_env.cleanup.assert_called_once()

            assert "experiment_name" in results
            assert "duration_seconds" in results
            assert "initial_metrics" in results
            assert "final_metrics" in results
            assert "timestamp" in results
            assert not results.get("is_mock", False)

    @mock.patch("arc_memory.simulate.code_interpreter.HAS_E2B", False)
    def test_run_simulation_no_e2b(self):
        """Test running a simulation when E2B is not available."""
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
            results = run_simulation(temp_file.name, duration_seconds=1)

            # Verify
            assert "experiment_name" in results
            assert "duration_seconds" in results
            assert "initial_metrics" in results
            assert "final_metrics" in results
            assert "timestamp" in results
            assert results.get("is_mock", False)

    @mock.patch("arc_memory.simulate.code_interpreter.HAS_E2B", True)
    @mock.patch("arc_memory.simulate.code_interpreter.create_simulation_environment")
    def test_run_simulation_failure(self, mock_create_simulation_environment):
        """Test running a simulation when it fails."""
        # Setup
        mock_env = mock.MagicMock()
        mock_env.initialize.side_effect = CodeInterpreterError("Test error")
        mock_create_simulation_environment.return_value = mock_env

        # Execute and verify
        with pytest.raises(CodeInterpreterError):
            run_simulation("test-manifest.yaml")

        mock_env.cleanup.assert_called_once()
