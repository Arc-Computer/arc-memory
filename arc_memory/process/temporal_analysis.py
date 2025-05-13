"""Temporal analysis for Arc Memory.

This module provides functions for enhancing the knowledge graph with
temporal understanding and reasoning capabilities.
"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from arc_memory.llm.ollama_client import OllamaClient
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType
from arc_memory.utils.temporal import normalize_timestamp

# Import OpenAI client conditionally to avoid hard dependency
try:
    from arc_memory.llm.openai_client import OpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = get_logger(__name__)


def enhance_with_temporal_analysis(
    nodes: List[Node],
    edges: List[Edge],
    repo_path: Optional[Path] = None,
    enhancement_level: str = "standard",
    ollama_client: Optional[OllamaClient] = None,
    openai_client: Optional[Any] = None,
    llm_provider: str = "ollama",
) -> Tuple[List[Node], List[Edge]]:
    """Enhance nodes and edges with temporal analysis.

    Args:
        nodes: List of nodes to enhance.
        edges: List of edges to enhance.
        repo_path: Path to the repository (for accessing file content).
        enhancement_level: Level of enhancement to apply ("none", "fast", "standard", or "deep").
        ollama_client: Optional Ollama client for LLM processing.
        openai_client: Optional OpenAI client for LLM processing.
        llm_provider: The LLM provider to use ("ollama" or "openai").

    Returns:
        Enhanced nodes and edges.
    """
    logger.info(f"Enhancing knowledge graph with temporal analysis ({enhancement_level} level)")

    # Skip processing if enhancement level is none
    if enhancement_level == "none":
        logger.info("Skipping temporal analysis (enhancement level: none)")
        return nodes, edges

    # Extract commit nodes
    commit_nodes = [n for n in nodes if n.type == NodeType.COMMIT]
    if not commit_nodes:
        logger.warning("No commit nodes found for temporal analysis")
        return nodes, edges

    # Sort commits by timestamp using the normalized timestamp
    commit_nodes.sort(key=lambda n: normalize_timestamp(n) or datetime.min)
    logger.info(f"Found {len(commit_nodes)} commit nodes for temporal analysis")

    # Extract file nodes
    file_nodes = [n for n in nodes if n.type == NodeType.FILE]
    logger.info(f"Found {len(file_nodes)} file nodes for temporal analysis")

    # Create file change frequency map
    file_change_frequency = defaultdict(int)
    file_to_commits = defaultdict(list)
    commit_to_files = defaultdict(list)

    # Build file change frequency map
    for edge in edges:
        if edge.rel == EdgeRel.MODIFIES and edge.src.startswith("commit:"):
            file_id = edge.dst
            commit_id = edge.src
            file_change_frequency[file_id] += 1
            file_to_commits[file_id].append(commit_id)
            commit_to_files[commit_id].append(file_id)

    # Calculate co-change patterns (files that change together)
    co_change_map = defaultdict(int)
    for commit_id, files in commit_to_files.items():
        for i in range(len(files)):
            for j in range(i+1, len(files)):
                file_pair = tuple(sorted([files[i], files[j]]))
                co_change_map[file_pair] += 1

    # Create new edges for co-changing files (files that often change together)
    co_change_edges = []
    for (file1, file2), count in co_change_map.items():
        if count >= 3:  # Threshold for co-change relationship
            co_change_edges.append(Edge(
                src=file1,
                dst=file2,
                rel=EdgeRel.CORRELATES_WITH,
                properties={
                    "co_change_count": count,
                    "inferred": True,
                }
            ))

    logger.info(f"Created {len(co_change_edges)} co-change relationship edges")

    # Create temporal edges between commits that modified the same files
    temporal_edges = []
    for file_id, commit_ids in file_to_commits.items():
        if len(commit_ids) > 1:
            # Sort commits by timestamp using the normalized timestamp
            commit_ids.sort(key=lambda cid:
                next((normalize_timestamp(n) or datetime.min
                      for n in commit_nodes if n.id == cid), datetime.min))

            # Create PRECEDES edges between consecutive commits
            for i in range(len(commit_ids) - 1):
                temporal_edges.append(Edge(
                    src=commit_ids[i],
                    dst=commit_ids[i+1],
                    rel=EdgeRel.PRECEDES,
                    properties={
                        "context": f"Both modified {file_id}",
                        "inferred": True,
                    }
                ))

    logger.info(f"Created {len(temporal_edges)} temporal sequence edges")

    # Create refactoring detection if enhancement level is standard or deep
    refactoring_nodes = []
    refactoring_edges = []

    if enhancement_level in ["standard", "deep"] and len(commit_nodes) > 0:
        # Identify potential refactoring commits based on commit message patterns
        refactoring_keywords = ["refactor", "clean", "restructure", "renam", "reorganiz"]
        for commit in commit_nodes:
            commit_msg = ""
            if hasattr(commit, "properties"):
                commit_msg = commit.properties.get("message", "").lower()
            elif hasattr(commit, "body"):
                commit_msg = (commit.body or "").lower()

            is_refactoring = any(keyword in commit_msg for keyword in refactoring_keywords)

            if is_refactoring:
                # Create refactoring node
                refactoring_id = f"refactoring:{commit.id.split(':')[1]}"

                # Safely get commit properties
                commit_properties = getattr(commit, "properties", {})
                if not commit_properties and hasattr(commit, "author"):
                    # Handle the case where CommitNode doesn't have properties dict
                    # but has direct attributes instead
                    timestamp = getattr(commit, "ts", None)
                    if timestamp:
                        timestamp = timestamp.timestamp() if hasattr(timestamp, "timestamp") else 0
                    commit_properties = {
                        "timestamp": timestamp,
                        "message": getattr(commit, "body", ""),
                        "author": getattr(commit, "author", ""),
                    }

                refactoring_node = Node(
                    id=refactoring_id,
                    title=f"Refactoring: {getattr(commit, 'title', '')}",
                    type=NodeType.REFACTORING,
                    properties={
                        "timestamp": commit_properties.get("timestamp", 0),
                        "description": commit_properties.get("message", ""),
                        "author": commit_properties.get("author", ""),
                    }
                )
                refactoring_nodes.append(refactoring_node)

                # Create edge from commit to refactoring
                refactoring_edges.append(Edge(
                    src=commit.id,
                    dst=refactoring_id,
                    rel=EdgeRel.CREATES,
                    properties={"inferred": True}
                ))

                # Create edges from refactoring to affected files
                affected_files = [edge.dst for edge in edges if edge.src == commit.id and edge.rel == EdgeRel.MODIFIES]
                for file_id in affected_files:
                    refactoring_edges.append(Edge(
                        src=refactoring_id,
                        dst=file_id,
                        rel=EdgeRel.IMPROVES,
                        properties={"inferred": True}
                    ))

    logger.info(f"Created {len(refactoring_nodes)} refactoring nodes and {len(refactoring_edges)} refactoring edges")

    # Add developer workflow analysis if enhancement level is deep
    workflow_nodes = []
    workflow_edges = []

    if enhancement_level == "deep":
        # Group commits by author
        author_to_commits = defaultdict(list)
        for commit in commit_nodes:
            author = ""
            if hasattr(commit, "properties"):
                author = commit.properties.get("author", "")
            elif hasattr(commit, "author"):
                author = commit.author

            if author:
                author_to_commits[author].append(commit)

        # For each author, analyze their work patterns
        for author, commits in author_to_commits.items():
            # Sort commits by timestamp using the normalized timestamp
            commits.sort(key=lambda c: normalize_timestamp(c) or datetime.min)

            # Extract file touches by author
            author_files = set()
            for commit in commits:
                touched_files = [edge.dst for edge in edges if edge.src == commit.id and edge.rel == EdgeRel.MODIFIES]
                author_files.update(touched_files)

            # Create author expertise node
            expertise_id = f"expertise:{author.replace(' ', '_')}"
            expertise_node = Node(
                id=expertise_id,
                title=f"Expertise: {author}",
                type="expertise",
                properties={
                    "author": author,
                    "commit_count": len(commits),
                    "file_count": len(author_files),
                    "first_commit": commits[0].properties.get("timestamp", 0) if commits else 0,
                    "last_commit": commits[-1].properties.get("timestamp", 0) if commits else 0,
                }
            )
            workflow_nodes.append(expertise_node)

            # Create edges to most frequently touched files (expertise areas)
            author_file_touches = defaultdict(int)
            for commit in commits:
                for edge in edges:
                    if edge.src == commit.id and edge.rel == EdgeRel.MODIFIES:
                        author_file_touches[edge.dst] += 1

            # Connect expertise node to top files
            top_files = sorted(author_file_touches.items(), key=lambda x: x[1], reverse=True)[:10]
            for file_id, touch_count in top_files:
                workflow_edges.append(Edge(
                    src=expertise_id,
                    dst=file_id,
                    rel=EdgeRel.KNOWS,
                    properties={
                        "touch_count": touch_count,
                        "inferred": True,
                    }
                ))

        logger.info(f"Created {len(workflow_nodes)} workflow nodes and {len(workflow_edges)} expertise edges")

        # Add LLM-enhanced temporal analysis if available
        if llm_provider == "openai" and openai_client is not None:
            try:
                llm_nodes, llm_edges = enhance_with_llm_temporal_analysis_openai(
                    nodes, edges, commit_nodes, openai_client
                )
                workflow_nodes.extend(llm_nodes)
                workflow_edges.extend(llm_edges)
                logger.info(f"Added {len(llm_nodes)} LLM-enhanced nodes and {len(llm_edges)} LLM-enhanced edges")
            except Exception as e:
                logger.error(f"Error in OpenAI temporal analysis: {e}")
        elif ollama_client is not None:
            try:
                llm_nodes, llm_edges = enhance_with_llm_temporal_analysis(
                    nodes, edges, commit_nodes, ollama_client
                )
                workflow_nodes.extend(llm_nodes)
                workflow_edges.extend(llm_edges)
                logger.info(f"Added {len(llm_nodes)} LLM-enhanced nodes and {len(llm_edges)} LLM-enhanced edges")
            except Exception as e:
                logger.error(f"Error in Ollama temporal analysis: {e}")

    # Add change frequency property to file nodes
    enhanced_nodes = []
    for node in nodes:
        if node.id in file_change_frequency:
            # Create a copy of the node with enhanced properties
            if hasattr(node, 'properties'):
                node_props = dict(node.properties)
            elif hasattr(node, 'extra'):
                node_props = dict(node.extra)
            else:
                node_props = {}

            node_props["change_frequency"] = file_change_frequency[node.id]

            # If high change frequency, mark as hotspot
            if file_change_frequency[node.id] > 5:  # Threshold for hotspot
                node_props["is_hotspot"] = True

            enhanced_node = Node(
                id=node.id,
                title=node.title,
                type=node.type,
                properties=node_props
            )

            # Copy other attributes from the original node
            # Only transfer attributes that are fields on Node base class or specific subclasses
            if hasattr(node, 'body'):
                enhanced_node.body = node.body
            if hasattr(node, 'ts'):
                enhanced_node.ts = node.ts

            # Only try to set these attributes if the node type might have them
            if node.type == NodeType.FILE:
                if hasattr(node, 'path'):
                    # Handle directly as property since FileNode has path attribute
                    node_props['path'] = getattr(node, 'path')
                if hasattr(node, 'language'):
                    node_props['language'] = getattr(node, 'language')
                if hasattr(node, 'last_modified'):
                    node_props['last_modified'] = getattr(node, 'last_modified')

            enhanced_nodes.append(enhanced_node)
        else:
            enhanced_nodes.append(node)

    # Add new nodes and edges
    all_new_nodes = refactoring_nodes + workflow_nodes
    all_new_edges = co_change_edges + temporal_edges + refactoring_edges + workflow_edges

    logger.info(f"Temporal analysis complete: added {len(all_new_nodes)} nodes and {len(all_new_edges)} edges")
    return enhanced_nodes + all_new_nodes, edges + all_new_edges


def enhance_with_llm_temporal_analysis(
    nodes: List[Node],
    edges: List[Edge],
    commit_nodes: List[Node],
    ollama_client: OllamaClient
) -> Tuple[List[Node], List[Edge]]:
    """Use Ollama LLM to enhance temporal analysis with deeper insights.

    Args:
        nodes: List of all nodes.
        edges: List of all edges.
        commit_nodes: List of commit nodes.
        ollama_client: The Ollama client for LLM processing.

    Returns:
        New nodes and edges derived from LLM analysis.
    """
    # Import modules needed for this function
    import json
    import re

    # System prompt for temporal reasoning
    system_prompt = """
    You are a specialized Knowledge Graph enhancement system focused on temporal code analysis.

    The knowledge graph has the following schema:
    - Nodes have a dedicated timestamp column for efficient temporal queries
    - Each node has a type (COMMIT, FILE, PR, ISSUE, ADR, etc.)
    - Each node has a normalized timestamp (ts) field
    - Timestamps are stored in ISO format and indexed for efficient querying
    - Temporal relationships like PRECEDES are created between nodes based on their timestamps
    - The knowledge graph supports bi-temporal analysis (as-of and as-at time dimensions)

    Analyze the commit patterns to identify:
    1. Development phases and project milestones
    2. Code evolution patterns
    3. Potential technical debt accumulation areas

    When analyzing temporal data, consider:
    - The chronological order of events based on normalized timestamps
    - The relationships between events that occurred close in time
    - Patterns of changes over time that might indicate development phases
    - The evolution of code entities over time based on their modification history

    Format your response as JSON with the following structure:
    {
        "phases": [
            {"name": "phase name", "description": "phase description", "start_commit": "commit_id", "end_commit": "commit_id", "timestamp_range": ["start_iso_date", "end_iso_date"]}
        ],
        "evolution_patterns": [
            {"pattern": "pattern name", "description": "pattern description", "affected_files": ["file_id1", "file_id2"], "timestamp_range": ["start_iso_date", "end_iso_date"]}
        ],
        "technical_debt": [
            {"area": "area name", "description": "description", "affected_files": ["file_id1", "file_id2"], "first_observed": "iso_date"}
        ]
    }
    """

    # Prepare prompt for LLM
    if len(commit_nodes) < 5:
        logger.warning("Not enough commits for meaningful LLM temporal analysis")
        return [], []

    # Select a sample of commits (most recent 20)
    sample_commits = sorted(commit_nodes, key=lambda n: normalize_timestamp(n) or datetime.min, reverse=True)[:20]

    # Format commit data for LLM
    commit_data = []
    for commit in sample_commits:
        # Find files modified by this commit
        modified_files = [edge.dst for edge in edges if edge.src == commit.id and edge.rel == EdgeRel.MODIFIES]
        file_names = [node.title for node in nodes if node.id in modified_files]

        commit_data.append({
            "id": commit.id,
            "title": commit.title,
            "author": commit.properties.get("author", "unknown"),
            "timestamp": commit.properties.get("timestamp", 0),
            "message": commit.properties.get("message", ""),
            "files_modified": file_names
        })

    prompt = f"""
    Analyze the following commit history to identify development phases, code evolution patterns, and potential technical debt:

    {json.dumps(commit_data, indent=2)}

    Focus on temporal patterns and evolutionary aspects of the codebase.
    """

    try:
        # Query the LLM with thinking mode for better reasoning
        response = ollama_client.generate_with_thinking(
            model="qwen3:4b",
            prompt=prompt,
            system=system_prompt,
            options={"temperature": 0.1}
        )

        # Try to extract JSON from the response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                logger.warning("Could not extract JSON from LLM response")
                return [], []

        analysis = json.loads(json_str)

        # Create nodes and edges based on LLM analysis
        new_nodes = []
        new_edges = []

        # Create phase nodes
        for phase in analysis.get("phases", []):
            phase_id = f"phase:{slugify(phase['name'])}"
            phase_node = Node(
                id=phase_id,
                title=phase["name"],
                type="development_phase",
                properties={
                    "description": phase["description"],
                    "start_commit": phase.get("start_commit", ""),
                    "end_commit": phase.get("end_commit", ""),
                }
            )
            new_nodes.append(phase_node)

            # Connect phase to commits
            if phase.get("start_commit") and phase.get("end_commit"):
                new_edges.append(Edge(
                    src=phase_id,
                    dst=phase["start_commit"],
                    rel=EdgeRel.STARTS_WITH,
                    properties={"inferred": True}
                ))
                new_edges.append(Edge(
                    src=phase_id,
                    dst=phase["end_commit"],
                    rel=EdgeRel.ENDS_WITH,
                    properties={"inferred": True}
                ))

        # Create evolution pattern nodes
        for pattern in analysis.get("evolution_patterns", []):
            pattern_id = f"pattern:{slugify(pattern['pattern'])}"
            pattern_node = Node(
                id=pattern_id,
                title=pattern["pattern"],
                type="evolution_pattern",
                properties={
                    "description": pattern["description"]
                }
            )
            new_nodes.append(pattern_node)

            # Connect pattern to affected files
            for file_id in pattern.get("affected_files", []):
                new_edges.append(Edge(
                    src=pattern_id,
                    dst=file_id,
                    rel=EdgeRel.AFFECTS,
                    properties={"inferred": True}
                ))

        # Create technical debt nodes
        for debt in analysis.get("technical_debt", []):
            debt_id = f"tech_debt:{slugify(debt['area'])}"
            debt_node = Node(
                id=debt_id,
                title=f"Technical Debt: {debt['area']}",
                type="technical_debt",
                properties={
                    "description": debt["description"]
                }
            )
            new_nodes.append(debt_node)

            # Connect debt to affected files
            for file_id in debt.get("affected_files", []):
                new_edges.append(Edge(
                    src=debt_id,
                    dst=file_id,
                    rel=EdgeRel.AFFECTS,
                    properties={"inferred": True}
                ))

        return new_nodes, new_edges

    except Exception as e:
        logger.error(f"Error in LLM temporal analysis: {e}")
        return [], []


def enhance_with_llm_temporal_analysis_openai(
    nodes: List[Node],
    edges: List[Edge],
    commit_nodes: List[Node],
    openai_client: Any
) -> Tuple[List[Node], List[Edge]]:
    """Use OpenAI LLM to enhance temporal analysis with deeper insights.

    Args:
        nodes: List of all nodes.
        edges: List of all edges.
        commit_nodes: List of commit nodes.
        openai_client: The OpenAI client for LLM processing.

    Returns:
        New nodes and edges derived from LLM analysis.
    """
    # Import modules needed for this function
    import json
    import re

    # System prompt for temporal reasoning
    system_prompt = """
    You are a specialized Knowledge Graph enhancement system focused on temporal code analysis.

    The knowledge graph has the following schema:
    - Nodes have a dedicated timestamp column for efficient temporal queries
    - Each node has a type (COMMIT, FILE, PR, ISSUE, ADR, etc.)
    - Each node has a normalized timestamp (ts) field
    - Timestamps are stored in ISO format and indexed for efficient querying
    - Temporal relationships like PRECEDES are created between nodes based on their timestamps
    - The knowledge graph supports bi-temporal analysis (as-of and as-at time dimensions)

    Analyze the commit patterns to identify:
    1. Development phases and project milestones
    2. Code evolution patterns
    3. Potential technical debt accumulation areas

    When analyzing temporal data, consider:
    - The chronological order of events based on normalized timestamps
    - The relationships between events that occurred close in time
    - Patterns of changes over time that might indicate development phases
    - The evolution of code entities over time based on their modification history

    Format your response as JSON with the following structure:
    {
        "phases": [
            {"name": "phase name", "description": "phase description", "start_commit": "commit_id", "end_commit": "commit_id", "timestamp_range": ["start_iso_date", "end_iso_date"]}
        ],
        "evolution_patterns": [
            {"pattern": "pattern name", "description": "pattern description", "affected_files": ["file_id1", "file_id2"], "timestamp_range": ["start_iso_date", "end_iso_date"]}
        ],
        "technical_debt": [
            {"area": "area name", "description": "description", "affected_files": ["file_id1", "file_id2"], "first_observed": "iso_date"}
        ]
    }
    """

    # Prepare prompt for LLM
    if len(commit_nodes) < 5:
        logger.warning("Not enough commits for meaningful LLM temporal analysis")
        return [], []

    # Select a sample of commits (most recent 20)
    sample_commits = sorted(commit_nodes, key=lambda n: normalize_timestamp(n) or datetime.min, reverse=True)[:20]

    # Format commit data for LLM
    commit_data = []
    for commit in sample_commits:
        # Find files modified by this commit
        modified_files = [edge.dst for edge in edges if edge.src == commit.id and edge.rel == EdgeRel.MODIFIES]
        file_names = [node.title for node in nodes if node.id in modified_files]

        commit_data.append({
            "id": commit.id,
            "title": commit.title,
            "author": commit.properties.get("author", "unknown"),
            "timestamp": commit.properties.get("timestamp", 0),
            "message": commit.properties.get("message", ""),
            "files_modified": file_names
        })

    prompt = f"""
    Analyze the following commit history to identify development phases, code evolution patterns, and potential technical debt:

    {json.dumps(commit_data, indent=2)}

    Focus on temporal patterns and evolutionary aspects of the codebase.
    """

    try:
        # Query the OpenAI LLM with thinking mode for better reasoning
        response = openai_client.generate_with_thinking(
            model="gpt-4.1",
            prompt=prompt,
            system=system_prompt,
            options={"temperature": 0.1}
        )

        # Try to extract JSON from the response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                logger.warning("Could not extract JSON from LLM response")
                return [], []

        analysis = json.loads(json_str)

        # Create nodes and edges based on LLM analysis
        new_nodes = []
        new_edges = []

        # Create phase nodes
        for phase in analysis.get("phases", []):
            phase_id = f"phase:{slugify(phase['name'])}"
            phase_node = Node(
                id=phase_id,
                title=phase["name"],
                type="development_phase",
                properties={
                    "description": phase["description"],
                    "start_commit": phase.get("start_commit", ""),
                    "end_commit": phase.get("end_commit", ""),
                }
            )
            new_nodes.append(phase_node)

            # Connect phase to commits
            if phase.get("start_commit") and phase.get("end_commit"):
                new_edges.append(Edge(
                    src=phase_id,
                    dst=phase["start_commit"],
                    rel=EdgeRel.STARTS_WITH,
                    properties={"inferred": True}
                ))
                new_edges.append(Edge(
                    src=phase_id,
                    dst=phase["end_commit"],
                    rel=EdgeRel.ENDS_WITH,
                    properties={"inferred": True}
                ))

        # Create evolution pattern nodes
        for pattern in analysis.get("evolution_patterns", []):
            pattern_id = f"pattern:{slugify(pattern['pattern'])}"
            pattern_node = Node(
                id=pattern_id,
                title=pattern["pattern"],
                type="evolution_pattern",
                properties={
                    "description": pattern["description"]
                }
            )
            new_nodes.append(pattern_node)

            # Connect pattern to affected files
            for file_id in pattern.get("affected_files", []):
                new_edges.append(Edge(
                    src=pattern_id,
                    dst=file_id,
                    rel=EdgeRel.AFFECTS,
                    properties={"inferred": True}
                ))

        # Create technical debt nodes
        for debt in analysis.get("technical_debt", []):
            debt_id = f"tech_debt:{slugify(debt['area'])}"
            debt_node = Node(
                id=debt_id,
                title=f"Technical Debt: {debt['area']}",
                type="technical_debt",
                properties={
                    "description": debt["description"]
                }
            )
            new_nodes.append(debt_node)

            # Connect debt to affected files
            for file_id in debt.get("affected_files", []):
                new_edges.append(Edge(
                    src=debt_id,
                    dst=file_id,
                    rel=EdgeRel.AFFECTS,
                    properties={"inferred": True}
                ))

        logger.info(f"OpenAI temporal analysis created {len(new_nodes)} nodes and {len(new_edges)} edges")
        return new_nodes, new_edges

    except Exception as e:
        logger.error(f"Error in OpenAI temporal analysis: {e}")
        return [], []


def slugify(text: str) -> str:
    """Convert text to slug format (lowercase, no spaces, alphanumeric only).

    Args:
        text: Text to convert to slug.

    Returns:
        Slugified text.
    """
    import re
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces with underscores
    slug = re.sub(r'\s+', '_', slug)
    # Remove non-alphanumeric characters
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    # Ensure slug is not empty
    if not slug:
        slug = "unknown"
    return slug
