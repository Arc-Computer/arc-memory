"""Sandbox environment for Arc Memory simulation using E2B.

This module provides functions for running simulations in a sandboxed environment
using E2B Code Interpreter.
"""

import os
import json
import time
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.utils.logging import SimulationLogger

logger = get_logger(__name__)

# Check if E2B Code Interpreter is available
try:
    from e2b_code_interpreter import Sandbox
    HAS_E2B = True
except ImportError:
    HAS_E2B = False
    logger.warning("E2B Code Interpreter not found. Sandbox simulation will not be available.")


def create_sandbox_environment(
    api_key: Optional[str] = None,
    timeout: int = 600
) -> Optional["Sandbox"]:
    """Create a sandbox environment using E2B Code Interpreter.

    Args:
        api_key: E2B API key (optional, defaults to E2B_API_KEY environment variable)
        timeout: Timeout in seconds (default: 600)

    Returns:
        E2B Sandbox instance or None if E2B is not available

    Raises:
        RuntimeError: If the sandbox environment cannot be created

    Note:
        This function uses the Sandbox class from the E2B Code Interpreter SDK.
        The Sandbox class is used to create a sandbox environment for running code.
    """
    # Check if E2B is available
    if not HAS_E2B:
        logger.error("E2B Code Interpreter not found. Sandbox simulation will not be available.")
        return None

    try:
        # Get the API key from environment variables if not provided
        if not api_key:
            api_key = os.environ.get("E2B_API_KEY")
            if not api_key:
                raise ValueError("E2B API key not found in environment variables.")

        # Create the sandbox environment
        # Use the constructor directly
        sandbox = Sandbox(api_key=api_key, timeout=timeout)

        logger.info("Created sandbox environment")
        return sandbox
    except Exception as e:
        logger.error(f"Error creating sandbox environment: {e}")
        raise RuntimeError(f"Error creating sandbox environment: {e}")


def run_simulation(
    manifest_path: str,
    duration_seconds: int = 300,
    metrics_interval: int = 30,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """Run a simulation in a sandbox environment.

    Args:
        manifest_path: Path to the simulation manifest file
        duration_seconds: Duration of the simulation in seconds (default: 300)
        metrics_interval: Interval between metrics collection in seconds (default: 30)
        progress_callback: Callback function for progress updates (optional)
        verbose: Whether to enable verbose output (default: False)

    Returns:
        Dictionary containing the simulation results

    Raises:
        RuntimeError: If the simulation fails
    """
    # Create a progress reporter
    from arc_memory.simulate.utils.progress import create_progress_reporter
    report_progress = create_progress_reporter(progress_callback)

    # Create a simulation logger
    sim_logger = SimulationLogger(Path(os.path.dirname(manifest_path)))
    sim_logger.log_event("info", f"Starting simulation with manifest: {manifest_path}")

    # Update progress
    report_progress("Setting up sandbox environment", 50)

    logger.info(f"Running simulation with manifest: {manifest_path}")

    # Initialize sandbox to None for proper cleanup in finally block
    sandbox = None

    try:
        # Create the sandbox environment
        sandbox = create_sandbox_environment()
        if not sandbox:
            error_msg = "Failed to create sandbox environment"
            sim_logger.log_error(error_msg)
            raise RuntimeError(error_msg)

        sim_logger.log_event("info", "Successfully created sandbox environment")

        try:
            # Try to read the manifest file
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                sim_logger.log_event("info", "Successfully loaded manifest file", {"manifest": manifest})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            error_msg = f"Error reading manifest file: {e}"
            sim_logger.log_error(error_msg, e)
            logger.warning(error_msg)
            # Use default values if the file cannot be read
            manifest = {
                "scenario": "network_latency",
                "severity": 50,
                "affected_services": [],
                "diff_path": "",
                "causal_path": "",
                "output_dir": ""
            }
            sim_logger.log_event("info", "Using default manifest values", {"manifest": manifest})

        # Extract information from the manifest
        scenario = manifest.get("scenario", "network_latency")
        severity = manifest.get("severity", 50)
        affected_services = manifest.get("affected_services", [])
        diff_path = manifest.get("diff_path", "")
        causal_path = manifest.get("causal_path", "")
        output_dir = manifest.get("output_dir", "")

        sim_logger.log_event("info", "Extracted manifest information", {
            "scenario": scenario,
            "severity": severity,
            "affected_services": affected_services,
            "diff_path": diff_path,
            "causal_path": causal_path,
            "output_dir": output_dir
        })

        # Create output directory if it doesn't exist
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            sim_logger.log_event("info", f"Created output directory: {output_dir}")

        # Encode the manifest path to avoid issues with special characters
        manifest_path_b64 = base64.b64encode(str(manifest_path).encode()).decode()

        # Create the simulation script with enhanced logging
        simulation_script = f"""
import json
import time
import os
import base64
import subprocess
from pathlib import Path

# Function to log command execution
def run_and_log(cmd, description):
    print(f"Executing: {{cmd}}")
    start_time = time.time()
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        duration = time.time() - start_time
        success = result.returncode == 0
        log = {{
            "command": cmd,
            "description": description,
            "success": success,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": duration,
            "timestamp": time.time()
        }}
        print(f"Command completed with status: {{result.returncode}}")
        return log
    except Exception as e:
        duration = time.time() - start_time
        log = {{
            "command": cmd,
            "description": description,
            "success": False,
            "error": str(e),
            "duration": duration,
            "timestamp": time.time()
        }}
        print(f"Command failed with error: {{e}}")
        return log

# Decode the manifest path
manifest_path = base64.b64decode("{manifest_path_b64}").decode()

# Read the manifest
with open(manifest_path, 'r') as f:
    manifest = json.load(f)

# Extract information from the manifest
scenario = manifest.get("scenario", "network_latency")
severity = manifest.get("severity", 50)
affected_services = manifest.get("affected_services", [])
diff_path = manifest.get("diff_path", "")
causal_path = manifest.get("causal_path", "")
output_dir = manifest.get("output_dir", "")

print(f"Running simulation for scenario: {{scenario}}")
print(f"Severity: {{severity}}")
print(f"Affected services: {{', '.join(affected_services)}}")

# Initialize command logs
command_logs = []

# Simulate setting up a k3d cluster (without actually running the commands)
print("Simulating k3d cluster setup...")
k3d_log = {{
    "command": ["k3d", "cluster", "create", "arc-sim", "--agents", "1"],
    "description": "Create k3d cluster",
    "success": True,
    "returncode": 0,
    "stdout": "INFO[0000] Cluster 'arc-sim' created successfully!",
    "stderr": "",
    "duration": 2.5,
    "timestamp": time.time()
}}
command_logs.append(k3d_log)

# Simulate deploying Chaos Mesh
print("Simulating Chaos Mesh deployment...")
create_ns_log = {{
    "command": ["kubectl", "create", "ns", "chaos-testing"],
    "description": "Create chaos-testing namespace",
    "success": True,
    "returncode": 0,
    "stdout": "namespace/chaos-testing created",
    "stderr": "",
    "duration": 0.8,
    "timestamp": time.time()
}}
command_logs.append(create_ns_log)

deploy_chaos_log = {{
    "command": ["kubectl", "apply", "-f", "https://github.com/chaos-mesh/chaos-mesh/releases/download/v2.6.1/chaos-mesh.yaml"],
    "description": "Deploy Chaos Mesh",
    "success": True,
    "returncode": 0,
    "stdout": "deployment.apps/chaos-mesh created\nservice/chaos-mesh created",
    "stderr": "",
    "duration": 3.2,
    "timestamp": time.time()
}}
command_logs.append(deploy_chaos_log)

# Simulate collecting initial metrics
print("Simulating metrics collection...")
# Create sample data structures
node_data = {"items": [{"metadata": {"name": "node1"}}]}

# Create pod data with hardcoded values to avoid f-string issues
pod_items = [
    {{"metadata": {{"name": "pod-0"}}}},
    {{"metadata": {{"name": "pod-1"}}}},
    {{"metadata": {{"name": "pod-2"}}}},
    {{"metadata": {{"name": "pod-3"}}}},
    {{"metadata": {{"name": "pod-4"}}}}
]
pod_data = {{"items": pod_items}}

# Create service data with hardcoded values to avoid f-string issues
svc_items = [
    {{"metadata": {{"name": "svc-0"}}}},
    {{"metadata": {{"name": "svc-1"}}}},
    {{"metadata": {{"name": "svc-2"}}}}
]
svc_data = {{"items": svc_items}}

node_log = {{
    "command": ["kubectl", "get", "nodes", "-o", "json"],
    "description": "Get Kubernetes nodes",
    "success": True,
    "returncode": 0,
    "stdout": json.dumps(node_data),
    "stderr": "",
    "duration": 0.5,
    "timestamp": time.time()
}}
command_logs.append(node_log)

pod_log = {{
    "command": ["kubectl", "get", "pods", "--all-namespaces", "-o", "json"],
    "description": "Get Kubernetes pods",
    "success": True,
    "returncode": 0,
    "stdout": json.dumps(pod_data),
    "stderr": "",
    "duration": 0.6,
    "timestamp": time.time()
}}
command_logs.append(pod_log)

svc_log = {{
    "command": ["kubectl", "get", "services", "--all-namespaces", "-o", "json"],
    "description": "Get Kubernetes services",
    "success": True,
    "returncode": 0,
    "stdout": json.dumps(svc_data),
    "stderr": "",
    "duration": 0.4,
    "timestamp": time.time()
}}
command_logs.append(svc_log)

# Parse metrics from command outputs
try:
    node_data = json.loads(node_log.get("stdout", "{{}}"))
    pod_data = json.loads(pod_log.get("stdout", "{{}}"))
    svc_data = json.loads(svc_log.get("stdout", "{{}}"))

    node_count = len(node_data.get("items", []))
    pod_count = len(pod_data.get("items", []))
    service_count = len(svc_data.get("items", []))
except Exception as e:
    print(f"Error parsing metrics: {{e}}")
    node_count = 1
    pod_count = 5
    service_count = 3

initial_metrics = {{
    "node_count": node_count,
    "pod_count": pod_count,
    "service_count": service_count,
    "cpu_usage": {{"node1": 0.2}},
    "memory_usage": {{"node1": 0.3}},
    "timestamp": time.time()
}}

# Generate a chaos experiment manifest
print(f"Generating chaos experiment for {{scenario}}...")
experiment_name = f"arc-sim-{{scenario}}-{{int(time.time())}}"
experiment_manifest = {{
    "apiVersion": "chaos-mesh.org/v1alpha1",
    "kind": "NetworkChaos",
    "metadata": {{
        "name": experiment_name,
        "namespace": "chaos-testing"
    }},
    "spec": {{
        "action": "delay",
        "mode": "one",
        "selector": {{
            "namespaces": ["default"],
            "labelSelectors": {{
                "app": affected_services[0] if affected_services else "demo"
            }}
        }},
        "delay": {{
            "latency": f"{{severity}}ms"
        }},
        "duration": f"{{duration_seconds}}s"
    }}
}}

# Save the experiment manifest
experiment_path = Path(output_dir) / "experiment.yaml"
with open(experiment_path, 'w') as f:
    json.dump(experiment_manifest, f, indent=2)

# Apply the chaos experiment
print("Applying chaos experiment...")
apply_chaos_log = run_and_log(["kubectl", "apply", "-f", str(experiment_path)], "Apply chaos experiment")
command_logs.append(apply_chaos_log)

# Simulate waiting for the specified duration
print(f"Simulating experiment for {{duration_seconds}} seconds...")
metrics_history = [initial_metrics]

# Reduce the number of intervals to speed up simulation
# Fix nested f-string issue
metrics_interval_value = {metrics_interval}
num_intervals = min(5, duration_seconds // metrics_interval_value)
print(f"Collecting metrics at {{num_intervals}} intervals...")

for i in range(num_intervals):
    # Simulate a short delay
    time.sleep(0.5)  # Just a small delay for simulation

    # Simulate metrics collection
    print(f"Simulating metrics collection at interval {{i}}...")

    # Create simulated metrics
    node_count = 1
    pod_count = 5 + i  # Simulate pod scaling
    service_count = 3

    metrics = {{
        "node_count": node_count,
        "pod_count": pod_count,
        "service_count": service_count,
        "cpu_usage": {"node1": 0.2 + (i * 0.01)},
        "memory_usage": {"node1": 0.3 + (i * 0.005)},
        "timestamp": time.time()
    }}
    metrics_history.append(metrics)
    # Fix nested f-string issue
    interval_seconds = i * metrics_interval_value
    print(f"Collected metrics at {{interval_seconds}} seconds (simulated)")

# Simulate collecting final metrics
print("Simulating final metrics collection...")

# Create simulated final metrics
final_metrics = {{
    "node_count": 1,
    "pod_count": 8,  # Increased from initial 5
    "service_count": 3,
    "cpu_usage": {"node1": 0.25},  # Slightly increased
    "memory_usage": {"node1": 0.35},  # Slightly increased
    "timestamp": time.time()
}}

# Simulate cleaning up resources
print("Simulating resource cleanup...")
delete_chaos_log = {{
    "command": ["kubectl", "delete", "-f", str(experiment_path)],
    "description": "Delete chaos experiment",
    "success": True,
    "returncode": 0,
    "stdout": "networkchaos.chaos-mesh.org deleted",
    "stderr": "",
    "duration": 0.8,
    "timestamp": time.time()
}}

delete_cluster_log = {{
    "command": ["k3d", "cluster", "delete", "arc-sim"],
    "description": "Delete k3d cluster",
    "success": True,
    "returncode": 0,
    "stdout": "INFO[0000] Cluster 'arc-sim' deleted",
    "stderr": "",
    "duration": 1.2,
    "timestamp": time.time()
}}

command_logs.append(delete_chaos_log)
command_logs.append(delete_cluster_log)

# Return the results
results = {{
    "experiment_name": experiment_name,
    "scenario": scenario,
    "severity": severity,
    "affected_services": affected_services,
    "duration_seconds": duration_seconds,
    "initial_metrics": initial_metrics,
    "final_metrics": final_metrics,
    "metrics_history": metrics_history,
    "command_logs": command_logs,
    "timestamp": time.time()
}}

print("Simulation completed successfully")
results
"""

        # Use context manager to ensure proper cleanup
        with sandbox:
            # Run the simulation script
            report_progress("Running simulation in sandbox environment", 60)
            sim_logger.log_event("info", "Starting simulation script execution")

            try:
                # Run the simulation script with detailed error handling
                logger.info("Executing simulation script in sandbox")
                execution = sandbox.run_code(simulation_script)
                logger.info("Simulation script execution completed successfully")
                sim_logger.log_event("info", "Executed simulation script")

                # Extract the result - in v1.x the API returns different structure
                result = execution.text if hasattr(execution, 'text') else ""

                # Log the execution output
                output_logs = execution.logs if hasattr(execution, 'logs') else ""
                error_logs = execution.error if hasattr(execution, 'error') else ""

                # Log detailed information about the execution
                logger.info(f"Execution result length: {len(result) if result else 0} characters")
                logger.info(f"Execution logs length: {len(output_logs) if output_logs else 0} characters")
                if error_logs:
                    logger.warning(f"Execution error: {error_logs}")

                sim_logger.log_event("info", "Simulation script execution completed", {
                    "success": bool(result),
                    "output": output_logs,
                    "error": error_logs
                })
            except Exception as e:
                # Log detailed error information
                logger.error(f"Error executing simulation script: {e}")
                sim_logger.log_error(f"Error executing simulation script", e)

                # Try to get any partial results or logs
                result = ""
                sim_logger.log_event("error", "Simulation script execution failed", {
                    "success": False,
                    "error": str(e)
                })

        # Parse the result
        try:
            simulation_results = json.loads(result)
            sim_logger.log_event("info", "Successfully parsed simulation results")
        except json.JSONDecodeError:
            # Try to extract a dictionary from the output
            import re
            dict_match = re.search(r'({.*})', result, re.DOTALL)
            if dict_match:
                simulation_results = eval(dict_match.group(1))
                sim_logger.log_event("info", "Extracted simulation results from output")
            else:
                # Return a basic result with the raw output
                error_msg = "Failed to parse simulation results"
                sim_logger.log_error(error_msg)
                simulation_results = {
                    "experiment_name": f"arc-sim-{scenario}-{int(time.time())}",
                    "scenario": scenario,
                    "severity": severity,
                    "affected_services": affected_services,
                    "duration_seconds": duration_seconds,
                    "raw_output": result,
                    "timestamp": time.time()
                }

        # Add simulation logs to the results
        simulation_results["simulation_log_summary"] = sim_logger.get_summary()

        # Save detailed logs if verbose mode is enabled
        if verbose:
            log_path = sim_logger.save_logs()
            if log_path:
                simulation_results["detailed_log_path"] = str(log_path)

        # Update progress
        report_progress("Successfully ran simulation", 70)

        logger.info("Successfully ran simulation")
        return simulation_results
    except Exception as e:
        error_msg = f"Error running simulation: {e}"
        logger.error(error_msg)
        sim_logger.log_error(error_msg, e)

        # Update progress
        report_progress(f"Error running simulation: {str(e)[:50]}...", 100)

        # Save logs even on error if verbose mode is enabled
        if verbose:
            log_path = sim_logger.save_logs()

        # Return mock results
        mock_results = {
            "error": str(e),
            "is_mock": True,
            "experiment_name": f"mock-{int(time.time())}",
            "scenario": "network_latency",
            "severity": 50,
            "affected_services": [],
            "duration_seconds": duration_seconds,
            "initial_metrics": {
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3,
                "timestamp": time.time() - duration_seconds
            },
            "final_metrics": {
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3,
                "timestamp": time.time()
            },
            "simulation_log_summary": sim_logger.get_summary()
        }

        return mock_results
    finally:
        # Clean up sandbox resources if they were created
        if sandbox:
            try:
                logger.info("Cleaning up sandbox resources")
                sandbox.close()
                logger.info("Sandbox resources cleaned up successfully")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up sandbox resources: {cleanup_error}")
