"""E2B Code Interpreter wrapper for Arc Memory simulation.

This module provides a wrapper for the E2B Code Interpreter to run simulations
in isolated sandbox environments.
"""

import os
import time
import yaml
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Try to import e2b_code_interpreter, but don't fail if it's not available
# Note: The package name is 'e2b-code-interpreter' in pyproject.toml, but Python
# imports use underscores instead of hyphens, so we import 'e2b_code_interpreter'
try:
    from e2b_code_interpreter import Sandbox
    HAS_E2B = True
except ImportError:
    logger.warning("e2b_code_interpreter not found. Sandbox simulation will not be available.")
    logger.info("To enable sandbox simulation, install with: pip install e2b-code-interpreter")
    HAS_E2B = False
    Sandbox = None  # Define Sandbox as None for type checking


class CodeInterpreterError(Exception):
    """Exception raised for errors in the E2B Code Interpreter."""
    pass


class SimulationEnvironment:
    """A simulation environment for fault injection experiments using E2B Code Interpreter."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the simulation environment.

        Args:
            api_key: The E2B API key (optional, defaults to E2B_API_KEY environment variable)

        Raises:
            CodeInterpreterError: If environment initialization fails
        """
        if not HAS_E2B:
            raise CodeInterpreterError(
                "E2B Code Interpreter is not available. Please install it with 'pip install e2b-code-interpreter'."
            )

        try:
            # Get API key from environment variable if not provided
            if not api_key:
                api_key = os.environ.get("E2B_API_KEY")
                if not api_key:
                    raise CodeInterpreterError(
                        "E2B API key not found. Please set the E2B_API_KEY environment variable or provide it as an argument."
                    )

            # Create the sandbox
            self.sandbox = Sandbox(api_key=api_key)
            self.k3d_cluster_name = f"arc-sim-{int(time.time())}"
            self.chaos_mesh_installed = False
            self.initialized = False
            logger.info("Simulation environment created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize simulation environment: {e}")
            raise CodeInterpreterError(f"Failed to initialize simulation environment: {e}")

    def initialize(self) -> None:
        """Initialize the simulation environment with required dependencies.

        This installs Docker, k3d, kubectl, and other required tools.

        Raises:
            CodeInterpreterError: If initialization fails
        """
        try:
            logger.info("Initializing simulation environment")

            # Install required dependencies
            logger.info("Installing required dependencies")
            self.sandbox.run_code("""
!apt-get update
!apt-get install -y curl apt-transport-https ca-certificates gnupg lsb-release jq
            """)

            # Install Docker
            logger.info("Installing Docker")
            self.sandbox.run_code("""
# Add Docker's official GPG key
!curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
# Set up the stable repository
!echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
# Install Docker Engine
!apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io
            """)

            # Install k3d
            logger.info("Installing k3d")
            self.sandbox.run_code("""
!curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
            """)

            # Install kubectl
            logger.info("Installing kubectl")
            self.sandbox.run_code("""
!curl -LO https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl
!chmod +x kubectl
!mv kubectl /usr/local/bin/
            """)

            # Verify installations
            logger.info("Verifying installations")
            tools = ["docker", "k3d", "kubectl"]
            for tool in tools:
                execution = self.sandbox.run_code(f"!{tool} --version")
                logger.info(f"{tool} version: {execution.text}")

            self.initialized = True
            logger.info("Simulation environment initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize simulation environment: {e}")
            raise CodeInterpreterError(f"Failed to initialize simulation environment: {e}")

    def setup_k3d_cluster(self) -> None:
        """Set up a k3d cluster in the sandbox environment.

        Raises:
            CodeInterpreterError: If cluster setup fails
        """
        if not self.initialized:
            raise CodeInterpreterError("Simulation environment not initialized. Call initialize() first.")

        try:
            logger.info(f"Setting up k3d cluster: {self.k3d_cluster_name}")

            # Create k3d cluster
            self.sandbox.run_code(f"""
!k3d cluster create {self.k3d_cluster_name} --agents 1 --wait
            """)

            # Verify cluster is running
            execution = self.sandbox.run_code("""
!kubectl get nodes
            """)

            logger.info(f"k3d cluster {self.k3d_cluster_name} set up successfully")
            logger.info(f"Cluster nodes:\n{execution.text}")
        except Exception as e:
            logger.error(f"Failed to set up k3d cluster: {e}")
            raise CodeInterpreterError(f"Failed to set up k3d cluster: {e}")

    def deploy_chaos_mesh(self) -> None:
        """Deploy Chaos Mesh in the k3d cluster.

        Raises:
            CodeInterpreterError: If Chaos Mesh deployment fails
        """
        if not self.initialized:
            raise CodeInterpreterError("Simulation environment not initialized. Call initialize() first.")

        try:
            logger.info("Deploying Chaos Mesh")

            # Install Helm
            logger.info("Installing Helm")
            self.sandbox.run_code("""
!curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
!chmod 700 get_helm.sh
!./get_helm.sh
            """)

            # Add Chaos Mesh Helm repository
            self.sandbox.run_code("""
!helm repo add chaos-mesh https://charts.chaos-mesh.org
            """)

            # Update Helm repositories
            self.sandbox.run_code("""
!helm repo update
            """)

            # Create namespace for Chaos Mesh
            self.sandbox.run_code("""
!kubectl create ns chaos-testing
            """)

            # Install Chaos Mesh
            self.sandbox.run_code("""
!helm install chaos-mesh chaos-mesh/chaos-mesh --namespace=chaos-testing --set chaosDaemon.runtime=containerd --set chaosDaemon.socketPath=/run/containerd/containerd.sock
            """)

            # Wait for Chaos Mesh to be ready
            logger.info("Waiting for Chaos Mesh to be ready")
            for _ in range(30):  # Wait up to 5 minutes
                execution = self.sandbox.run_code("""
!kubectl get pods -n chaos-testing | grep chaos-controller-manager | grep Running
                """)
                if execution.text:
                    logger.info("Chaos Mesh is ready")
                    break
                time.sleep(10)
            else:
                raise CodeInterpreterError("Timed out waiting for Chaos Mesh to be ready")

            self.chaos_mesh_installed = True
            logger.info("Chaos Mesh deployed successfully")
        except Exception as e:
            logger.error(f"Failed to deploy Chaos Mesh: {e}")
            raise CodeInterpreterError(f"Failed to deploy Chaos Mesh: {e}")

    def apply_chaos_experiment(self, manifest_path: str) -> str:
        """Apply a Chaos Mesh experiment using the provided manifest.

        Args:
            manifest_path: Path to the Chaos Mesh manifest file

        Returns:
            The experiment name

        Raises:
            CodeInterpreterError: If experiment application fails
        """
        if not self.initialized or not self.chaos_mesh_installed:
            raise CodeInterpreterError("Chaos Mesh not installed. Call deploy_chaos_mesh() first.")

        try:
            logger.info(f"Applying Chaos Mesh experiment from {manifest_path}")

            # Create a temporary file for the remote manifest
            remote_path = f"/tmp/chaos-manifest-{int(time.time())}.yaml"

            # Upload the manifest to the sandbox
            with open(manifest_path, 'r') as f:
                manifest_content = f.read()

            # Base64 encode the manifest content to avoid string interpolation issues
            import base64
            encoded_content = base64.b64encode(manifest_content.encode()).decode()

            # Write the manifest to the sandbox using base64 encoding to avoid string interpolation issues
            self.sandbox.run_code(f"""
import base64
with open('{remote_path}', 'w') as f:
    decoded_content = base64.b64decode('{encoded_content}').decode()
    f.write(decoded_content)
            """)

            # Apply the manifest
            self.sandbox.run_code(f"""
!kubectl apply -f {remote_path}
            """)

            # Extract the experiment name from the manifest
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)

            experiment_name = manifest.get('metadata', {}).get('name', 'unknown-experiment')
            logger.info(f"Chaos Mesh experiment {experiment_name} applied successfully")

            return experiment_name
        except Exception as e:
            logger.error(f"Failed to apply Chaos Mesh experiment: {e}")
            raise CodeInterpreterError(f"Failed to apply Chaos Mesh experiment: {e}")

    def delete_chaos_experiment(self, experiment_name: str, kind: str = "NetworkChaos") -> None:
        """Delete a Chaos Mesh experiment.

        Args:
            experiment_name: The name of the experiment to delete
            kind: The kind of the experiment (default: "NetworkChaos")

        Raises:
            CodeInterpreterError: If experiment deletion fails
        """
        if not self.initialized or not self.chaos_mesh_installed:
            raise CodeInterpreterError("Chaos Mesh not installed. Call deploy_chaos_mesh() first.")

        try:
            logger.info(f"Deleting Chaos Mesh experiment: {experiment_name}")

            # Delete the experiment
            self.sandbox.run_code(f"""
!kubectl delete {kind} {experiment_name}
            """)

            logger.info(f"Chaos Mesh experiment {experiment_name} deleted successfully")
        except Exception as e:
            logger.error(f"Failed to delete Chaos Mesh experiment: {e}")
            raise CodeInterpreterError(f"Failed to delete Chaos Mesh experiment: {e}")

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from the k3d cluster.

        Returns:
            A dictionary of metrics

        Raises:
            CodeInterpreterError: If metrics collection fails
        """
        if not self.initialized:
            raise CodeInterpreterError("Simulation environment not initialized. Call initialize() first.")

        try:
            logger.info("Collecting metrics from k3d cluster")

            metrics = {
                "timestamp": time.time(),
                "node_count": 0,
                "pod_count": 0,
                "service_count": 0,
                "cpu_usage": {},
                "memory_usage": {}
            }

            # Get node count
            execution = self.sandbox.run_code("""
!kubectl get nodes -o json | jq '.items | length'
            """)
            if execution.text:
                metrics["node_count"] = int(execution.text.strip())

            # Get pod count
            execution = self.sandbox.run_code("""
!kubectl get pods --all-namespaces -o json | jq '.items | length'
            """)
            if execution.text:
                metrics["pod_count"] = int(execution.text.strip())

            # Get service count
            execution = self.sandbox.run_code("""
!kubectl get services --all-namespaces -o json | jq '.items | length'
            """)
            if execution.text:
                metrics["service_count"] = int(execution.text.strip())

            # Get CPU and memory usage for each node
            execution = self.sandbox.run_code("""
!kubectl top nodes
            """)
            if execution.text:
                lines = execution.text.strip().split("\n")[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        node_name = parts[0]
                        cpu = parts[2]
                        memory = parts[4]
                        metrics["cpu_usage"][node_name] = cpu
                        metrics["memory_usage"][node_name] = memory

            logger.info(f"Metrics collected: {metrics}")
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            raise CodeInterpreterError(f"Failed to collect metrics: {e}")

    def cleanup(self) -> None:
        """Clean up resources after simulation.

        Raises:
            CodeInterpreterError: If cleanup fails
        """
        try:
            logger.info("Cleaning up simulation environment")

            if self.initialized:
                # Delete k3d cluster if it exists
                try:
                    self.sandbox.run_code(f"""
!k3d cluster delete {self.k3d_cluster_name}
                    """)
                except Exception as e:
                    logger.warning(f"Failed to delete k3d cluster: {e}")

            # Close the sandbox
            try:
                self.sandbox.close()
                logger.info("Sandbox closed successfully")
            except Exception as e:
                logger.warning(f"Failed to close sandbox: {e}")

            logger.info("Simulation environment cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to clean up simulation environment: {e}")
            raise CodeInterpreterError(f"Failed to clean up simulation environment: {e}")

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        self.cleanup()


def create_simulation_environment(api_key: Optional[str] = None) -> SimulationEnvironment:
    """Create a new simulation environment.

    Args:
        api_key: The E2B API key (optional, defaults to E2B_API_KEY environment variable)

    Returns:
        A SimulationEnvironment instance

    Raises:
        CodeInterpreterError: If environment creation fails or E2B is not available
    """
    if not HAS_E2B:
        raise CodeInterpreterError(
            "E2B Code Interpreter is not available. Please install it with 'pip install e2b-code-interpreter'."
        )
    return SimulationEnvironment(api_key=api_key)


def run_simulation(manifest_path: str, duration_seconds: int = 300, metrics_interval: int = 30) -> Dict[str, Any]:
    """Run a simulation using the provided manifest.

    Args:
        manifest_path: Path to the Chaos Mesh manifest file
        duration_seconds: Duration of the simulation in seconds (default: 300)
        metrics_interval: Interval between metrics collection in seconds (default: 30)

    Returns:
        A dictionary of simulation results

    Raises:
        CodeInterpreterError: If simulation fails
    """
    # Check if E2B is available
    if not HAS_E2B:
        logger.warning("E2B Code Interpreter is not available. Returning mock simulation results.")
        # Return mock simulation results
        return {
            "experiment_name": "mock-experiment",
            "duration_seconds": duration_seconds,
            "initial_metrics": {
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3,
                "timestamp": time.time()
            },
            "final_metrics": {
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3,
                "timestamp": time.time() + duration_seconds
            },
            "timestamp": time.time(),
            "is_mock": True
        }

    env = None
    try:
        logger.info(f"Running simulation with manifest: {manifest_path}")

        # Create simulation environment
        env = create_simulation_environment()

        # Initialize environment
        env.initialize()

        # Set up k3d cluster
        env.setup_k3d_cluster()

        # Deploy Chaos Mesh
        env.deploy_chaos_mesh()

        # Import the fault driver here to avoid circular imports
        from arc_memory.simulate.fault_driver import run_fault_injection

        # Run the fault injection experiment
        results = run_fault_injection(
            manifest_path=manifest_path,
            simulation_env=env,
            duration_seconds=duration_seconds,
            metrics_interval=metrics_interval
        )

        # Add timestamp and mock flag
        results["timestamp"] = time.time()
        results["is_mock"] = False

        logger.info(f"Simulation completed successfully")
        return results
    except Exception as e:
        logger.error(f"Failed to run simulation: {e}")
        raise CodeInterpreterError(f"Failed to run simulation: {e}")
    finally:
        # Clean up resources
        if env:
            try:
                env.cleanup()
            except Exception as e:
                logger.error(f"Failed to clean up resources: {e}")
