"""Causal relationship extraction for Arc Memory.

This module provides functions for extracting causal relationships from various sources
such as commit messages, PR descriptions, Linear tickets, and ADRs.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from arc_memory.llm.ollama_client import OllamaClient
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    ADRNode,
    CommitNode,
    DecisionNode,
    Edge,
    EdgeRel,
    ImplicationNode,
    CodeChangeNode,
    IssueNode,
    Node,
    NodeType,
    PRNode,
)

logger = get_logger(__name__)


def extract_causal_relationships(
    nodes: List[Node],
    edges: List[Edge],
    repo_path: Optional[Path] = None,
    enhancement_level: str = "standard",
    ollama_client: Optional[OllamaClient] = None,
) -> Tuple[List[Node], List[Edge]]:
    """Extract causal relationships from nodes and edges.

    Args:
        nodes: List of nodes to analyze.
        edges: List of edges between nodes.
        repo_path: Optional path to the repository.
        enhancement_level: Level of enhancement to apply ("fast", "standard", or "deep").
        ollama_client: Optional Ollama client for LLM processing.

    Returns:
        New nodes and edges representing causal relationships.
    """
    logger.info(f"Extracting causal relationships ({enhancement_level} level)")

    # Initialize Ollama client if not provided
    if ollama_client is None:
        ollama_client = OllamaClient()

    # Extract causal relationships based on enhancement level
    if enhancement_level == "fast":
        # Fast extraction - rule-based only
        causal_nodes, causal_edges = extract_causal_relationships_rule_based(nodes, edges)
    elif enhancement_level == "standard":
        # Standard extraction - rule-based + LLM for ambiguous cases
        rule_nodes, rule_edges = extract_causal_relationships_rule_based(nodes, edges)
        llm_nodes, llm_edges = extract_causal_relationships_llm(
            nodes, edges, ollama_client, repo_path, selective=True
        )
        causal_nodes = rule_nodes + llm_nodes
        causal_edges = rule_edges + llm_edges
    elif enhancement_level == "deep":
        # Deep extraction - comprehensive LLM analysis
        rule_nodes, rule_edges = extract_causal_relationships_rule_based(nodes, edges)
        llm_nodes, llm_edges = extract_causal_relationships_llm(
            nodes, edges, ollama_client, repo_path, selective=False
        )
        causal_nodes = rule_nodes + llm_nodes
        causal_edges = rule_edges + llm_edges
    else:
        # No enhancement
        return [], []

    logger.info(f"Extracted {len(causal_nodes)} causal nodes and {len(causal_edges)} causal edges")
    return causal_nodes, causal_edges


def extract_causal_relationships_rule_based(
    nodes: List[Node], edges: List[Edge]
) -> Tuple[List[Node], List[Edge]]:
    """Extract causal relationships using rule-based methods.

    Args:
        nodes: List of nodes to analyze.
        edges: List of edges between nodes.

    Returns:
        New nodes and edges representing causal relationships.
    """
    logger.info("Extracting causal relationships using rule-based methods")

    causal_nodes = []
    causal_edges = []

    # Process different node types
    commit_nodes = [n for n in nodes if n.type == NodeType.COMMIT]
    pr_nodes = [n for n in nodes if n.type == NodeType.PR]
    issue_nodes = [n for n in nodes if n.type == NodeType.ISSUE]
    adr_nodes = [n for n in nodes if n.type == NodeType.ADR]

    # Extract from commits
    commit_results = extract_from_commits(commit_nodes, edges)
    causal_nodes.extend(commit_results[0])
    causal_edges.extend(commit_results[1])

    # Extract from PRs
    pr_results = extract_from_prs(pr_nodes, edges)
    causal_nodes.extend(pr_results[0])
    causal_edges.extend(pr_results[1])

    # Extract from issues (Linear tickets)
    issue_results = extract_from_issues(issue_nodes, edges)
    causal_nodes.extend(issue_results[0])
    causal_edges.extend(issue_results[1])

    # Extract from ADRs
    adr_results = extract_from_adrs(adr_nodes, edges)
    causal_nodes.extend(adr_results[0])
    causal_edges.extend(adr_results[1])

    # Connect related causal nodes
    connected_edges = connect_causal_nodes(causal_nodes, nodes, edges)
    causal_edges.extend(connected_edges)

    return causal_nodes, causal_edges


def extract_from_commits(
    commit_nodes: List[Node], edges: List[Edge]
) -> Tuple[List[Node], List[Edge]]:
    """Extract causal relationships from commit messages.

    Args:
        commit_nodes: List of commit nodes to analyze.
        edges: List of edges between nodes.

    Returns:
        New nodes and edges representing causal relationships.
    """
    logger.info(f"Extracting causal relationships from {len(commit_nodes)} commits")

    causal_nodes = []
    causal_edges = []

    # Decision keywords in commit messages
    decision_keywords = [
        r"decide[ds]?",
        r"choose|chose",
        r"select(ed)?",
        r"opt(ed)? for",
        r"implement(ed)?",
        r"adopt(ed)?",
        r"switch(ed)? to",
    ]

    # Implication keywords in commit messages
    implication_keywords = [
        r"because",
        r"due to",
        r"as a result",
        r"impact[s]?",
        r"affect[s]?",
        r"consequence[s]?",
        r"implication[s]?",
        r"lead[s]? to",
        r"result[s]? in",
    ]

    # Compile regex patterns
    decision_pattern = re.compile(r"(" + "|".join(decision_keywords) + r")", re.IGNORECASE)
    implication_pattern = re.compile(r"(" + "|".join(implication_keywords) + r")", re.IGNORECASE)

    for commit in commit_nodes:
        commit_message = commit.body or ""
        commit_title = commit.title or ""
        full_message = f"{commit_title}\n\n{commit_message}"

        # Check for decision patterns
        if decision_pattern.search(full_message):
            # Create a decision node
            decision_id = f"decision:{commit.id.split(':')[1]}"
            decision_node = DecisionNode(
                id=decision_id,
                type=NodeType.DECISION,
                title=f"Decision from commit: {commit_title}",
                body=commit_message,
                ts=commit.ts,
                decision_type="implementation",
                decision_makers=[commit.author] if hasattr(commit, "author") else [],
                confidence=0.8,  # Rule-based extraction has medium-high confidence
                source=commit.id,
            )
            causal_nodes.append(decision_node)

            # Create edge from commit to decision
            commit_decision_edge = Edge(
                src=commit.id,
                dst=decision_id,
                rel=EdgeRel.IMPLEMENTS_DECISION,
                properties={"confidence": 0.8, "extraction_method": "rule_based"},
            )
            causal_edges.append(commit_decision_edge)

            # Check for modified files to create code change nodes
            if hasattr(commit, "files") and commit.files:
                code_change_id = f"code_change:{commit.id.split(':')[1]}"
                code_change_node = CodeChangeNode(
                    id=code_change_id,
                    type=NodeType.CODE_CHANGE,
                    title=f"Code changes from commit: {commit_title}",
                    body=commit_message,
                    ts=commit.ts,
                    change_type="implementation",
                    files=commit.files,
                    description=commit_message,
                    author=commit.author if hasattr(commit, "author") else None,
                    commit_sha=commit.sha if hasattr(commit, "sha") else None,
                    confidence=0.9,  # High confidence for direct code changes
                )
                causal_nodes.append(code_change_node)

                # Create edge from decision to code change
                decision_code_edge = Edge(
                    src=decision_id,
                    dst=code_change_id,
                    rel=EdgeRel.RESULTS_IN,
                    properties={"confidence": 0.8, "extraction_method": "rule_based"},
                )
                causal_edges.append(decision_code_edge)

        # Check for implication patterns
        if implication_pattern.search(full_message):
            # Create an implication node
            implication_id = f"implication:{commit.id.split(':')[1]}"
            implication_node = ImplicationNode(
                id=implication_id,
                type=NodeType.IMPLICATION,
                title=f"Implication from commit: {commit_title}",
                body=commit_message,
                ts=commit.ts,
                implication_type="technical",
                severity="medium",
                scope=commit.files if hasattr(commit, "files") else [],
                confidence=0.7,  # Medium confidence for implications
                source=commit.id,
            )
            causal_nodes.append(implication_node)

            # Create edge from commit to implication
            commit_implication_edge = Edge(
                src=commit.id,
                dst=implication_id,
                rel=EdgeRel.CAUSED_BY,
                properties={"confidence": 0.7, "extraction_method": "rule_based"},
            )
            causal_edges.append(commit_implication_edge)

    return causal_nodes, causal_edges


def extract_from_prs(
    pr_nodes: List[Node], edges: List[Edge]
) -> Tuple[List[Node], List[Edge]]:
    """Extract causal relationships from PR descriptions.

    Args:
        pr_nodes: List of PR nodes to analyze.
        edges: List of edges between nodes.

    Returns:
        New nodes and edges representing causal relationships.
    """
    logger.info(f"Extracting causal relationships from {len(pr_nodes)} PRs")

    causal_nodes = []
    causal_edges = []

    # Decision sections in PR descriptions
    decision_sections = [
        r"## Decision",
        r"## Why",
        r"## Rationale",
        r"## Approach",
        r"## Solution",
    ]

    # Implication sections in PR descriptions
    implication_sections = [
        r"## Impact",
        r"## Implications",
        r"## Consequences",
        r"## Effects",
        r"## Changes",
    ]

    # Compile regex patterns
    decision_section_pattern = re.compile(r"(" + "|".join(decision_sections) + r")\s*\n(.*?)(?:\n##|\Z)", re.DOTALL | re.IGNORECASE)
    implication_section_pattern = re.compile(r"(" + "|".join(implication_sections) + r")\s*\n(.*?)(?:\n##|\Z)", re.DOTALL | re.IGNORECASE)

    for pr in pr_nodes:
        pr_description = pr.body or ""
        pr_title = pr.title or ""

        # Extract decision sections
        decision_matches = decision_section_pattern.findall(pr_description)
        for section_title, section_content in decision_matches:
            # Create a decision node
            decision_id = f"decision:pr_{pr.id.split(':')[1]}"
            decision_node = DecisionNode(
                id=decision_id,
                type=NodeType.DECISION,
                title=f"Decision from PR: {pr_title}",
                body=section_content.strip(),
                ts=pr.ts,
                decision_type="implementation",
                decision_makers=[pr.merged_by] if hasattr(pr, "merged_by") and pr.merged_by else [],
                confidence=0.85,  # High confidence for explicit sections
                source=pr.id,
            )
            causal_nodes.append(decision_node)

            # Create edge from PR to decision
            pr_decision_edge = Edge(
                src=pr.id,
                dst=decision_id,
                rel=EdgeRel.IMPLEMENTS_DECISION,
                properties={"confidence": 0.85, "extraction_method": "rule_based"},
            )
            causal_edges.append(pr_decision_edge)

        # Extract implication sections
        implication_matches = implication_section_pattern.findall(pr_description)
        for section_title, section_content in implication_matches:
            # Create an implication node
            implication_id = f"implication:pr_{pr.id.split(':')[1]}"
            implication_node = ImplicationNode(
                id=implication_id,
                type=NodeType.IMPLICATION,
                title=f"Implication from PR: {pr_title}",
                body=section_content.strip(),
                ts=pr.ts,
                implication_type="technical",
                severity="medium",
                confidence=0.8,  # High confidence for explicit sections
                source=pr.id,
            )
            causal_nodes.append(implication_node)

            # Create edge from PR to implication
            pr_implication_edge = Edge(
                src=pr.id,
                dst=implication_id,
                rel=EdgeRel.CAUSED_BY,
                properties={"confidence": 0.8, "extraction_method": "rule_based"},
            )
            causal_edges.append(pr_implication_edge)

            # If we also have a decision, connect them
            if decision_matches:
                decision_id = f"decision:pr_{pr.id.split(':')[1]}"
                decision_implication_edge = Edge(
                    src=decision_id,
                    dst=implication_id,
                    rel=EdgeRel.LEADS_TO,
                    properties={"confidence": 0.75, "extraction_method": "rule_based"},
                )
                causal_edges.append(decision_implication_edge)

    return causal_nodes, causal_edges


def extract_from_issues(
    issue_nodes: List[Node], edges: List[Edge]
) -> Tuple[List[Node], List[Edge]]:
    """Extract causal relationships from issues (Linear tickets).

    Args:
        issue_nodes: List of issue nodes to analyze.
        edges: List of edges between nodes.

    Returns:
        New nodes and edges representing causal relationships.
    """
    logger.info(f"Extracting causal relationships from {len(issue_nodes)} issues")

    causal_nodes = []
    causal_edges = []

    # Decision keywords in issue descriptions
    decision_keywords = [
        r"decide[ds]?",
        r"choose|chose",
        r"select(ed)?",
        r"opt(ed)? for",
        r"implement(ed)?",
        r"adopt(ed)?",
        r"switch(ed)? to",
    ]

    # Implication keywords in issue descriptions
    implication_keywords = [
        r"because",
        r"due to",
        r"as a result",
        r"impact[s]?",
        r"affect[s]?",
        r"consequence[s]?",
        r"implication[s]?",
        r"lead[s]? to",
        r"result[s]? in",
    ]

    # Compile regex patterns
    decision_pattern = re.compile(r"(" + "|".join(decision_keywords) + r")", re.IGNORECASE)
    implication_pattern = re.compile(r"(" + "|".join(implication_keywords) + r")", re.IGNORECASE)

    for issue in issue_nodes:
        issue_description = issue.body or ""
        issue_title = issue.title or ""
        full_description = f"{issue_title}\n\n{issue_description}"

        # Check for decision patterns
        if decision_pattern.search(full_description):
            # Create a decision node
            decision_id = f"decision:issue_{issue.id.split(':')[1]}"
            decision_node = DecisionNode(
                id=decision_id,
                type=NodeType.DECISION,
                title=f"Decision from issue: {issue_title}",
                body=issue_description,
                ts=issue.ts,
                decision_type="requirement",
                confidence=0.75,  # Medium-high confidence
                source=issue.id,
            )
            causal_nodes.append(decision_node)

            # Create edge from issue to decision
            issue_decision_edge = Edge(
                src=issue.id,
                dst=decision_id,
                rel=EdgeRel.ADDRESSES,
                properties={"confidence": 0.75, "extraction_method": "rule_based"},
            )
            causal_edges.append(issue_decision_edge)

        # Check for implication patterns
        if implication_pattern.search(full_description):
            # Create an implication node
            implication_id = f"implication:issue_{issue.id.split(':')[1]}"
            implication_node = ImplicationNode(
                id=implication_id,
                type=NodeType.IMPLICATION,
                title=f"Implication from issue: {issue_title}",
                body=issue_description,
                ts=issue.ts,
                implication_type="business",
                severity="medium",
                confidence=0.7,  # Medium confidence
                source=issue.id,
            )
            causal_nodes.append(implication_node)

            # Create edge from issue to implication
            issue_implication_edge = Edge(
                src=issue.id,
                dst=implication_id,
                rel=EdgeRel.LEADS_TO,
                properties={"confidence": 0.7, "extraction_method": "rule_based"},
            )
            causal_edges.append(issue_implication_edge)

    return causal_nodes, causal_edges


def extract_from_adrs(
    adr_nodes: List[Node], edges: List[Edge]
) -> Tuple[List[Node], List[Edge]]:
    """Extract causal relationships from ADRs.

    Args:
        adr_nodes: List of ADR nodes to analyze.
        edges: List of edges between nodes.

    Returns:
        New nodes and edges representing causal relationships.
    """
    logger.info(f"Extracting causal relationships from {len(adr_nodes)} ADRs")

    causal_nodes = []
    causal_edges = []

    # ADRs are explicit decision records, so we can create decision nodes directly
    for adr in adr_nodes:
        # Create a decision node
        decision_id = f"decision:adr_{adr.id.split(':')[1]}"
        decision_node = DecisionNode(
            id=decision_id,
            type=NodeType.DECISION,
            title=f"Decision from ADR: {adr.title}",
            body=adr.body or "",
            ts=adr.ts,
            decision_type="architectural",
            decision_makers=adr.decision_makers if hasattr(adr, "decision_makers") else [],
            confidence=0.95,  # Very high confidence for ADRs
            source=adr.id,
        )
        causal_nodes.append(decision_node)

        # Create edge from ADR to decision
        adr_decision_edge = Edge(
            src=adr.id,
            dst=decision_id,
            rel=EdgeRel.DECIDES,
            properties={"confidence": 0.95, "extraction_method": "rule_based"},
        )
        causal_edges.append(adr_decision_edge)

        # Look for implications in the ADR content
        adr_content = adr.body or ""

        # Common sections in ADRs that describe implications
        implication_sections = [
            r"## Consequences",
            r"## Implications",
            r"## Impact",
            r"## Results",
        ]

        # Try to extract implication sections
        for section_pattern in implication_sections:
            match = re.search(f"{section_pattern}\\s*\\n(.*?)(?:\\n##|\\Z)", adr_content, re.DOTALL | re.IGNORECASE)
            if match:
                section_content = match.group(1).strip()

                # Create an implication node
                implication_id = f"implication:adr_{adr.id.split(':')[1]}"
                implication_node = ImplicationNode(
                    id=implication_id,
                    type=NodeType.IMPLICATION,
                    title=f"Implication from ADR: {adr.title}",
                    body=section_content,
                    ts=adr.ts,
                    implication_type="architectural",
                    severity="high",  # ADR implications are typically significant
                    confidence=0.9,  # High confidence
                    source=adr.id,
                )
                causal_nodes.append(implication_node)

                # Create edge from decision to implication
                decision_implication_edge = Edge(
                    src=decision_id,
                    dst=implication_id,
                    rel=EdgeRel.LEADS_TO,
                    properties={"confidence": 0.9, "extraction_method": "rule_based"},
                )
                causal_edges.append(decision_implication_edge)

                # Only use the first matching section
                break

    return causal_nodes, causal_edges


def connect_causal_nodes(
    causal_nodes: List[Node], original_nodes: List[Node], original_edges: List[Edge]
) -> List[Edge]:
    """Connect related causal nodes based on existing relationships.

    Args:
        causal_nodes: List of causal nodes to connect.
        original_nodes: List of original nodes in the graph.
        original_edges: List of original edges in the graph.

    Returns:
        New edges connecting causal nodes.
    """
    logger.info("Connecting related causal nodes")

    new_edges = []

    # Create maps for quick lookup
    decision_nodes = {n.id: n for n in causal_nodes if n.type == NodeType.DECISION}
    implication_nodes = {n.id: n for n in causal_nodes if n.type == NodeType.IMPLICATION}
    code_change_nodes = {n.id: n for n in causal_nodes if n.type == NodeType.CODE_CHANGE}

    # Map source entities to their causal nodes
    source_to_decision = {}
    source_to_implication = {}
    source_to_code_change = {}

    for node_id, node in decision_nodes.items():
        if hasattr(node, "source") and node.source:
            source_to_decision[node.source] = node_id

    for node_id, node in implication_nodes.items():
        if hasattr(node, "source") and node.source:
            source_to_implication[node.source] = node_id

    for node_id, node in code_change_nodes.items():
        if hasattr(node, "source") and node.source:
            source_to_code_change[node.source] = node_id

    # Connect based on MENTIONS relationships in the original graph
    for edge in original_edges:
        if edge.rel == EdgeRel.MENTIONS:
            # If source mentions target and both have causal nodes, connect them
            if edge.src in source_to_decision and edge.dst in source_to_decision:
                new_edges.append(Edge(
                    src=source_to_decision[edge.src],
                    dst=source_to_decision[edge.dst],
                    rel=EdgeRel.INFLUENCES,
                    properties={"confidence": 0.7, "extraction_method": "rule_based"},
                ))

            if edge.src in source_to_decision and edge.dst in source_to_implication:
                new_edges.append(Edge(
                    src=source_to_decision[edge.src],
                    dst=source_to_implication[edge.dst],
                    rel=EdgeRel.LEADS_TO,
                    properties={"confidence": 0.7, "extraction_method": "rule_based"},
                ))

            if edge.src in source_to_implication and edge.dst in source_to_code_change:
                new_edges.append(Edge(
                    src=source_to_implication[edge.src],
                    dst=source_to_code_change[edge.dst],
                    rel=EdgeRel.RESULTS_IN,
                    properties={"confidence": 0.7, "extraction_method": "rule_based"},
                ))

    return new_edges


def extract_causal_relationships_llm(
    nodes: List[Node], edges: List[Edge], ollama_client: OllamaClient, repo_path: Optional[Path], selective: bool = True
) -> Tuple[List[Node], List[Edge]]:
    """Extract causal relationships using LLM-based analysis.

    Args:
        nodes: List of nodes to analyze.
        edges: List of edges between nodes.
        ollama_client: Ollama client for LLM processing.
        repo_path: Optional path to the repository.
        selective: Whether to be selective about which nodes to analyze.

    Returns:
        New nodes and edges representing causal relationships.
    """
    logger.info(f"Extracting causal relationships using LLM-based analysis (selective={selective})")

    causal_nodes = []
    causal_edges = []

    # If selective, only analyze nodes that are likely to contain causal relationships
    if selective:
        # Filter nodes to analyze
        nodes_to_analyze = []

        # Include ADRs, PRs with detailed descriptions, and commits with detailed messages
        for node in nodes:
            if node.type == NodeType.ADR:
                nodes_to_analyze.append(node)
            elif node.type == NodeType.PR and node.body and len(node.body) > 200:
                nodes_to_analyze.append(node)
            elif node.type == NodeType.COMMIT and node.body and len(node.body) > 200:
                nodes_to_analyze.append(node)
            elif node.type == NodeType.ISSUE and node.body and len(node.body) > 200:
                nodes_to_analyze.append(node)

        logger.info(f"Selected {len(nodes_to_analyze)} nodes for LLM analysis")
    else:
        # Analyze all nodes of relevant types
        nodes_to_analyze = [
            node for node in nodes
            if node.type in [NodeType.ADR, NodeType.PR, NodeType.COMMIT, NodeType.ISSUE]
        ]
        logger.info(f"Analyzing all {len(nodes_to_analyze)} relevant nodes with LLM")

    # Process nodes in batches to avoid overwhelming the LLM
    batch_size = 5
    for i in range(0, len(nodes_to_analyze), batch_size):
        batch = nodes_to_analyze[i:i + batch_size]

        # Process each node in the batch
        for node in batch:
            try:
                # Extract causal relationships from the node
                node_results = extract_causal_from_node_llm(node, ollama_client)
                causal_nodes.extend(node_results[0])
                causal_edges.extend(node_results[1])
            except Exception as e:
                logger.error(f"Error extracting causal relationships from {node.id}: {e}")

    return causal_nodes, causal_edges


def extract_causal_from_node_llm(
    node: Node, ollama_client: OllamaClient
) -> Tuple[List[Node], List[Edge]]:
    """Extract causal relationships from a single node using LLM.

    Args:
        node: The node to analyze.
        ollama_client: Ollama client for LLM processing.

    Returns:
        New nodes and edges representing causal relationships.
    """
    causal_nodes = []
    causal_edges = []

    # Prepare content for analysis
    title = node.title or ""
    body = node.body or ""
    node_type = node.type.value
    node_id = node.id

    # Create prompt for LLM
    prompt = f"""
    Analyze the following {node_type} and extract causal relationships (decisions, implications, and code changes).

    {node_type.upper()}: {title}

    CONTENT:
    {body[:3000]}  # Limit to 3000 chars to avoid token limits

    Extract the following:
    1. Decisions: What decisions were made? Why were they made?
    2. Implications: What are the implications of these decisions?
    3. Code Changes: What specific code changes resulted from these decisions?

    Format your response as JSON with the following structure:
    {{
        "decisions": [
            {{
                "title": "Decision title",
                "description": "Decision description",
                "type": "architectural|implementation|requirement",
                "confidence": 0.0-1.0
            }}
        ],
        "implications": [
            {{
                "title": "Implication title",
                "description": "Implication description",
                "type": "technical|business|security",
                "severity": "low|medium|high",
                "confidence": 0.0-1.0
            }}
        ],
        "code_changes": [
            {{
                "title": "Code change title",
                "description": "Code change description",
                "type": "feature|bugfix|refactoring",
                "confidence": 0.0-1.0
            }}
        ],
        "relationships": [
            {{
                "src_type": "decision|implication|code_change",
                "src_index": 0,
                "dst_type": "decision|implication|code_change",
                "dst_index": 0,
                "relationship": "leads_to|results_in|implements_decision|influences",
                "confidence": 0.0-1.0
            }}
        ]
    }}

    Return ONLY the JSON object, nothing else.
    """

    try:
        # Generate response from LLM
        response = ollama_client.generate(
            model="qwen3:4b",
            prompt=prompt,
            options={"temperature": 0.2}
        )

        # Extract and parse JSON
        from arc_memory.process.semantic_analysis import _extract_json_from_llm_response
        try:
            data = _extract_json_from_llm_response(response)
        except ValueError:
            logger.warning(f"Could not parse JSON from LLM response for {node_id}")
            return [], []

        # Create decision nodes
        decision_nodes = []
        for i, decision in enumerate(data.get("decisions", [])):
            decision_id = f"decision:llm_{node_id.split(':')[1]}_{i}"
            decision_node = DecisionNode(
                id=decision_id,
                type=NodeType.DECISION,
                title=decision.get("title", f"Decision from {node_type}"),
                body=decision.get("description", ""),
                decision_type=decision.get("type", "implementation"),
                confidence=decision.get("confidence", 0.7),
                source=node_id,
            )
            decision_nodes.append(decision_node)
            causal_nodes.append(decision_node)

            # Create edge from source node to decision
            source_decision_edge = Edge(
                src=node_id,
                dst=decision_id,
                rel=EdgeRel.ADDRESSES if node.type == NodeType.ISSUE else EdgeRel.IMPLEMENTS_DECISION,
                properties={"confidence": decision.get("confidence", 0.7), "extraction_method": "llm"},
            )
            causal_edges.append(source_decision_edge)

        # Create implication nodes
        implication_nodes = []
        for i, implication in enumerate(data.get("implications", [])):
            implication_id = f"implication:llm_{node_id.split(':')[1]}_{i}"
            implication_node = ImplicationNode(
                id=implication_id,
                type=NodeType.IMPLICATION,
                title=implication.get("title", f"Implication from {node_type}"),
                body=implication.get("description", ""),
                implication_type=implication.get("type", "technical"),
                severity=implication.get("severity", "medium"),
                confidence=implication.get("confidence", 0.7),
                source=node_id,
            )
            implication_nodes.append(implication_node)
            causal_nodes.append(implication_node)

            # Create edge from source node to implication
            source_implication_edge = Edge(
                src=node_id,
                dst=implication_id,
                rel=EdgeRel.LEADS_TO,
                properties={"confidence": implication.get("confidence", 0.7), "extraction_method": "llm"},
            )
            causal_edges.append(source_implication_edge)

        # Create code change nodes
        code_change_nodes = []
        for i, code_change in enumerate(data.get("code_changes", [])):
            code_change_id = f"code_change:llm_{node_id.split(':')[1]}_{i}"
            code_change_node = CodeChangeNode(
                id=code_change_id,
                type=NodeType.CODE_CHANGE,
                title=code_change.get("title", f"Code change from {node_type}"),
                body=code_change.get("description", ""),
                change_type=code_change.get("type", "implementation"),
                description=code_change.get("description", ""),
                confidence=code_change.get("confidence", 0.7),
                source=node_id,
            )
            code_change_nodes.append(code_change_node)
            causal_nodes.append(code_change_node)

            # Create edge from source node to code change
            source_code_change_edge = Edge(
                src=node_id,
                dst=code_change_id,
                rel=EdgeRel.RESULTS_IN,
                properties={"confidence": code_change.get("confidence", 0.7), "extraction_method": "llm"},
            )
            causal_edges.append(source_code_change_edge)

        # Create relationships between causal nodes
        for relationship in data.get("relationships", []):
            src_type = relationship.get("src_type")
            src_index = relationship.get("src_index", 0)
            dst_type = relationship.get("dst_type")
            dst_index = relationship.get("dst_index", 0)
            rel_type = relationship.get("relationship")
            confidence = relationship.get("confidence", 0.7)

            # Get source and destination nodes
            src_node = None
            dst_node = None

            if src_type == "decision" and src_index < len(decision_nodes):
                src_node = decision_nodes[src_index]
            elif src_type == "implication" and src_index < len(implication_nodes):
                src_node = implication_nodes[src_index]
            elif src_type == "code_change" and src_index < len(code_change_nodes):
                src_node = code_change_nodes[src_index]

            if dst_type == "decision" and dst_index < len(decision_nodes):
                dst_node = decision_nodes[dst_index]
            elif dst_type == "implication" and dst_index < len(implication_nodes):
                dst_node = implication_nodes[dst_index]
            elif dst_type == "code_change" and dst_index < len(code_change_nodes):
                dst_node = code_change_nodes[dst_index]

            # Create edge if both nodes exist
            if src_node and dst_node:
                # Map relationship type to EdgeRel
                edge_rel = None
                if rel_type == "leads_to":
                    edge_rel = EdgeRel.LEADS_TO
                elif rel_type == "results_in":
                    edge_rel = EdgeRel.RESULTS_IN
                elif rel_type == "implements_decision":
                    edge_rel = EdgeRel.IMPLEMENTS_DECISION
                elif rel_type == "influences":
                    edge_rel = EdgeRel.INFLUENCES
                else:
                    edge_rel = EdgeRel.INFLUENCES  # Default

                # Create edge
                relationship_edge = Edge(
                    src=src_node.id,
                    dst=dst_node.id,
                    rel=edge_rel,
                    properties={"confidence": confidence, "extraction_method": "llm"},
                )
                causal_edges.append(relationship_edge)

        return causal_nodes, causal_edges

    except Exception as e:
        logger.error(f"Error in LLM extraction for {node_id}: {e}")
        return [], []