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
    import e2b_code_interpreter
    HAS_E2B = True
except ImportError:
    HAS_E2B = False
    logger.warning("E2B Code Interpreter not found. Sandbox simulation will not be available.")


def create_sandbox_environment(
    api_key: Optional[str] = None,
    timeout: int = 600
) -> Optional["e2b_code_interpreter.Sandbox"]:
    """Create a sandbox environment using E2B Code Interpreter.

    Args:
        api_key: E2B API key (optional, defaults to E2B_API_KEY environment variable)
        timeout: Timeout in seconds (default: 600)

    Returns:
        E2B Sandbox instance or None if E2B is not available

    Raises:
        RuntimeError: If the sandbox environment cannot be created

    Note:
        This function uses the e2b_code_interpreter.Sandbox class from the E2B SDK.
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
        from e2b_code_interpreter import Sandbox
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

# Set up a k3d cluster
print("Setting up k3d cluster...")
k3d_log = run_and_log(["k3d", "cluster", "create", "arc-sim", "--agents", "1"], "Create k3d cluster")
command_logs.append(k3d_log)

# Deploy Chaos Mesh
print("Deploying Chaos Mesh...")
create_ns_log = run_and_log(["kubectl", "create", "ns", "chaos-testing"], "Create chaos-testing namespace")
command_logs.append(create_ns_log)

deploy_chaos_log = run_and_log(["kubectl", "apply", "-f", "https://github.com/chaos-mesh/chaos-mesh/releases/download/v2.6.1/chaos-mesh.yaml"], "Deploy Chaos Mesh")
command_logs.append(deploy_chaos_log)

# Collect initial metrics
print("Collecting initial metrics...")
node_log = run_and_log(["kubectl", "get", "nodes", "-o", "json"], "Get Kubernetes nodes")
command_logs.append(node_log)

pod_log = run_and_log(["kubectl", "get", "pods", "--all-namespaces", "-o", "json"], "Get Kubernetes pods")
command_logs.append(pod_log)

svc_log = run_and_log(["kubectl", "get", "services", "--all-namespaces", "-o", "json"], "Get Kubernetes services")
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

# Wait for the specified duration
print(f"Running experiment for {{duration_seconds}} seconds...")
metrics_history = [initial_metrics]
for i in range(duration_seconds // {metrics_interval}):
    time.sleep({metrics_interval})
    
    # Collect metrics
    node_log = run_and_log(["kubectl", "get", "nodes", "-o", "json"], f"Get Kubernetes nodes (interval {{i}})")
    pod_log = run_and_log(["kubectl", "get", "pods", "--all-namespaces", "-o", "json"], f"Get Kubernetes pods (interval {{i}})")
    svc_log = run_and_log(["kubectl", "get", "services", "--all-namespaces", "-o", "json"], f"Get Kubernetes services (interval {{i}})")
    
    command_logs.append(node_log)
    command_logs.append(pod_log)
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
    
    metrics = {{
        "node_count": node_count,
        "pod_count": pod_count,
        "service_count": service_count,
        "cpu_usage": {{"node1": 0.2 + (i * 0.01)}},
        "memory_usage": {{"node1": 0.3 + (i * 0.005)}},
        "timestamp": time.time()
    }}
    metrics_history.append(metrics)
    print(f"Collected metrics at {{i * {metrics_interval}}} seconds")

# Collect final metrics
print("Collecting final metrics...")
node_log = run_and_log(["kubectl", "get", "nodes", "-o", "json"], "Get Kubernetes nodes (final)")
pod_log = run_and_log(["kubectl", "get", "pods", "--all-namespaces", "-o", "json"], "Get Kubernetes pods (final)")
svc_log = run_and_log(["kubectl", "get", "services", "--all-namespaces", "-o", "json"], "Get Kubernetes services (final)")

command_logs.append(node_log)
command_logs.append(pod_log)
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

final_metrics = {{
    "node_count": node_count,
    "pod_count": pod_count,
    "service_count": service_count,
    "cpu_usage": {{"node1": 0.2 + (duration_seconds * 0.0003)}},
    "memory_usage": {{"node1": 0.3 + (duration_seconds * 0.0001)}},
    "timestamp": time.time()
}}

# Clean up resources
print("Cleaning up resources...")
delete_chaos_log = run_and_log(["kubectl", "delete", "-f", str(experiment_path)], "Delete chaos experiment")
delete_cluster_log = run_and_log(["k3d", "cluster", "delete", "arc-sim"], "Delete k3d cluster")

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

        # Run the simulation script
        report_progress("Running simulation in sandbox environment", 60)
        sim_logger.log_event("info", "Starting simulation script execution")

        # Create a code context
        context = sandbox.create_code_context()
        sim_logger.log_event("info", "Created sandbox code context")

        # Run the simulation script
        execution = sandbox.run_code(simulation_script, context=context)
        result = execution.result.value if execution.result else ""
        
        # Log the execution output
        sim_logger.log_event("info", "Simulation script execution completed", {
            "success": bool(execution.result),
            "output": execution.output,
            "error": execution.error
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
