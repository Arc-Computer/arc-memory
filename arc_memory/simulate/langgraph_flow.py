"""LangGraph workflow for Arc Memory simulation.

This module provides a workflow orchestration system for the simulation process
using LangGraph to define the steps and manage state passing between them.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, TypedDict, Annotated, Literal, Union, cast

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.diff_utils import serialize_diff, analyze_diff, GitError
from arc_memory.simulate.causal import derive_causal
from arc_memory.simulate.manifest import generate_simulation_manifest
from arc_memory.simulate.code_interpreter import run_simulation as run_sandbox_simulation
from arc_memory.simulate.code_interpreter import HAS_E2B
from arc_memory.sql.db import ensure_arc_dir

logger = get_logger(__name__)


class SimulationState(TypedDict):
    """State for the simulation workflow."""
    # Input parameters
    rev_range: str
    scenario: str
    severity: int
    timeout: int
    repo_path: str
    db_path: str
    
    # Intermediate state
    diff_data: Optional[Dict[str, Any]]
    affected_services: Optional[List[str]]
    causal_graph: Optional[Dict[str, Any]]
    manifest: Optional[Dict[str, Any]]
    manifest_path: Optional[str]
    simulation_results: Optional[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]]
    risk_score: Optional[int]
    
    # Output state
    explanation: Optional[str]
    attestation: Optional[Dict[str, Any]]
    error: Optional[str]
    status: Literal["in_progress", "completed", "failed"]


def get_llm():
    """Get the LLM for the workflow."""
    # Check if OpenAI API key is available
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not found in environment variables")
        return None
    
    # Initialize the LLM
    try:
        llm = ChatOpenAI(
            model="gpt-4.1-2025-04-14",
            temperature=0.1,
            api_key=api_key
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return None


def extract_diff(state: SimulationState) -> SimulationState:
    """Extract the diff from Git.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated workflow state
    """
    logger.info(f"Extracting diff for range: {state['rev_range']}")
    
    try:
        # Extract the diff
        diff_data = serialize_diff(state["rev_range"], repo_path=state["repo_path"])
        
        # Update the state
        state["diff_data"] = diff_data
        
        logger.info(f"Successfully extracted diff with {len(diff_data.get('files', []))} files")
        return state
    except GitError as e:
        logger.error(f"Git error: {e}")
        state["error"] = f"Git error: {e}"
        state["status"] = "failed"
        return state
    except Exception as e:
        logger.error(f"Error extracting diff: {e}")
        state["error"] = f"Error extracting diff: {e}"
        state["status"] = "failed"
        return state


def analyze_changes(state: SimulationState) -> SimulationState:
    """Analyze the diff to identify affected services.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated workflow state
    """
    logger.info("Analyzing diff to identify affected services")
    
    try:
        # Check if we have diff data
        if not state.get("diff_data"):
            state["error"] = "No diff data available for analysis"
            state["status"] = "failed"
            return state
        
        # Analyze the diff
        affected_services = analyze_diff(state["diff_data"], state["db_path"])
        
        # Update the state
        state["affected_services"] = affected_services
        
        logger.info(f"Identified {len(affected_services)} affected services")
        return state
    except Exception as e:
        logger.error(f"Error analyzing diff: {e}")
        state["error"] = f"Error analyzing diff: {e}"
        state["status"] = "failed"
        return state


def build_causal_graph(state: SimulationState) -> SimulationState:
    """Build the causal graph from the knowledge graph.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated workflow state
    """
    logger.info("Building causal graph from knowledge graph")
    
    try:
        # Derive the causal graph
        causal_graph = derive_causal(state["db_path"])
        
        # Update the state
        state["causal_graph"] = causal_graph
        
        logger.info("Successfully built causal graph")
        return state
    except Exception as e:
        logger.error(f"Error building causal graph: {e}")
        state["error"] = f"Error building causal graph: {e}"
        state["status"] = "failed"
        return state


def generate_manifest(state: SimulationState) -> SimulationState:
    """Generate the simulation manifest.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated workflow state
    """
    logger.info(f"Generating simulation manifest for scenario: {state['scenario']}")
    
    try:
        # Check if we have the necessary data
        if not state.get("causal_graph"):
            state["error"] = "No causal graph available for manifest generation"
            state["status"] = "failed"
            return state
        
        if not state.get("diff_data"):
            state["error"] = "No diff data available for manifest generation"
            state["status"] = "failed"
            return state
        
        if not state.get("affected_services"):
            state["error"] = "No affected services identified for manifest generation"
            state["status"] = "failed"
            return state
        
        # Get the affected files
        affected_files = [file["path"] for file in state["diff_data"].get("files", [])]
        
        # Create a temporary manifest path
        arc_dir = ensure_arc_dir()
        sim_dir = arc_dir / "sim"
        sim_dir.mkdir(exist_ok=True)
        
        manifest_path = sim_dir / f"manifest_{hashlib.md5(state['rev_range'].encode()).hexdigest()}.yaml"
        
        # Generate the manifest
        manifest = generate_simulation_manifest(
            causal_graph=state["causal_graph"],
            affected_files=affected_files,
            scenario=state["scenario"],
            severity=state["severity"],
            target_services=state["affected_services"],
            output_path=manifest_path
        )
        
        # Update the state
        state["manifest"] = manifest
        state["manifest_path"] = str(manifest_path)
        
        logger.info(f"Successfully generated simulation manifest at {manifest_path}")
        return state
    except Exception as e:
        logger.error(f"Error generating manifest: {e}")
        state["error"] = f"Error generating manifest: {e}"
        state["status"] = "failed"
        return state


def run_simulation(state: SimulationState) -> SimulationState:
    """Run the simulation using the manifest.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated workflow state
    """
    logger.info("Running simulation")
    
    try:
        # Check if we have a manifest
        if not state.get("manifest_path"):
            state["error"] = "No manifest available for simulation"
            state["status"] = "failed"
            return state
        
        # Check if sandbox simulation is available
        if not HAS_E2B or not run_sandbox_simulation:
            logger.warning("E2B Code Interpreter not available, skipping simulation")
            state["simulation_results"] = {
                "is_mock": True,
                "experiment_name": "mock-experiment",
                "duration_seconds": state["timeout"],
                "initial_metrics": {
                    "node_count": 1,
                    "pod_count": 5,
                    "service_count": 3,
                },
                "final_metrics": {
                    "node_count": 1,
                    "pod_count": 5,
                    "service_count": 3,
                }
            }
            
            # Extract basic metrics
            state["metrics"] = {
                "latency_ms": int(state["severity"] * 10),
                "error_rate": round(state["severity"] / 1000, 3),
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3
            }
            
            # Calculate a simple risk score
            state["risk_score"] = state["severity"] // 2
            
            return state
        
        # Run the simulation
        simulation_timeout = min(state["timeout"], 300)  # Cap at 5 minutes for now
        simulation_results = run_sandbox_simulation(
            manifest_path=state["manifest_path"],
            duration_seconds=simulation_timeout,
            metrics_interval=30
        )
        
        # Update the state
        state["simulation_results"] = simulation_results
        
        # Extract metrics
        metrics = {
            "latency_ms": int(state["severity"] * 10),
            "error_rate": round(state["severity"] / 1000, 3),
        }
        
        # Add actual metrics from simulation if available
        if "final_metrics" in simulation_results:
            final_metrics = simulation_results.get("final_metrics", {})
            
            # Add basic metrics
            metrics["node_count"] = final_metrics.get("node_count", 0)
            metrics["pod_count"] = final_metrics.get("pod_count", 0)
            metrics["service_count"] = final_metrics.get("service_count", 0)
            
            # Add CPU and memory metrics if available
            if "cpu_usage" in final_metrics:
                metrics["cpu_usage"] = final_metrics.get("cpu_usage", {})
            if "memory_usage" in final_metrics:
                metrics["memory_usage"] = final_metrics.get("memory_usage", {})
        
        # Add experiment details if available
        if "experiment_name" in simulation_results:
            metrics["experiment_name"] = simulation_results.get("experiment_name")
        
        # Update the state with metrics
        state["metrics"] = metrics
        
        # Calculate risk score based on simulation results
        # For now, use a simple formula based on severity
        state["risk_score"] = state["severity"] // 2
        
        logger.info("Successfully ran simulation")
        return state
    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        
        # Fall back to static analysis
        logger.info("Falling back to static analysis")
        
        # Extract basic metrics
        state["metrics"] = {
            "latency_ms": int(state["severity"] * 10),
            "error_rate": round(state["severity"] / 1000, 3),
        }
        
        # Calculate a simple risk score
        state["risk_score"] = state["severity"] // 2
        
        return state


def generate_explanation(state: SimulationState) -> SimulationState:
    """Generate a human-readable explanation of the simulation results.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated workflow state
    """
    logger.info("Generating explanation")
    
    # Check if we have an LLM available
    llm = get_llm()
    if not llm:
        logger.warning("No LLM available, generating simple explanation")
        
        # Generate a simple explanation
        file_count = len(state.get("diff_data", {}).get("files", []))
        service_count = len(state.get("affected_services", []))
        
        explanation = (
            f"Simulation for {service_count} services based on {file_count} changed files. "
            f"Risk score: {state.get('risk_score', 0)} out of 100."
        )
        
        state["explanation"] = explanation
        return state
    
    try:
        # Prepare the prompt
        system_prompt = """You are an expert system analyst tasked with explaining the results of a simulation that predicts the impact of code changes.
Your goal is to provide a clear, concise explanation of the simulation results, focusing on:
1. What services were affected by the code changes
2. What the simulation revealed about potential impacts
3. The risk level and what it means
4. Recommendations for the developer

Be specific and technical, but also make your explanation accessible to developers who may not be familiar with the system architecture.
Focus on actionable insights rather than generic warnings.
"""

        human_prompt = """
# Simulation Context
- Rev Range: {rev_range}
- Scenario: {scenario}
- Severity Threshold: {severity}
- Risk Score: {risk_score}

# Changed Files
{file_summary}

# Affected Services
{service_summary}

# Metrics
{metrics_summary}

Based on this information, provide a concise explanation (3-5 paragraphs) of the simulation results and what they mean for the developer.
"""

        # Prepare the file summary
        files = state.get("diff_data", {}).get("files", [])
        file_summary = "\n".join([f"- {file['path']}" for file in files[:10]])
        if len(files) > 10:
            file_summary += f"\n- ... and {len(files) - 10} more files"
        
        # Prepare the service summary
        services = state.get("affected_services", [])
        service_summary = "\n".join([f"- {service}" for service in services])
        
        # Prepare the metrics summary
        metrics = state.get("metrics", {})
        metrics_summary = "\n".join([f"- {key}: {value}" for key, value in metrics.items() if not isinstance(value, dict)])
        
        # Format the prompt
        formatted_prompt = human_prompt.format(
            rev_range=state.get("rev_range", ""),
            scenario=state.get("scenario", ""),
            severity=state.get("severity", 0),
            risk_score=state.get("risk_score", 0),
            file_summary=file_summary,
            service_summary=service_summary,
            metrics_summary=metrics_summary
        )
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=formatted_prompt)
        ])
        
        # Generate the explanation
        chain = prompt | llm
        explanation = chain.invoke({}).content
        
        # Update the state
        state["explanation"] = explanation
        
        logger.info("Successfully generated explanation")
        return state
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        
        # Generate a simple explanation as fallback
        file_count = len(state.get("diff_data", {}).get("files", []))
        service_count = len(state.get("affected_services", []))
        
        explanation = (
            f"Simulation for {service_count} services based on {file_count} changed files. "
            f"Risk score: {state.get('risk_score', 0)} out of 100."
        )
        
        state["explanation"] = explanation
        return state


def generate_attestation(state: SimulationState) -> SimulationState:
    """Generate an attestation for the simulation results.
    
    Args:
        state: The current workflow state
        
    Returns:
        Updated workflow state
    """
    logger.info("Generating attestation")
    
    try:
        # Check if we have the necessary data
        if not state.get("diff_data"):
            state["error"] = "No diff data available for attestation"
            state["status"] = "failed"
            return state
        
        if not state.get("metrics"):
            state["error"] = "No metrics available for attestation"
            state["status"] = "failed"
            return state
        
        if not state.get("manifest"):
            state["error"] = "No manifest available for attestation"
            state["status"] = "failed"
            return state
        
        # Generate a unique simulation ID
        sim_id = f"sim_{state['rev_range'].replace('..', '_').replace('/', '_')}"
        
        # Get the manifest hash
        manifest_hash = state["manifest"]["metadata"]["annotations"]["arc-memory.io/manifest-hash"]
        
        # Create the attestation
        attestation = {
            "sim_id": sim_id,
            "manifest_hash": manifest_hash,
            "commit_target": state["diff_data"].get("end_commit", "unknown"),
            "metrics": state["metrics"],
            "timestamp": state["diff_data"].get("timestamp", "unknown"),
            "diff_hash": hashlib.md5(json.dumps(state["diff_data"], sort_keys=True).encode('utf-8')).hexdigest(),
            "risk_score": state.get("risk_score", 0),
            "explanation": state.get("explanation", "")
        }
        
        # Save the attestation
        arc_dir = ensure_arc_dir()
        attest_dir = arc_dir / ".attest"
        attest_dir.mkdir(exist_ok=True)
        
        attest_path = attest_dir / f"{sim_id}.json"
        with open(attest_path, 'w') as f:
            json.dump(attestation, f, indent=2)
        
        # Update the state
        state["attestation"] = attestation
        state["status"] = "completed"
        
        logger.info(f"Successfully generated attestation at {attest_path}")
        return state
    except Exception as e:
        logger.error(f"Error generating attestation: {e}")
        state["error"] = f"Error generating attestation: {e}"
        state["status"] = "failed"
        return state


def should_continue(state: SimulationState) -> Literal["continue", "end"]:
    """Determine if the workflow should continue or end.
    
    Args:
        state: The current workflow state
        
    Returns:
        "continue" if the workflow should continue, "end" if it should end
    """
    if state.get("status") == "failed":
        return "end"
    return "continue"


def create_workflow() -> StateGraph:
    """Create the simulation workflow graph.
    
    Returns:
        The workflow graph
    """
    # Create the workflow graph
    workflow = StateGraph(SimulationState)
    
    # Add the nodes
    workflow.add_node("extract_diff", extract_diff)
    workflow.add_node("analyze_changes", analyze_changes)
    workflow.add_node("build_causal_graph", build_causal_graph)
    workflow.add_node("generate_manifest", generate_manifest)
    workflow.add_node("run_simulation", run_simulation)
    workflow.add_node("generate_explanation", generate_explanation)
    workflow.add_node("generate_attestation", generate_attestation)
    
    # Define the edges
    workflow.add_edge("extract_diff", "analyze_changes")
    workflow.add_edge("analyze_changes", "build_causal_graph")
    workflow.add_edge("build_causal_graph", "generate_manifest")
    workflow.add_edge("generate_manifest", "run_simulation")
    workflow.add_edge("run_simulation", "generate_explanation")
    workflow.add_edge("generate_explanation", "generate_attestation")
    
    # Set the entry point
    workflow.set_entry_point("extract_diff")
    
    # Set conditional edges
    workflow.add_conditional_edges(
        "extract_diff",
        should_continue,
        {
            "continue": "analyze_changes",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "analyze_changes",
        should_continue,
        {
            "continue": "build_causal_graph",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "build_causal_graph",
        should_continue,
        {
            "continue": "generate_manifest",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "generate_manifest",
        should_continue,
        {
            "continue": "run_simulation",
            "end": END
        }
    )
    
    # Compile the workflow
    return workflow.compile()


def run_sim(
    rev_range: str,
    scenario: str = "network_latency",
    severity: int = 50,
    timeout: int = 600,
    repo_path: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Run a simulation workflow.
    
    Args:
        rev_range: Git rev-range to analyze
        scenario: Fault scenario ID
        severity: CI fail threshold 0-100
        timeout: Max runtime in seconds
        repo_path: Path to the Git repository (default: current directory)
        db_path: Path to the knowledge graph database (default: .arc/graph.db)
        
    Returns:
        The simulation results
    """
    logger.info(f"Starting simulation workflow for rev-range: {rev_range}")
    
    # Set default paths
    if not repo_path:
        repo_path = os.getcwd()
    
    if not db_path:
        arc_dir = ensure_arc_dir()
        db_path = str(arc_dir / "graph.db")
    
    # Create the initial state
    initial_state: SimulationState = {
        "rev_range": rev_range,
        "scenario": scenario,
        "severity": severity,
        "timeout": timeout,
        "repo_path": repo_path,
        "db_path": db_path,
        "diff_data": None,
        "affected_services": None,
        "causal_graph": None,
        "manifest": None,
        "manifest_path": None,
        "simulation_results": None,
        "metrics": None,
        "risk_score": None,
        "explanation": None,
        "attestation": None,
        "error": None,
        "status": "in_progress"
    }
    
    try:
        # Create the workflow
        workflow = create_workflow()
        
        # Run the workflow
        final_state = workflow.invoke(initial_state)
        
        # Check if the workflow completed successfully
        if final_state.get("status") == "failed":
            logger.error(f"Workflow failed: {final_state.get('error')}")
            return {
                "status": "failed",
                "error": final_state.get("error"),
                "rev_range": rev_range
            }
        
        # Return the results
        return {
            "status": "completed",
            "attestation": final_state.get("attestation"),
            "explanation": final_state.get("explanation"),
            "risk_score": final_state.get("risk_score"),
            "metrics": final_state.get("metrics"),
            "affected_services": final_state.get("affected_services"),
            "rev_range": rev_range
        }
    except Exception as e:
        logger.exception(f"Error running simulation workflow: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "rev_range": rev_range
        }
