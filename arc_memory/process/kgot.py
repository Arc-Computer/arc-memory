"""Knowledge Graph of Thoughts (KGoT) processor for Arc Memory.

This module implements the Knowledge Graph of Thoughts approach, which
externalizes reasoning processes into the knowledge graph itself.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from arc_memory.llm.ollama_client import OllamaClient
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType

logger = get_logger(__name__)


class KGoTProcessor:
    """Processor that implements Knowledge Graph of Thoughts."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """Initialize the KGoT processor.

        Args:
            ollama_client: Optional Ollama client for LLM processing.
        """
        self.ollama_client = ollama_client or OllamaClient()

    def process(
        self, nodes: List[Node], edges: List[Edge], repo_path: Optional[Path] = None
    ) -> Tuple[List[Node], List[Edge]]:
        """Generate a reasoning graph structure.

        Args:
            nodes: List of nodes in the knowledge graph.
            edges: List of edges in the knowledge graph.
            repo_path: Optional path to the repository.

        Returns:
            New nodes and edges representing reasoning structures.
        """
        logger.info("Generating Knowledge Graph of Thoughts structures")

        # Identify key decision points
        decision_points = self._identify_decision_points(nodes, edges)
        logger.info(f"Identified {len(decision_points)} decision points")

        # Generate reasoning structures for each decision point
        all_reasoning_nodes = []
        all_reasoning_edges = []

        for decision_point in decision_points:
            try:
                reasoning_nodes, reasoning_edges = self._generate_reasoning_structure(
                    decision_point, nodes, edges
                )
                all_reasoning_nodes.extend(reasoning_nodes)
                all_reasoning_edges.extend(reasoning_edges)
            except Exception as e:
                logger.error(f"Error generating reasoning structure: {e}")

        logger.info(
            f"Generated {len(all_reasoning_nodes)} reasoning nodes and {len(all_reasoning_edges)} reasoning edges"
        )
        return all_reasoning_nodes, all_reasoning_edges

    def _identify_decision_points(self, nodes: List[Node], edges: List[Edge]) -> List[Node]:
        """Identify key decision points in the knowledge graph.

        Args:
            nodes: List of nodes in the knowledge graph.
            edges: List of edges in the knowledge graph.

        Returns:
            List of nodes representing decision points.
        """
        decision_points = []

        # ADRs are explicit decision points
        adr_nodes = [node for node in nodes if node.type == NodeType.ADR]
        decision_points.extend(adr_nodes)

        # PRs with significant discussion are implicit decision points
        pr_nodes = [node for node in nodes if node.type == NodeType.PR]
        for pr_node in pr_nodes:
            # Check if PR has many mentions or is mentioned by many entities
            mentions_count = len(
                [
                    edge
                    for edge in edges
                    if (edge.src == pr_node.id or edge.dst == pr_node.id)
                    and edge.rel == EdgeRel.MENTIONS
                ]
            )
            if mentions_count >= 3:  # Arbitrary threshold
                decision_points.append(pr_node)

        # Issues that led to significant code changes are decision points
        issue_nodes = [node for node in nodes if node.type == NodeType.ISSUE]
        for issue_node in issue_nodes:
            # Check if issue is connected to many commits
            commit_connections = len(
                [
                    edge
                    for edge in edges
                    if edge.dst == issue_node.id and edge.src.startswith("commit:")
                ]
            )
            if commit_connections >= 2:  # Arbitrary threshold
                decision_points.append(issue_node)

        return decision_points

    def _generate_reasoning_structure(
        self, decision_point: Node, nodes: List[Node], edges: List[Edge]
    ) -> Tuple[List[Node], List[Edge]]:
        """Generate a reasoning structure for a decision point.

        Args:
            decision_point: The node representing a decision point.
            nodes: All nodes in the knowledge graph.
            edges: All edges in the knowledge graph.

        Returns:
            New nodes and edges representing the reasoning structure.
        """
        # Get context for the decision point
        context = self._get_decision_context(decision_point, nodes, edges)

        # Create prompt for the LLM
        prompt = f"""
        Analyze this decision point and generate a reasoning structure that explains the decision process.
        
        Decision point: {decision_point.title}
        Type: {decision_point.type}
        
        Context:
        {json.dumps(context, indent=2)}
        
        Generate a reasoning structure with:
        1. The key question or problem being addressed
        2. The alternatives that were considered
        3. The criteria used for evaluation
        4. The reasoning process that led to the decision
        5. The implications of the decision
        
        Format your response as JSON with the following structure:
        {{
            "question": "What was the key question?",
            "alternatives": [
                {{ "name": "Alternative 1", "description": "Description of alternative 1" }},
                {{ "name": "Alternative 2", "description": "Description of alternative 2" }}
            ],
            "criteria": [
                {{ "name": "Criterion 1", "description": "Description of criterion 1" }},
                {{ "name": "Criterion 2", "description": "Description of criterion 2" }}
            ],
            "reasoning": [
                {{ "step": 1, "description": "First step in the reasoning process" }},
                {{ "step": 2, "description": "Second step in the reasoning process" }}
            ],
            "implications": [
                "Implication 1",
                "Implication 2"
            ]
        }}
        """

        try:
            # Generate response from LLM
            response = self.ollama_client.generate(
                model="phi4-mini-reasoning",
                prompt=prompt,
                options={"temperature": 0.3},
            )

            # Parse the response
            try:
                # First try direct JSON parsing
                data = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON using regex
                import re
                # Look for JSON between triple backticks, or just any JSON-like structure
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find anything that looks like a JSON object
                    json_match = re.search(r'(\{.*\})', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # Fallback to a minimal structure
                        logger.warning(f"Could not parse JSON from LLM response for {decision_point.id}")
                        json_str = '{"question": "What decision was made?", "alternatives": [], "criteria": [], "reasoning": [], "implications": []}'
                
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {e}")
                    # Provide a minimal fallback structure
                    data = {
                        "question": f"What decision was made in {decision_point.title}?",
                        "alternatives": [],
                        "criteria": [],
                        "reasoning": [],
                        "implications": []
                    }

            # Create reasoning nodes and edges
            reasoning_nodes = []
            reasoning_edges = []

            # Create question node
            question_id = f"reasoning:question:{decision_point.id}"
            question_node = Node(
                id=question_id,
                type=NodeType.REASONING_QUESTION,
                title=data.get("question", "Unknown question"),
                extra={"decision_point": decision_point.id},
            )
            reasoning_nodes.append(question_node)

            # Connect question to decision point
            question_edge = Edge(
                src=question_id,
                dst=decision_point.id,
                rel=EdgeRel.REASONS_ABOUT,
                properties={"type": "question"},
            )
            reasoning_edges.append(question_edge)

            # Create alternative nodes
            for i, alt in enumerate(data.get("alternatives", [])):
                alt_id = f"reasoning:alternative:{decision_point.id}:{i}"
                alt_node = Node(
                    id=alt_id,
                    type=NodeType.REASONING_ALTERNATIVE,
                    title=alt.get("name", f"Alternative {i+1}"),
                    body=alt.get("description", ""),
                    extra={"decision_point": decision_point.id},
                )
                reasoning_nodes.append(alt_node)

                # Connect alternative to question
                alt_edge = Edge(
                    src=question_id,
                    dst=alt_id,
                    rel=EdgeRel.HAS_ALTERNATIVE,
                    properties={"index": i},
                )
                reasoning_edges.append(alt_edge)

            # Create criteria nodes
            for i, criterion in enumerate(data.get("criteria", [])):
                criterion_id = f"reasoning:criterion:{decision_point.id}:{i}"
                criterion_node = Node(
                    id=criterion_id,
                    type=NodeType.REASONING_CRITERION,
                    title=criterion.get("name", f"Criterion {i+1}"),
                    body=criterion.get("description", ""),
                    extra={"decision_point": decision_point.id},
                )
                reasoning_nodes.append(criterion_node)

                # Connect criterion to question
                criterion_edge = Edge(
                    src=question_id,
                    dst=criterion_id,
                    rel=EdgeRel.HAS_CRITERION,
                    properties={"index": i},
                )
                reasoning_edges.append(criterion_edge)

            # Create reasoning step nodes
            prev_step_id = question_id
            for step in data.get("reasoning", []):
                step_id = f"reasoning:step:{decision_point.id}:{step.get('step', 0)}"
                step_node = Node(
                    id=step_id,
                    type=NodeType.REASONING_STEP,
                    title=f"Step {step.get('step', 0)}",
                    body=step.get("description", ""),
                    extra={"decision_point": decision_point.id},
                )
                reasoning_nodes.append(step_node)

                # Connect step to previous step
                step_edge = Edge(
                    src=prev_step_id,
                    dst=step_id,
                    rel=EdgeRel.NEXT_STEP,
                    properties={"step": step.get("step", 0)},
                )
                reasoning_edges.append(step_edge)
                prev_step_id = step_id

            # Create implication nodes
            for i, implication in enumerate(data.get("implications", [])):
                impl_id = f"reasoning:implication:{decision_point.id}:{i}"
                impl_node = Node(
                    id=impl_id,
                    type=NodeType.REASONING_IMPLICATION,
                    title=f"Implication {i+1}",
                    body=implication,
                    extra={"decision_point": decision_point.id},
                )
                reasoning_nodes.append(impl_node)

                # Connect implication to decision point
                impl_edge = Edge(
                    src=decision_point.id,
                    dst=impl_id,
                    rel=EdgeRel.HAS_IMPLICATION,
                    properties={"index": i},
                )
                reasoning_edges.append(impl_edge)

            return reasoning_nodes, reasoning_edges

        except Exception as e:
            logger.error(f"Error generating reasoning structure: {e}")
            return [], []

    def _get_decision_context(
        self, decision_point: Node, nodes: List[Node], edges: List[Edge]
    ) -> Dict[str, Any]:
        """Get context for a decision point.

        Args:
            decision_point: The node representing a decision point.
            nodes: All nodes in the knowledge graph.
            edges: All edges in the knowledge graph.

        Returns:
            Dictionary with context information.
        """
        context = {
            "id": decision_point.id,
            "type": decision_point.type,
            "title": decision_point.title,
            "body": decision_point.body,
            "related_entities": [],
        }

        # Get directly connected nodes
        connected_edges = [
            edge
            for edge in edges
            if edge.src == decision_point.id or edge.dst == decision_point.id
        ]

        # Get related entities
        for edge in connected_edges:
            related_id = edge.dst if edge.src == decision_point.id else edge.src
            related_node = next((n for n in nodes if n.id == related_id), None)
            if related_node:
                context["related_entities"].append(
                    {
                        "id": related_node.id,
                        "type": related_node.type,
                        "title": related_node.title,
                        "relationship": edge.rel,
                        "direction": "outgoing" if edge.src == decision_point.id else "incoming",
                    }
                )

        return context


def enhance_with_reasoning_structures(
    nodes: List[Node], edges: List[Edge], repo_path: Optional[Path] = None
) -> Tuple[List[Node], List[Edge]]:
    """Enhance the knowledge graph with reasoning structures.

    Args:
        nodes: List of nodes in the knowledge graph.
        edges: List of edges in the knowledge graph.
        repo_path: Optional path to the repository.

    Returns:
        Enhanced nodes and edges.
    """
    logger.info("Enhancing knowledge graph with reasoning structures")

    # Initialize KGoT processor
    processor = KGoTProcessor()

    # Process the knowledge graph
    reasoning_nodes, reasoning_edges = processor.process(nodes, edges, repo_path)

    # Combine original and new nodes/edges
    all_nodes = nodes + reasoning_nodes
    all_edges = edges + reasoning_edges

    logger.info(
        f"Added {len(reasoning_nodes)} reasoning nodes and {len(reasoning_edges)} reasoning edges"
    )
    return all_nodes, all_edges
