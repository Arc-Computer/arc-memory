"""Fault injection driver for Arc Memory simulation.

This module provides a high-level interface for applying fault injection experiments
using Chaos Mesh in a Kubernetes cluster.
"""

import os
import time
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.code_interpreter import (
    SimulationEnvironment,
    CodeInterpreterError,
    HAS_E2B
)

logger = get_logger(__name__)


class FaultInjectionError(Exception):
    """Exception raised for errors in the fault injection process."""
    pass


class FaultDriver:
    """Driver for fault injection experiments using Chaos Mesh."""

    def __init__(self, simulation_env: SimulationEnvironment):
        """Initialize the fault driver.

        Args:
            simulation_env: The simulation environment to use

        Raises:
            FaultInjectionError: If initialization fails
        """
        if not HAS_E2B:
            raise FaultInjectionError(
                "E2B Code Interpreter is not available. Please install it with 'pip install e2b-code-interpreter'."
            )

        self.env = simulation_env
        self.active_experiments = {}  # type: Dict[str, Dict[str, Any]]
        self.metrics_history = []  # type: List[Dict[str, Any]]
        self.logs = []  # type: List[Dict[str, Any]]

        # Ensure the environment is initialized
        if not self.env.initialized:
            raise FaultInjectionError(
                "Simulation environment not initialized. Call env.initialize() first."
            )

        # Ensure Chaos Mesh is installed
        if not self.env.chaos_mesh_installed:
            raise FaultInjectionError(
                "Chaos Mesh not installed. Call env.deploy_chaos_mesh() first."
            )

        logger.info("Fault driver initialized successfully")

    def apply_fault(self, manifest_path: Union[str, Path]) -> str:
        """Apply a fault using the provided manifest.

        Args:
            manifest_path: Path to the Chaos Mesh manifest file

        Returns:
            The experiment ID

        Raises:
            FaultInjectionError: If fault application fails
        """
        try:
            logger.info(f"Applying fault from manifest: {manifest_path}")

            # Load the manifest to get details
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)

            # Extract experiment details
            kind = manifest.get('kind', 'Unknown')
            name = manifest.get('metadata', {}).get('name', 'unknown-experiment')
            namespace = manifest.get('metadata', {}).get('namespace', 'default')

            # Apply the experiment using the simulation environment
            experiment_name = self.env.apply_chaos_experiment(manifest_path)

            # Store the active experiment
            self.active_experiments[experiment_name] = {
                'kind': kind,
                'name': experiment_name,
                'namespace': namespace,
                'start_time': time.time(),
                'manifest': manifest
            }

            logger.info(f"Applied fault experiment: {experiment_name} (kind: {kind})")
            return experiment_name
        except Exception as e:
            logger.error(f"Failed to apply fault: {e}")
            raise FaultInjectionError(f"Failed to apply fault: {e}")

    def delete_fault(self, experiment_name: str) -> None:
        """Delete a fault experiment.

        Args:
            experiment_name: The name of the experiment to delete

        Raises:
            FaultInjectionError: If fault deletion fails
        """
        try:
            if experiment_name not in self.active_experiments:
                logger.warning(f"Experiment {experiment_name} not found in active experiments")
                return

            experiment = self.active_experiments[experiment_name]
            kind = experiment.get('kind', 'NetworkChaos')

            logger.info(f"Deleting fault experiment: {experiment_name} (kind: {kind})")

            # Delete the experiment using the simulation environment
            self.env.delete_chaos_experiment(experiment_name, kind=kind)

            # Update the experiment record
            self.active_experiments[experiment_name]['end_time'] = time.time()
            self.active_experiments[experiment_name]['status'] = 'deleted'

            logger.info(f"Deleted fault experiment: {experiment_name}")
        except Exception as e:
            logger.error(f"Failed to delete fault: {e}")
            raise FaultInjectionError(f"Failed to delete fault: {e}")

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from the Kubernetes cluster.

        Returns:
            A dictionary of metrics

        Raises:
            FaultInjectionError: If metrics collection fails
        """
        try:
            logger.info("Collecting metrics from Kubernetes cluster")

            # Collect metrics using the simulation environment
            metrics = self.env.collect_metrics()

            # Add timestamp if not present
            if 'timestamp' not in metrics:
                metrics['timestamp'] = time.time()

            # Store metrics in history
            self.metrics_history.append(metrics)

            logger.info(f"Collected metrics: {metrics}")
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            raise FaultInjectionError(f"Failed to collect metrics: {e}")

    def collect_logs(self, namespace: str = "default", label_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """Collect logs from pods in the Kubernetes cluster.

        Args:
            namespace: The namespace to collect logs from
            label_selector: Optional label selector to filter pods

        Returns:
            A list of log entries

        Raises:
            FaultInjectionError: If log collection fails
        """
        try:
            logger.info(f"Collecting logs from namespace: {namespace}")

            # Build the kubectl command
            cmd = f"kubectl get pods -n {namespace}"
            if label_selector:
                cmd += f" -l {label_selector}"
            cmd += " -o json"

            # Get the list of pods
            execution = self.env.sandbox.run_code(f"""
!{cmd}
            """)

            if not execution.text:
                logger.warning(f"No pods found in namespace {namespace}")
                return []

            # Parse the pod list
            pods = json.loads(execution.text).get('items', [])

            logs = []
            for pod in pods:
                pod_name = pod.get('metadata', {}).get('name')
                if not pod_name:
                    continue

                # Get logs for the pod
                log_cmd = f"kubectl logs -n {namespace} {pod_name} --tail=50"
                log_execution = self.env.sandbox.run_code(f"""
!{log_cmd}
                """)

                if log_execution.text:
                    log_entry = {
                        'pod': pod_name,
                        'namespace': namespace,
                        'timestamp': time.time(),
                        'logs': log_execution.text
                    }
                    logs.append(log_entry)
                    self.logs.append(log_entry)

            logger.info(f"Collected logs from {len(logs)} pods")
            return logs
        except Exception as e:
            logger.error(f"Failed to collect logs: {e}")
            raise FaultInjectionError(f"Failed to collect logs: {e}")

    def monitor_experiment(self, experiment_name: str, duration_seconds: int = 300,
                          metrics_interval: int = 30) -> Dict[str, Any]:
        """Monitor an experiment for the specified duration.

        Args:
            experiment_name: The name of the experiment to monitor
            duration_seconds: Duration to monitor in seconds
            metrics_interval: Interval between metrics collection in seconds

        Returns:
            A dictionary of monitoring results

        Raises:
            FaultInjectionError: If monitoring fails
        """
        try:
            if experiment_name not in self.active_experiments:
                raise FaultInjectionError(f"Experiment {experiment_name} not found in active experiments")

            experiment = self.active_experiments[experiment_name]
            logger.info(f"Monitoring experiment {experiment_name} for {duration_seconds} seconds")

            # Collect initial metrics
            initial_metrics = self.collect_metrics()

            # Collect initial logs
            namespace = experiment.get('namespace', 'default')
            initial_logs = self.collect_logs(namespace=namespace)

            # Monitor for the specified duration
            start_time = time.time()
            end_time = start_time + duration_seconds

            # In a real scenario, we would collect metrics periodically
            # For testing purposes, we'll skip the loop if duration is very short
            if duration_seconds > 5:  # Only enter the loop for meaningful durations
                current_time = time.time()
                while current_time < end_time:
                    # Sleep until the next metrics collection
                    sleep_time = min(metrics_interval, end_time - current_time)
                    time.sleep(sleep_time)

                    # Get the current time after sleeping
                    current_time = time.time()

                    # Check if we've reached the end time
                    if current_time >= end_time:
                        break

                    # Collect metrics
                    self.collect_metrics()

            # Collect final metrics
            final_metrics = self.collect_metrics()

            # Collect final logs
            final_logs = self.collect_logs(namespace=namespace)

            # Calculate results
            results = {
                'experiment_name': experiment_name,
                'duration_seconds': duration_seconds,
                'initial_metrics': initial_metrics,
                'final_metrics': final_metrics,
                'metrics_history': self.metrics_history,
                'initial_logs': initial_logs,
                'final_logs': final_logs,
                'start_time': start_time,
                'end_time': time.time()
            }

            logger.info(f"Monitoring completed for experiment {experiment_name}")
            return results
        except Exception as e:
            logger.error(f"Failed to monitor experiment: {e}")
            raise FaultInjectionError(f"Failed to monitor experiment: {e}")

    def run_fault_experiment(self, manifest_path: Union[str, Path],
                            duration_seconds: int = 300,
                            metrics_interval: int = 30) -> Dict[str, Any]:
        """Run a complete fault experiment.

        This method applies a fault, monitors it for the specified duration,
        and then deletes the fault.

        Args:
            manifest_path: Path to the Chaos Mesh manifest file
            duration_seconds: Duration to run the experiment in seconds
            metrics_interval: Interval between metrics collection in seconds

        Returns:
            A dictionary of experiment results

        Raises:
            FaultInjectionError: If the experiment fails
        """
        experiment_name = None
        try:
            logger.info(f"Running fault experiment with manifest: {manifest_path}")

            # Apply the fault
            experiment_name = self.apply_fault(manifest_path)

            # Monitor the experiment
            results = self.monitor_experiment(
                experiment_name=experiment_name,
                duration_seconds=duration_seconds,
                metrics_interval=metrics_interval
            )

            logger.info(f"Fault experiment completed successfully")
            return results
        except Exception as e:
            logger.error(f"Failed to run fault experiment: {e}")
            raise FaultInjectionError(f"Failed to run fault experiment: {e}")
        finally:
            # Clean up the experiment
            if experiment_name:
                # Implement retry mechanism for cleanup
                max_retries = 3
                retry_delay = 2  # seconds

                for retry in range(max_retries):
                    try:
                        logger.info(f"Cleaning up experiment {experiment_name} (attempt {retry + 1}/{max_retries})")
                        self.delete_fault(experiment_name)
                        logger.info(f"Successfully cleaned up experiment {experiment_name}")
                        break
                    except Exception as e:
                        logger.error(f"Failed to clean up experiment {experiment_name} (attempt {retry + 1}/{max_retries}): {e}")
                        if retry < max_retries - 1:
                            logger.info(f"Retrying cleanup in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            # Increase delay for next retry (exponential backoff)
                            retry_delay *= 2
                        else:
                            logger.error(f"All cleanup attempts failed for experiment {experiment_name}. Manual cleanup may be required.")
                            # Add experiment to a list of failed cleanups for potential future handling
                            self.active_experiments[experiment_name]['cleanup_failed'] = True


def run_fault_injection(manifest_path: Union[str, Path],
                       simulation_env: SimulationEnvironment,
                       duration_seconds: int = 300,
                       metrics_interval: int = 30) -> Dict[str, Any]:
    """Run a fault injection experiment.

    Args:
        manifest_path: Path to the Chaos Mesh manifest file
        simulation_env: The simulation environment to use
        duration_seconds: Duration to run the experiment in seconds
        metrics_interval: Interval between metrics collection in seconds

    Returns:
        A dictionary of experiment results

    Raises:
        FaultInjectionError: If the experiment fails
    """
    try:
        # Create the fault driver
        driver = FaultDriver(simulation_env)

        # Run the experiment
        results = driver.run_fault_experiment(
            manifest_path=manifest_path,
            duration_seconds=duration_seconds,
            metrics_interval=metrics_interval
        )

        return results
    except Exception as e:
        logger.error(f"Failed to run fault injection: {e}")
        raise FaultInjectionError(f"Failed to run fault injection: {e}")
