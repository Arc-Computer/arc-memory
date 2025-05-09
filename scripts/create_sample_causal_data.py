#!/usr/bin/env python
"""
Script to create sample causal data for Arc Memory.

This script creates realistic sample decision nodes, implication nodes, and code change nodes
with appropriate edges between them to test the causal relationship extraction and export.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from arc_memory.schema.models import (
    DecisionNode,
    ImplicationNode,
    CodeChangeNode,
    Edge,
    EdgeRel,
    NodeType,
)
from arc_memory.sql.db import ensure_arc_dir

# Configuration
DB_PATH = ensure_arc_dir() / "graph.db"
NOW = datetime.now()
ONE_DAY = timedelta(days=1)
TWO_DAYS = timedelta(days=2)
THREE_DAYS = timedelta(days=3)


def connect_to_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def insert_node(conn, node):
    """Insert a node into the database."""
    cursor = conn.cursor()

    # Convert extra fields to JSON
    extra_dict = node.extra.copy() if node.extra else {}

    # Add timestamp to extra if present
    if hasattr(node, 'ts') and node.ts:
        extra_dict['timestamp'] = node.ts.isoformat()

    # Add specific fields based on node type
    if node.type == NodeType.DECISION:
        extra_dict['decision_type'] = node.decision_type
        extra_dict['decision_makers'] = node.decision_makers
        extra_dict['alternatives'] = node.alternatives
        extra_dict['criteria'] = node.criteria
        extra_dict['confidence'] = node.confidence
        if node.source:
            extra_dict['source'] = node.source

    elif node.type == NodeType.IMPLICATION:
        extra_dict['implication_type'] = node.implication_type
        extra_dict['severity'] = node.severity
        extra_dict['scope'] = node.scope
        extra_dict['confidence'] = node.confidence
        if node.source:
            extra_dict['source'] = node.source

    elif node.type == NodeType.CODE_CHANGE:
        extra_dict['change_type'] = node.change_type
        extra_dict['files'] = node.files
        extra_dict['description'] = node.description
        extra_dict['confidence'] = node.confidence
        if node.author:
            extra_dict['author'] = node.author
        if node.commit_sha:
            extra_dict['commit_sha'] = node.commit_sha

    # Convert to JSON
    extra = json.dumps(extra_dict)

    cursor.execute(
        """
        INSERT INTO nodes (id, type, title, body, extra)
        VALUES (?, ?, ?, ?, ?)
        """,
        (node.id, node.type.value, node.title, node.body, extra),
    )

    return cursor.lastrowid


def insert_edge(conn, edge):
    """Insert an edge into the database."""
    cursor = conn.cursor()

    # Convert properties to JSON
    properties = json.dumps(edge.properties) if edge.properties else None

    cursor.execute(
        """
        INSERT INTO edges (src, dst, rel, properties)
        VALUES (?, ?, ?, ?)
        """,
        (edge.src, edge.dst, edge.rel.value, properties),
    )

    return cursor.lastrowid


def create_sample_data():
    """Create sample causal data in the database."""
    conn = connect_to_db()

    try:
        # Sample 1: Enhanced Knowledge Graph Implementation
        # Decision: Implement Knowledge Graph of Thoughts
        decision1 = DecisionNode(
            id="decision:kgot_implementation",
            type=NodeType.DECISION,
            title="Implement Knowledge Graph of Thoughts",
            body="""
            We've decided to implement a Knowledge Graph of Thoughts (KGoT) to better capture
            decision trails in the codebase. This will enhance our ability to reason about
            code changes and their implications.

            The KGoT will connect decision points, reasoning steps, alternatives considered,
            and implications into a structured graph that can be queried and analyzed.
            """,
            ts=NOW - THREE_DAYS,
            decision_type="architectural",
            decision_makers=["Jarrod Barnes"],
            alternatives=[
                {
                    "name": "Vector embeddings only",
                    "description": "Use only vector embeddings for code understanding"
                },
                {
                    "name": "Knowledge Graph of Thoughts",
                    "description": "Implement a structured graph of reasoning processes"
                }
            ],
            criteria=[
                {
                    "name": "Reasoning capability",
                    "description": "Ability to capture and represent reasoning processes"
                },
                {
                    "name": "Implementation complexity",
                    "description": "Effort required to implement the solution"
                }
            ],
            confidence=0.95,
            source="pr:123",
        )

        # Implication: Need for enhanced reasoning structures
        implication1 = ImplicationNode(
            id="implication:kgot_reasoning_structures",
            type=NodeType.IMPLICATION,
            title="Need for enhanced reasoning structures",
            body="""
            Implementing the Knowledge Graph of Thoughts requires creating new node types
            for reasoning structures, including questions, alternatives, criteria, and
            implications. These structures need to be connected in a way that captures
            the reasoning process.
            """,
            ts=NOW - THREE_DAYS + timedelta(hours=2),
            implication_type="technical",
            severity="medium",
            scope=["arc_memory/schema/models.py", "arc_memory/process/kgot.py"],
            confidence=0.9,
            source="decision:kgot_implementation",
        )

        # Code Change: Add reasoning structure node types
        code_change1 = CodeChangeNode(
            id="code_change:add_reasoning_node_types",
            type=NodeType.CODE_CHANGE,
            title="Add reasoning structure node types",
            body="""
            Added new node types for reasoning structures:
            - REASONING_QUESTION
            - REASONING_ALTERNATIVE
            - REASONING_CRITERION
            - REASONING_STEP
            - REASONING_IMPLICATION

            Also added corresponding edge types to connect these nodes.
            """,
            ts=NOW - TWO_DAYS,
            change_type="feature",
            files=["arc_memory/schema/models.py"],
            description="Added new node types for reasoning structures",
            author="Jarrod Barnes",
            commit_sha="abc123def456",
            confidence=1.0,
        )

        # Sample 2: Causal Relationship Extraction
        # Decision: Implement causal relationship extraction
        decision2 = DecisionNode(
            id="decision:causal_extraction",
            type=NodeType.DECISION,
            title="Implement causal relationship extraction",
            body="""
            We've decided to implement causal relationship extraction to identify
            decision → implication → code-change chains in the codebase. This will
            help us understand why certain changes were made and their expected impact.

            The extraction will use both rule-based patterns and LLM-based analysis
            to identify causal relationships in commit messages, PR descriptions,
            Linear tickets, and ADRs.
            """,
            ts=NOW - TWO_DAYS,
            decision_type="implementation",
            decision_makers=["Jarrod Barnes"],
            alternatives=[
                {
                    "name": "Manual annotation only",
                    "description": "Rely only on manually annotated causal relationships"
                },
                {
                    "name": "Automated extraction",
                    "description": "Implement automated extraction of causal relationships"
                }
            ],
            criteria=[
                {
                    "name": "Accuracy",
                    "description": "Accuracy of extracted causal relationships"
                },
                {
                    "name": "Coverage",
                    "description": "Coverage of different sources of causal information"
                }
            ],
            confidence=0.9,
            source="issue:456",
        )

        # Implication: Need for causal node types
        implication2 = ImplicationNode(
            id="implication:causal_node_types",
            type=NodeType.IMPLICATION,
            title="Need for causal node types",
            body="""
            Implementing causal relationship extraction requires creating new node types
            for decisions, implications, and code changes. These node types need to
            capture the causal relationships between different entities in the codebase.
            """,
            ts=NOW - TWO_DAYS + timedelta(hours=3),
            implication_type="technical",
            severity="high",
            scope=["arc_memory/schema/models.py", "arc_memory/process/causal_extraction.py"],
            confidence=0.85,
            source="decision:causal_extraction",
        )

        # Code Change: Add causal node types
        code_change2 = CodeChangeNode(
            id="code_change:add_causal_node_types",
            type=NodeType.CODE_CHANGE,
            title="Add causal node types",
            body="""
            Added new node types for causal relationships:
            - DECISION
            - IMPLICATION
            - CODE_CHANGE

            Also added corresponding edge types to connect these nodes:
            - LEADS_TO
            - RESULTS_IN
            - IMPLEMENTS_DECISION
            - CAUSED_BY
            - INFLUENCES
            - ADDRESSES
            """,
            ts=NOW - ONE_DAY,
            change_type="feature",
            files=["arc_memory/schema/models.py"],
            description="Added new node types for causal relationships",
            author="Jarrod Barnes",
            commit_sha="def456abc789",
            confidence=1.0,
        )

        # Sample 3: Export Optimization for Causal Relationships
        # Decision: Optimize export for causal relationships
        decision3 = DecisionNode(
            id="decision:optimize_export",
            type=NodeType.DECISION,
            title="Optimize export for causal relationships",
            body="""
            We've decided to optimize the export functionality to better handle causal
            relationships. This will enhance the JSON payload for the PR bot and improve
            the LLM's ability to reason about causal relationships.

            The optimization will include adding specialized reasoning paths for causal
            relationships and enhancing the LLM optimization for causal reasoning.
            """,
            ts=NOW - ONE_DAY,
            decision_type="implementation",
            decision_makers=["Jarrod Barnes"],
            alternatives=[
                {
                    "name": "Basic export",
                    "description": "Export causal relationships without optimization"
                },
                {
                    "name": "Optimized export",
                    "description": "Optimize export specifically for causal reasoning"
                }
            ],
            criteria=[
                {
                    "name": "LLM reasoning quality",
                    "description": "Quality of LLM reasoning about causal relationships"
                },
                {
                    "name": "Export size",
                    "description": "Size of the exported JSON payload"
                }
            ],
            confidence=0.9,
            source="issue:789",
        )

        # Implication: Need for causal reasoning paths
        implication3 = ImplicationNode(
            id="implication:causal_reasoning_paths",
            type=NodeType.IMPLICATION,
            title="Need for causal reasoning paths",
            body="""
            Optimizing export for causal relationships requires adding specialized
            reasoning paths for causal chains. These paths will guide the LLM in
            reasoning about decision → implication → code-change chains.
            """,
            ts=NOW - ONE_DAY + timedelta(hours=2),
            implication_type="technical",
            severity="medium",
            scope=["arc_memory/export.py"],
            confidence=0.85,
            source="decision:optimize_export",
        )

        # Code Change: Add causal reasoning paths
        code_change3 = CodeChangeNode(
            id="code_change:add_causal_reasoning_paths",
            type=NodeType.CODE_CHANGE,
            title="Add causal reasoning paths",
            body="""
            Added specialized reasoning paths for causal relationships:
            - causal_chain_analysis: For analyzing decision → implication → code-change chains
            - implication_analysis: For analyzing implications by severity
            - reverse_causal_analysis: For tracing from code changes back to decisions
            """,
            ts=NOW,
            change_type="enhancement",
            files=["arc_memory/export.py"],
            description="Added specialized reasoning paths for causal relationships",
            author="Jarrod Barnes",
            commit_sha="ghi789jkl012",
            confidence=1.0,
        )

        # Insert nodes
        nodes = [
            decision1, implication1, code_change1,
            decision2, implication2, code_change2,
            decision3, implication3, code_change3,
        ]

        for node in nodes:
            insert_node(conn, node)
            print(f"Inserted node: {node.id} - {node.title}")

        # Create edges
        edges = [
            # Sample 1 edges
            Edge(
                src=decision1.id,
                dst=implication1.id,
                rel=EdgeRel.LEADS_TO,
                properties={"confidence": 0.9, "extraction_method": "manual"},
            ),
            Edge(
                src=implication1.id,
                dst=code_change1.id,
                rel=EdgeRel.RESULTS_IN,
                properties={"confidence": 0.9, "extraction_method": "manual"},
            ),
            Edge(
                src="pr:123",
                dst=decision1.id,
                rel=EdgeRel.IMPLEMENTS_DECISION,
                properties={"confidence": 0.9, "extraction_method": "manual"},
            ),

            # Sample 2 edges
            Edge(
                src=decision2.id,
                dst=implication2.id,
                rel=EdgeRel.LEADS_TO,
                properties={"confidence": 0.85, "extraction_method": "manual"},
            ),
            Edge(
                src=implication2.id,
                dst=code_change2.id,
                rel=EdgeRel.RESULTS_IN,
                properties={"confidence": 0.85, "extraction_method": "manual"},
            ),
            Edge(
                src="issue:456",
                dst=decision2.id,
                rel=EdgeRel.ADDRESSES,
                properties={"confidence": 0.85, "extraction_method": "manual"},
            ),

            # Sample 3 edges
            Edge(
                src=decision3.id,
                dst=implication3.id,
                rel=EdgeRel.LEADS_TO,
                properties={"confidence": 0.85, "extraction_method": "manual"},
            ),
            Edge(
                src=implication3.id,
                dst=code_change3.id,
                rel=EdgeRel.RESULTS_IN,
                properties={"confidence": 0.85, "extraction_method": "manual"},
            ),
            Edge(
                src="issue:789",
                dst=decision3.id,
                rel=EdgeRel.ADDRESSES,
                properties={"confidence": 0.85, "extraction_method": "manual"},
            ),
        ]

        for edge in edges:
            insert_edge(conn, edge)
            print(f"Inserted edge: {edge.src} -{edge.rel.value}-> {edge.dst}")

        conn.commit()
        print(f"Successfully created {len(nodes)} nodes and {len(edges)} edges")

    except Exception as e:
        conn.rollback()
        print(f"Error creating sample data: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print(f"Creating sample causal data in {DB_PATH}")
    create_sample_data()
    print("Done!")
