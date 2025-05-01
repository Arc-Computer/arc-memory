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
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.diff_utils import serialize_diff, analyze_diff, GitError
from arc_memory.simulate.causal import derive_causal
from arc_memory.simulate.manifest import generate_simulation_manifest
from arc_memory.simulate.code_interpreter import run_simulation as run_sandbox_simulation
from arc_memory.simulate.code_interpreter import HAS_E2B
from arc_memory.simulate.explanation import (
    analyze_simulation_results,
    process_metrics,
    calculate_risk_score,
    generate_explanation
)
from arc_memory.attestation.write_attest import (
    generate_and_save_attestation
)
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
    processed_metrics: Optional[Dict[str, Any]]
    risk_factors: Optional[Dict[str, float]]
    risk_score: Optional[int]

    # Context retrieval state
    context_documents: Optional[List[Document]]

    # Output state
    explanation: Optional[str]
    attestation: Optional[Dict[str, Any]]
    error: Optional[str]
    status: Literal["in_progress", "completed", "failed"]


def process_and_calculate_risk(
    state: SimulationState,
    raw_metrics: Dict[str, Any]
) -> SimulationState:
    """Process metrics, calculate risk score, and update state.

    Args:
        state: The current workflow state
        raw_metrics: Raw metrics from simulation

    Returns:
        Updated workflow state
    """
    # Process metrics
    processed_metrics = process_metrics(raw_metrics)

    # Calculate risk score
    risk_score, risk_factors = calculate_risk_score(
        processed_metrics,
        state["severity"],
        state.get("affected_services", [])
    )

    # Update state
    state["metrics"] = raw_metrics
    state["processed_metrics"] = processed_metrics
    state["risk_factors"] = risk_factors
    state["risk_score"] = risk_score

    return state


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
    # Check if diff data is already provided
    if state.get("diff_data"):
        logger.info("Using pre-loaded diff data")
        logger.info(f"Pre-loaded diff contains {len(state['diff_data'].get('files', []))} files")
        return state

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
            raw_metrics = {
                "latency_ms": int(state["severity"] * 10),
                "error_rate": round(state["severity"] / 1000, 3),
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3
            }

            # Process metrics, calculate risk score, and update state
            state = process_and_calculate_risk(state, raw_metrics)

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

        # Update the state with raw metrics
        state["metrics"] = metrics

        # Process metrics, calculate risk score, and update state
        state = process_and_calculate_risk(state, metrics)

        logger.info("Successfully ran simulation")
        return state
    except Exception as e:
        logger.error(f"Error running simulation: {e}")

        # Fall back to static analysis
        logger.info("Falling back to static analysis")

        # Extract basic metrics
        raw_metrics = {
            "latency_ms": int(state["severity"] * 10),
            "error_rate": round(state["severity"] / 1000, 3),
        }

        # Process metrics, calculate risk score, and update state
        state = process_and_calculate_risk(state, raw_metrics)

        return state


def create_embeddings_from_diff(state: SimulationState) -> SimulationState:
    """Create embeddings from the diff data to enhance context retrieval.

    Args:
        state: The current workflow state

    Returns:
        Updated workflow state with embeddings
    """
    logger.info("Creating embeddings from diff data")

    try:
        # Check if we have diff data
        if not state.get("diff_data"):
            logger.warning("No diff data available for embedding creation")
            return state

        # Create documents from diff data
        documents = []

        # Add file content as documents
        for file in state.get("diff_data", {}).get("files", []):
            if "content" in file and file["content"]:
                documents.append(
                    Document(
                        page_content=file["content"],
                        metadata={
                            "path": file["path"],
                            "type": "file_content",
                            "change_type": file.get("change_type", "modified")
                        }
                    )
                )

            # Add diff hunks as separate documents for more granular context
            if "hunks" in file:
                for i, hunk in enumerate(file["hunks"]):
                    hunk_content = hunk.get("content", "")
                    if hunk_content:
                        documents.append(
                            Document(
                                page_content=hunk_content,
                                metadata={
                                    "path": file["path"],
                                    "type": "diff_hunk",
                                    "hunk_index": i,
                                    "change_type": file.get("change_type", "modified")
                                }
                            )
                        )

        # Add causal graph information if available
        if state.get("causal_graph"):
            causal_graph_str = json.dumps(state["causal_graph"], indent=2)
            documents.append(
                Document(
                    page_content=causal_graph_str,
                    metadata={
                        "type": "causal_graph"
                    }
                )
            )

        # Add simulation results if available
        if state.get("simulation_results"):
            sim_results_str = json.dumps(state["simulation_results"], indent=2)
            documents.append(
                Document(
                    page_content=sim_results_str,
                    metadata={
                        "type": "simulation_results"
                    }
                )
            )

        # Store the documents in the state
        state["context_documents"] = documents

        logger.info(f"Created {len(documents)} documents for context retrieval")
        return state
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
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
        logger.warning("No LLM available, generating explanation with our built-in generator")

        # Use our built-in explanation generator from the explanation module
        from arc_memory.simulate.explanation import generate_explanation as generate_explanation_from_module

        explanation = generate_explanation_from_module(
            scenario=state.get("scenario", "unknown"),
            severity=state.get("severity", 50),
            affected_services=state.get("affected_services", []),
            processed_metrics=state.get("processed_metrics", {}),
            risk_score=state.get("risk_score", 0),
            risk_factors=state.get("risk_factors", {}),
            simulation_results=state.get("simulation_results")
        )

        state["explanation"] = explanation
        return state

    try:
        # Create embeddings for context if not already done
        if not state.get("context_documents"):
            state = create_embeddings_from_diff(state)

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
- Risk Score: {risk_score}/100

# Changed Files
{file_summary}

# Affected Services
{service_summary}

# Metrics
{metrics_summary}

# Risk Factors
{risk_factors_summary}

# Relevant Code Context
{code_context}

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

        # Prepare risk factors summary
        risk_factors = state.get("risk_factors", {})
        risk_factors_summary = "\n".join([
            f"- {key.replace('normalized_', '').replace('_', ' ').title()}: {value * 100:.2f}%"
            for key, value in risk_factors.items()
        ])

        # Prepare code context from documents
        code_context = ""
        if state.get("context_documents"):
            # Use OpenAI embeddings for semantic search
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-large",
                dimensions=1024
            )

            # Create a query combining the scenario and affected services
            query = f"Impact of {state.get('scenario', '')} on {', '.join(state.get('affected_services', []))}"

            # Embed the query
            query_embedding = embeddings.embed_query(query)

            # Find the most relevant documents
            documents = state.get("context_documents", [])

            # Embed all documents
            doc_embeddings = embeddings.embed_documents([doc.page_content for doc in documents])

            # Calculate similarity scores
            from numpy import dot
            from numpy.linalg import norm

            def cosine_similarity(a, b):
                return dot(a, b) / (norm(a) * norm(b))

            # Calculate similarity for each document
            similarities = [cosine_similarity(query_embedding, doc_emb) for doc_emb in doc_embeddings]

            # Sort documents by similarity
            sorted_docs = [doc for _, doc in sorted(zip(similarities, documents), key=lambda x: x[0], reverse=True)]

            # Take the top 3 most relevant documents
            top_docs = sorted_docs[:3]

            # Format the code context
            for doc in top_docs:
                doc_type = doc.metadata.get("type", "unknown")
                if doc_type == "file_content":
                    code_context += f"\n## File: {doc.metadata.get('path', 'unknown')}\n"
                    # Limit content to first 20 lines to avoid overwhelming the context
                    content_lines = doc.page_content.split("\n")[:20]
                    code_context += "\n".join(content_lines)
                    if len(doc.page_content.split("\n")) > 20:
                        code_context += "\n... (truncated)"
                elif doc_type == "diff_hunk":
                    code_context += f"\n## Diff in {doc.metadata.get('path', 'unknown')}\n"
                    code_context += doc.page_content[:500]  # Limit to 500 chars
                    if len(doc.page_content) > 500:
                        code_context += "\n... (truncated)"
                else:
                    # For other types, just include a summary
                    code_context += f"\n## {doc_type.replace('_', ' ').title()}\n"
                    content_preview = doc.page_content[:300]
                    code_context += content_preview
                    if len(doc.page_content) > 300:
                        code_context += "\n... (truncated)"

        # Format the prompt
        formatted_prompt = human_prompt.format(
            rev_range=state.get("rev_range", ""),
            scenario=state.get("scenario", ""),
            severity=state.get("severity", 0),
            risk_score=state.get("risk_score", 0),
            file_summary=file_summary,
            service_summary=service_summary,
            metrics_summary=metrics_summary,
            risk_factors_summary=risk_factors_summary,
            code_context=code_context
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

        # Use our built-in explanation generator as fallback
        try:
            from arc_memory.simulate.explanation import generate_explanation as generate_explanation_from_module

            explanation = generate_explanation_from_module(
                scenario=state.get("scenario", "unknown"),
                severity=state.get("severity", 50),
                affected_services=state.get("affected_services", []),
                processed_metrics=state.get("processed_metrics", {}),
                risk_score=state.get("risk_score", 0),
                risk_factors=state.get("risk_factors", {}),
                simulation_results=state.get("simulation_results")
            )
        except Exception as inner_e:
            logger.error(f"Error generating fallback explanation: {inner_e}")
            # Generate a very simple explanation as last resort
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

        # Get the manifest hash
        manifest_hash = state["manifest"]["metadata"]["annotations"]["arc-memory.io/manifest-hash"]

        # Calculate diff hash
        diff_hash = hashlib.md5(json.dumps(state["diff_data"], sort_keys=True).encode('utf-8')).hexdigest()

        # Generate and save the attestation
        attestation = generate_and_save_attestation(
            rev_range=state["rev_range"],
            scenario=state["scenario"],
            severity=state["severity"],
            affected_services=state.get("affected_services", []),
            metrics=state["metrics"],
            risk_score=state.get("risk_score", 0),
            explanation=state.get("explanation", ""),
            manifest_hash=manifest_hash,
            commit_target=state["diff_data"].get("end_commit", "unknown"),
            timestamp=state["diff_data"].get("timestamp", "unknown"),
            diff_hash=diff_hash,
            simulation_results=state.get("simulation_results")
        )

        # Update the state
        state["attestation"] = attestation
        state["status"] = "completed"

        logger.info(f"Successfully generated attestation")
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
    workflow.add_node("create_embeddings", create_embeddings_from_diff)
    workflow.add_node("generate_explanation", generate_explanation)
    workflow.add_node("generate_attestation", generate_attestation)

    # Define the edges
    workflow.add_edge("extract_diff", "analyze_changes")
    workflow.add_edge("analyze_changes", "build_causal_graph")
    workflow.add_edge("build_causal_graph", "generate_manifest")
    workflow.add_edge("generate_manifest", "run_simulation")
    workflow.add_edge("run_simulation", "create_embeddings")
    workflow.add_edge("create_embeddings", "generate_explanation")
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

    workflow.add_conditional_edges(
        "run_simulation",
        should_continue,
        {
            "continue": "create_embeddings",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "create_embeddings",
        should_continue,
        {
            "continue": "generate_explanation",
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
    db_path: Optional[str] = None,
    diff_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Run a simulation workflow.

    Args:
        rev_range: Git rev-range to analyze
        scenario: Fault scenario ID
        severity: CI fail threshold 0-100
        timeout: Max runtime in seconds
        repo_path: Path to the Git repository (default: current directory)
        db_path: Path to the knowledge graph database (default: .arc/graph.db)
        diff_data: Pre-loaded diff data (optional)

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
        "diff_data": diff_data,  # Use pre-loaded diff data if provided
        "affected_services": None,
        "causal_graph": None,
        "manifest": None,
        "manifest_path": None,
        "simulation_results": None,
        "metrics": None,
        "processed_metrics": None,
        "risk_factors": None,
        "risk_score": None,
        "context_documents": None,
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
