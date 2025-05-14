"""Knowledge Graph of Thoughts (KGoT) processor for Arc Memory.

This module implements the Knowledge Graph of Thoughts approach, which
externalizes reasoning processes into the knowledge graph itself.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from arc_memory.llm.ollama_client import OllamaClient
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType

# Import OpenAI client conditionally to avoid hard dependency
try:
    from arc_memory.llm.openai_client import OpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = get_logger(__name__)


class KGoTProcessor:
    """Processor that implements Knowledge Graph of Thoughts."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        system_prompt: Optional[str] = None
    ):
        """Initialize the KGoT processor.

        Args:
            ollama_client: Optional Ollama client for LLM processing.
            system_prompt: Optional system prompt for the LLM.
        """
        self.ollama_client = ollama_client or OllamaClient()
        self.system_prompt = system_prompt

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

        # First, look for explicit DecisionNode instances from causal extraction
        decision_nodes = [node for node in nodes if node.type == NodeType.DECISION]
        if decision_nodes:
            logger.info(f"Found {len(decision_nodes)} explicit decision nodes from causal extraction")
            decision_points.extend(decision_nodes)

            # Also add the source nodes of these decisions for context
            source_nodes = []
            for decision_node in decision_nodes:
                if hasattr(decision_node, "source") and decision_node.source:
                    source_node = next((n for n in nodes if n.id == decision_node.source), None)
                    if source_node and source_node not in decision_points and source_node not in source_nodes:
                        source_nodes.append(source_node)

            decision_points.extend(source_nodes)
            logger.info(f"Added {len(source_nodes)} source nodes as decision points")

        # ADRs are explicit decision points
        adr_nodes = [node for node in nodes if node.type == NodeType.ADR]
        # Only add ADRs that aren't already included via decision nodes
        new_adr_nodes = [node for node in adr_nodes if node not in decision_points]
        decision_points.extend(new_adr_nodes)
        logger.info(f"Added {len(new_adr_nodes)} ADR nodes as decision points")

        # PRs with significant discussion are implicit decision points
        pr_nodes = [node for node in nodes if node.type == NodeType.PR]
        added_pr_count = 0
        for pr_node in pr_nodes:
            # Skip if already included
            if pr_node in decision_points:
                continue

            # Check if PR has many mentions or is mentioned by many entities
            mentions_count = len(
                [
                    edge
                    for edge in edges
                    if (edge.src == pr_node.id or edge.dst == pr_node.id)
                    and edge.rel == EdgeRel.MENTIONS
                ]
            )

            # Check if PR has IMPLEMENTS_DECISION or LEADS_TO edges
            decision_edges = len(
                [
                    edge
                    for edge in edges
                    if (edge.src == pr_node.id or edge.dst == pr_node.id)
                    and edge.rel in [EdgeRel.IMPLEMENTS_DECISION, EdgeRel.LEADS_TO, EdgeRel.RESULTS_IN]
                ]
            )

            # Include PR if it meets any of the criteria
            if mentions_count >= 3 or decision_edges > 0:
                decision_points.append(pr_node)
                added_pr_count += 1

        if added_pr_count > 0:
            logger.info(f"Added {added_pr_count} PR nodes as decision points")

        # Issues that led to significant code changes or have causal relationships are decision points
        issue_nodes = [node for node in nodes if node.type == NodeType.ISSUE]
        added_issue_count = 0
        for issue_node in issue_nodes:
            # Skip if already included
            if issue_node in decision_points:
                continue

            # Check if issue is connected to many commits
            commit_connections = len(
                [
                    edge
                    for edge in edges
                    if edge.dst == issue_node.id and edge.src.startswith("commit:")
                ]
            )

            # Check if issue has ADDRESSES or LEADS_TO edges
            causal_edges = len(
                [
                    edge
                    for edge in edges
                    if (edge.src == issue_node.id or edge.dst == issue_node.id)
                    and edge.rel in [EdgeRel.ADDRESSES, EdgeRel.LEADS_TO]
                ]
            )

            # Include issue if it meets any of the criteria
            if commit_connections >= 2 or causal_edges > 0:
                decision_points.append(issue_node)
                added_issue_count += 1

        if added_issue_count > 0:
            logger.info(f"Added {added_issue_count} issue nodes as decision points")

        # Commits with explicit decisions in their messages
        commit_nodes = [node for node in nodes if node.type == NodeType.COMMIT]
        added_commit_count = 0
        for commit_node in commit_nodes:
            # Skip if already included
            if commit_node in decision_points:
                continue

            # Check if commit has IMPLEMENTS_DECISION edges
            decision_edges = len(
                [
                    edge
                    for edge in edges
                    if edge.src == commit_node.id and edge.rel == EdgeRel.IMPLEMENTS_DECISION
                ]
            )

            if decision_edges > 0:
                decision_points.append(commit_node)
                added_commit_count += 1

        if added_commit_count > 0:
            logger.info(f"Added {added_commit_count} commit nodes as decision points")

        logger.info(f"Identified {len(decision_points)} total decision points")
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
        2. The alternatives that were considered (with pros and cons for each)
        3. The criteria used for evaluation (with importance ratings)
        4. The reasoning process that led to the decision (step by step)
        5. The implications of the decision (with confidence scores)

        Format your response as JSON with the following structure:
        {{
            "question": "What was the key question?",
            "confidence": 0.9, // Confidence in the question formulation (0.0-1.0)
            "alternatives": [
                {{
                    "name": "Alternative 1",
                    "description": "Description of alternative 1",
                    "pros": ["Pro 1", "Pro 2"],
                    "cons": ["Con 1", "Con 2"],
                    "confidence": 0.8 // Confidence that this was a real alternative (0.0-1.0)
                }},
                {{
                    "name": "Alternative 2",
                    "description": "Description of alternative 2",
                    "pros": ["Pro 1", "Pro 2"],
                    "cons": ["Con 1", "Con 2"],
                    "confidence": 0.7
                }}
            ],
            "criteria": [
                {{
                    "name": "Criterion 1",
                    "description": "Description of criterion 1",
                    "importance": "high", // high, medium, or low
                    "confidence": 0.9 // Confidence that this was a real criterion (0.0-1.0)
                }},
                {{
                    "name": "Criterion 2",
                    "description": "Description of criterion 2",
                    "importance": "medium",
                    "confidence": 0.8
                }}
            ],
            "reasoning": [
                {{
                    "step": 1,
                    "description": "First step in the reasoning process",
                    "confidence": 0.9 // Confidence in this reasoning step (0.0-1.0)
                }},
                {{
                    "step": 2,
                    "description": "Second step in the reasoning process",
                    "confidence": 0.8
                }}
            ],
            "implications": [
                {{
                    "description": "Implication 1",
                    "severity": "high", // high, medium, or low
                    "confidence": 0.9 // Confidence in this implication (0.0-1.0)
                }},
                {{
                    "description": "Implication 2",
                    "severity": "medium",
                    "confidence": 0.8
                }}
            ]
        }}
        """

        try:
            # Generate response from LLM
            response = self.ollama_client.generate(
                model="qwen3:4b",
                prompt=prompt,
                system=self.system_prompt,
                options={"temperature": 0.3},
            )

            # Parse the response
            try:
                # Use the robust JSON extraction function from semantic_analysis
                from arc_memory.process.semantic_analysis import _extract_json_from_llm_response
                try:
                    data = _extract_json_from_llm_response(response)
                except ValueError:
                    # Fallback to a minimal structure
                    logger.warning(f"Could not parse JSON from LLM response for {decision_point.id}")
                    data = {
                        "question": "What decision was made?",
                        "alternatives": [],
                        "criteria": [],
                        "reasoning": [],
                        "implications": []
                    }
            except ImportError:
                # Handle the case where semantic_analysis module can't be imported
                logger.error("Could not import _extract_json_from_llm_response from semantic_analysis")
                # Fallback to a minimal structure
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
            question_confidence = data.get("confidence", 0.7)  # Default confidence if not provided
            question_node = Node(
                id=question_id,
                type=NodeType.REASONING_QUESTION,
                title=data.get("question", "Unknown question"),
                extra={
                    "decision_point": decision_point.id,
                    "confidence": question_confidence,
                },
            )
            reasoning_nodes.append(question_node)

            # Connect question to decision point
            question_edge = Edge(
                src=question_id,
                dst=decision_point.id,
                rel=EdgeRel.REASONS_ABOUT,
                properties={
                    "type": "question",
                    "confidence": question_confidence,
                },
            )
            reasoning_edges.append(question_edge)

            # Create alternative nodes
            for i, alt in enumerate(data.get("alternatives", [])):
                alt_id = f"reasoning:alternative:{decision_point.id}:{i}"
                alt_confidence = alt.get("confidence", 0.7)  # Default confidence if not provided

                # Prepare pros and cons for the extra field
                pros = alt.get("pros", [])
                cons = alt.get("cons", [])

                alt_node = Node(
                    id=alt_id,
                    type=NodeType.REASONING_ALTERNATIVE,
                    title=alt.get("name", f"Alternative {i+1}"),
                    body=alt.get("description", ""),
                    extra={
                        "decision_point": decision_point.id,
                        "confidence": alt_confidence,
                        "pros": pros,
                        "cons": cons,
                    },
                )
                reasoning_nodes.append(alt_node)

                # Connect alternative to question
                alt_edge = Edge(
                    src=question_id,
                    dst=alt_id,
                    rel=EdgeRel.HAS_ALTERNATIVE,
                    properties={
                        "index": i,
                        "confidence": alt_confidence,
                    },
                )
                reasoning_edges.append(alt_edge)

            # Create criteria nodes
            for i, criterion in enumerate(data.get("criteria", [])):
                criterion_id = f"reasoning:criterion:{decision_point.id}:{i}"
                criterion_confidence = criterion.get("confidence", 0.7)  # Default confidence if not provided
                importance = criterion.get("importance", "medium")  # Default importance if not provided

                criterion_node = Node(
                    id=criterion_id,
                    type=NodeType.REASONING_CRITERION,
                    title=criterion.get("name", f"Criterion {i+1}"),
                    body=criterion.get("description", ""),
                    extra={
                        "decision_point": decision_point.id,
                        "confidence": criterion_confidence,
                        "importance": importance,
                    },
                )
                reasoning_nodes.append(criterion_node)

                # Connect criterion to question
                criterion_edge = Edge(
                    src=question_id,
                    dst=criterion_id,
                    rel=EdgeRel.HAS_CRITERION,
                    properties={
                        "index": i,
                        "confidence": criterion_confidence,
                        "importance": importance,
                    },
                )
                reasoning_edges.append(criterion_edge)

            # Create reasoning step nodes
            prev_step_id = question_id
            for step in data.get("reasoning", []):
                step_id = f"reasoning:step:{decision_point.id}:{step.get('step', 0)}"
                step_confidence = step.get("confidence", 0.7)  # Default confidence if not provided

                step_node = Node(
                    id=step_id,
                    type=NodeType.REASONING_STEP,
                    title=f"Step {step.get('step', 0)}",
                    body=step.get("description", ""),
                    extra={
                        "decision_point": decision_point.id,
                        "confidence": step_confidence,
                    },
                )
                reasoning_nodes.append(step_node)

                # Connect step to previous step
                step_edge = Edge(
                    src=prev_step_id,
                    dst=step_id,
                    rel=EdgeRel.NEXT_STEP,
                    properties={
                        "step": step.get("step", 0),
                        "confidence": step_confidence,
                    },
                )
                reasoning_edges.append(step_edge)
                prev_step_id = step_id

            # Create implication nodes
            for i, implication in enumerate(data.get("implications", [])):
                impl_id = f"reasoning:implication:{decision_point.id}:{i}"

                # Handle both string and dict formats for implications
                if isinstance(implication, dict):
                    impl_description = implication.get("description", f"Implication {i+1}")
                    impl_confidence = implication.get("confidence", 0.7)
                    impl_severity = implication.get("severity", "medium")
                else:
                    impl_description = implication
                    impl_confidence = 0.7  # Default confidence
                    impl_severity = "medium"  # Default severity

                impl_node = Node(
                    id=impl_id,
                    type=NodeType.REASONING_IMPLICATION,
                    title=f"Implication {i+1}",
                    body=impl_description,
                    extra={
                        "decision_point": decision_point.id,
                        "confidence": impl_confidence,
                        "severity": impl_severity,
                    },
                )
                reasoning_nodes.append(impl_node)

                # Connect implication to decision point
                impl_edge = Edge(
                    src=decision_point.id,
                    dst=impl_id,
                    rel=EdgeRel.HAS_IMPLICATION,
                    properties={
                        "index": i,
                        "confidence": impl_confidence,
                        "severity": impl_severity,
                    },
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
            "causal_relationships": [],
            "extra_attributes": {},
        }

        # Add any extra attributes from the node
        if hasattr(decision_point, "extra") and decision_point.extra:
            context["extra_attributes"] = decision_point.extra

        # Add specific attributes based on node type
        if decision_point.type == NodeType.DECISION:
            if hasattr(decision_point, "decision_type"):
                context["decision_type"] = decision_point.decision_type
            if hasattr(decision_point, "decision_makers"):
                context["decision_makers"] = decision_point.decision_makers
            if hasattr(decision_point, "confidence"):
                context["confidence"] = decision_point.confidence
            if hasattr(decision_point, "alternatives"):
                context["alternatives"] = decision_point.alternatives
            if hasattr(decision_point, "criteria"):
                context["criteria"] = decision_point.criteria
            if hasattr(decision_point, "source"):
                context["source"] = decision_point.source

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
                # Create basic entity info
                entity_info = {
                    "id": related_node.id,
                    "type": related_node.type,
                    "title": related_node.title,
                    "relationship": edge.rel,
                    "direction": "outgoing" if edge.src == decision_point.id else "incoming",
                }

                # Add confidence if available
                if edge.properties and "confidence" in edge.properties:
                    entity_info["confidence"] = edge.properties["confidence"]

                # Add to related entities
                context["related_entities"].append(entity_info)

                # If this is a causal relationship, add to causal_relationships
                if edge.rel in [
                    EdgeRel.LEADS_TO,
                    EdgeRel.RESULTS_IN,
                    EdgeRel.IMPLEMENTS_DECISION,
                    EdgeRel.CAUSED_BY,
                    EdgeRel.INFLUENCES,
                    EdgeRel.ADDRESSES,
                    EdgeRel.HAS_IMPLICATION
                ]:
                    causal_info = entity_info.copy()

                    # Add body content for more context
                    if related_node.body:
                        causal_info["body"] = related_node.body

                    # Add specific attributes based on node type
                    if related_node.type == NodeType.DECISION:
                        if hasattr(related_node, "decision_type"):
                            causal_info["decision_type"] = related_node.decision_type
                        if hasattr(related_node, "confidence"):
                            causal_info["confidence"] = related_node.confidence

                    elif related_node.type == NodeType.IMPLICATION:
                        if hasattr(related_node, "implication_type"):
                            causal_info["implication_type"] = related_node.implication_type
                        if hasattr(related_node, "severity"):
                            causal_info["severity"] = related_node.severity
                        if hasattr(related_node, "confidence"):
                            causal_info["confidence"] = related_node.confidence

                    elif related_node.type == NodeType.CODE_CHANGE:
                        if hasattr(related_node, "change_type"):
                            causal_info["change_type"] = related_node.change_type
                        if hasattr(related_node, "files"):
                            causal_info["files"] = related_node.files
                        if hasattr(related_node, "confidence"):
                            causal_info["confidence"] = related_node.confidence

                    context["causal_relationships"].append(causal_info)

        # Add second-degree connections for causal relationships
        if context["causal_relationships"]:
            for causal_rel in context["causal_relationships"]:
                related_id = causal_rel["id"]

                # Find edges connecting to this related node
                second_degree_edges = [
                    edge for edge in edges
                    if (edge.src == related_id or edge.dst == related_id)
                    and edge.src != decision_point.id
                    and edge.dst != decision_point.id
                ]

                second_degree_connections = []
                for edge in second_degree_edges:
                    second_id = edge.dst if edge.src == related_id else edge.src
                    second_node = next((n for n in nodes if n.id == second_id), None)

                    if second_node and second_node.id != decision_point.id:
                        connection_info = {
                            "id": second_node.id,
                            "type": second_node.type,
                            "title": second_node.title,
                            "relationship": edge.rel,
                            "direction": "outgoing" if edge.src == related_id else "incoming",
                        }

                        # Add confidence if available
                        if edge.properties and "confidence" in edge.properties:
                            connection_info["confidence"] = edge.properties["confidence"]

                        second_degree_connections.append(connection_info)

                if second_degree_connections:
                    causal_rel["connected_entities"] = second_degree_connections

        return context


def enhance_with_reasoning_structures(
    nodes: List[Node],
    edges: List[Edge],
    repo_path: Optional[Path] = None,
    ollama_client: Optional[OllamaClient] = None,
    openai_client: Optional[Any] = None,
    llm_provider: str = "ollama",
    enhancement_level: str = "standard",
    system_prompt: Optional[str] = None
) -> Tuple[List[Node], List[Edge]]:
    """Enhance the knowledge graph with reasoning structures.

    Args:
        nodes: List of nodes in the knowledge graph.
        edges: List of edges in the knowledge graph.
        repo_path: Optional path to the repository.
        ollama_client: Optional Ollama client for LLM processing.
        openai_client: Optional OpenAI client for LLM processing.
        llm_provider: The LLM provider to use ("ollama" or "openai").
        enhancement_level: Level of enhancement to apply ("fast", "standard", or "deep").
        system_prompt: Optional system prompt for the LLM.

    Returns:
        Enhanced nodes and edges.
    """
    logger.info(f"Enhancing knowledge graph with reasoning structures ({enhancement_level} level)")

    # Skip processing if enhancement level is none
    if enhancement_level == "none":
        logger.info(f"Skipping reasoning structure generation (enhancement level: {enhancement_level})")
        return nodes, edges

    # Initialize the KGoT processor with appropriate system prompt based on enhancement level
    if system_prompt is None:
        if enhancement_level == "fast":
            system_prompt = """You are a reasoning assistant that helps extract decision trails from software development artifacts.
            Focus on identifying the key decisions and their immediate implications.
            Keep your analysis concise and focus only on the most important aspects.
            Provide confidence scores that reflect the certainty of your analysis."""
        elif enhancement_level == "standard":
            system_prompt = """You are a reasoning assistant that helps extract decision trails from software development artifacts.
            Analyze the decision points to identify the key questions, alternatives considered, evaluation criteria,
            reasoning process, and implications. Provide confidence scores for each element of your analysis.
            Focus on providing a balanced analysis that captures the essential reasoning without excessive detail."""
        elif enhancement_level == "deep":
            system_prompt = """You are a reasoning assistant that helps extract comprehensive decision trails from software development artifacts.
            Perform a detailed analysis of decision points to identify the key questions, all alternatives considered,
            evaluation criteria with importance ratings, step-by-step reasoning process, and all implications with severity ratings.
            Provide confidence scores for each element of your analysis, and be thorough in capturing all aspects of the decision process.
            Consider second-order effects and connections between different decisions."""

    # Initialize the KGoT processor with the appropriate client
    if llm_provider == "openai" and OPENAI_AVAILABLE and openai_client is not None:
        # Create a custom KGoTProcessor that uses OpenAI
        class OpenAIKGoTProcessor(KGoTProcessor):
            def __init__(self, openai_client, system_prompt=None):
                self.openai_client = openai_client
                self.system_prompt = system_prompt

            def _generate_reasoning_structure(
                self, decision_point: Node, nodes: List[Node], edges: List[Edge]
            ) -> Tuple[List[Node], List[Edge]]:
                # Get context for the decision point
                context = self._get_decision_context(decision_point, nodes, edges)

                # Create prompt for the LLM (same as in the parent class)
                prompt = f"""
                Analyze this decision point and generate a reasoning structure that explains the decision process.

                Decision point: {decision_point.title}
                Type: {decision_point.type}

                Context:
                {json.dumps(context, indent=2)}

                Generate a reasoning structure with:
                1. The key question or problem being addressed
                2. The alternatives that were considered (with pros and cons for each)
                3. The criteria used for evaluation (with importance ratings)
                4. The reasoning process that led to the decision (step by step)
                5. The implications of the decision (with confidence scores)

                Format your response as JSON with the following structure:
                {{
                    "question": "What was the key question?",
                    "confidence": 0.9, // Confidence in the question formulation (0.0-1.0)
                    "alternatives": [
                        {{
                            "name": "Alternative 1",
                            "description": "Description of alternative 1",
                            "pros": ["Pro 1", "Pro 2"],
                            "cons": ["Con 1", "Con 2"],
                            "confidence": 0.8 // Confidence that this was a real alternative (0.0-1.0)
                        }},
                        {{
                            "name": "Alternative 2",
                            "description": "Description of alternative 2",
                            "pros": ["Pro 1", "Pro 2"],
                            "cons": ["Con 1", "Con 2"],
                            "confidence": 0.7
                        }}
                    ],
                    "criteria": [
                        {{
                            "name": "Criterion 1",
                            "description": "Description of criterion 1",
                            "importance": "high", // high, medium, or low
                            "confidence": 0.9 // Confidence that this was a real criterion (0.0-1.0)
                        }},
                        {{
                            "name": "Criterion 2",
                            "description": "Description of criterion 2",
                            "importance": "medium",
                            "confidence": 0.8
                        }}
                    ],
                    "reasoning": [
                        {{
                            "step": 1,
                            "description": "First step in the reasoning process",
                            "confidence": 0.9 // Confidence in this reasoning step (0.0-1.0)
                        }},
                        {{
                            "step": 2,
                            "description": "Second step in the reasoning process",
                            "confidence": 0.8
                        }}
                    ],
                    "implications": [
                        {{
                            "description": "Implication 1",
                            "severity": "high", // high, medium, or low
                            "confidence": 0.9 // Confidence in this implication (0.0-1.0)
                        }},
                        {{
                            "description": "Implication 2",
                            "severity": "medium",
                            "confidence": 0.8
                        }}
                    ]
                }}
                """

                try:
                    # Generate response from OpenAI
                    response = self.openai_client.generate(
                        model="gpt-4.1",
                        prompt=prompt,
                        system=self.system_prompt,
                        options={"temperature": 0.3},
                    )

                    # Parse the response (same as in the parent class)
                    try:
                        # Use the robust JSON extraction function from semantic_analysis
                        from arc_memory.process.semantic_analysis import _extract_json_from_llm_response
                        try:
                            data = _extract_json_from_llm_response(response)
                        except ValueError:
                            # Fallback to a minimal structure
                            logger.warning(f"Could not parse JSON from LLM response for {decision_point.id}")
                            data = {
                                "question": "What decision was made?",
                                "alternatives": [],
                                "criteria": [],
                                "reasoning": [],
                                "implications": []
                            }
                    except ImportError:
                        # Handle the case where semantic_analysis module can't be imported
                        logger.error("Could not import _extract_json_from_llm_response from semantic_analysis")
                        # Fallback to a minimal structure
                        data = {
                            "question": f"What decision was made in {decision_point.title}?",
                            "alternatives": [],
                            "criteria": [],
                            "reasoning": [],
                            "implications": []
                        }

                    # Create reasoning nodes and edges (same as in the parent class)
                    # This is a direct copy of the parent class implementation
                    reasoning_nodes = []
                    reasoning_edges = []

                    # Create question node
                    question_id = f"reasoning:question:{decision_point.id}"
                    question_confidence = data.get("confidence", 0.7)  # Default confidence if not provided
                    question_node = Node(
                        id=question_id,
                        type=NodeType.REASONING_QUESTION,
                        title=data.get("question", "Unknown question"),
                        extra={
                            "decision_point": decision_point.id,
                            "confidence": question_confidence,
                        },
                    )
                    reasoning_nodes.append(question_node)

                    # Connect question to decision point
                    question_edge = Edge(
                        src=question_id,
                        dst=decision_point.id,
                        rel=EdgeRel.REASONS_ABOUT,
                        properties={
                            "type": "question",
                            "confidence": question_confidence,
                        },
                    )
                    reasoning_edges.append(question_edge)

                    # Create alternative nodes
                    for i, alt in enumerate(data.get("alternatives", [])):
                        alt_id = f"reasoning:alternative:{decision_point.id}:{i}"
                        alt_confidence = alt.get("confidence", 0.7)  # Default confidence if not provided

                        # Prepare pros and cons for the extra field
                        pros = alt.get("pros", [])
                        cons = alt.get("cons", [])

                        alt_node = Node(
                            id=alt_id,
                            type=NodeType.REASONING_ALTERNATIVE,
                            title=alt.get("name", f"Alternative {i+1}"),
                            body=alt.get("description", ""),
                            extra={
                                "decision_point": decision_point.id,
                                "confidence": alt_confidence,
                                "pros": pros,
                                "cons": cons,
                            },
                        )
                        reasoning_nodes.append(alt_node)

                        # Connect alternative to question
                        alt_edge = Edge(
                            src=question_id,
                            dst=alt_id,
                            rel=EdgeRel.HAS_ALTERNATIVE,
                            properties={
                                "index": i,
                                "confidence": alt_confidence,
                            },
                        )
                        reasoning_edges.append(alt_edge)

                    # Create criteria nodes
                    for i, criterion in enumerate(data.get("criteria", [])):
                        criterion_id = f"reasoning:criterion:{decision_point.id}:{i}"
                        criterion_confidence = criterion.get("confidence", 0.7)  # Default confidence if not provided
                        importance = criterion.get("importance", "medium")  # Default importance if not provided

                        criterion_node = Node(
                            id=criterion_id,
                            type=NodeType.REASONING_CRITERION,
                            title=criterion.get("name", f"Criterion {i+1}"),
                            body=criterion.get("description", ""),
                            extra={
                                "decision_point": decision_point.id,
                                "confidence": criterion_confidence,
                                "importance": importance,
                            },
                        )
                        reasoning_nodes.append(criterion_node)

                        # Connect criterion to question
                        criterion_edge = Edge(
                            src=question_id,
                            dst=criterion_id,
                            rel=EdgeRel.HAS_CRITERION,
                            properties={
                                "index": i,
                                "confidence": criterion_confidence,
                                "importance": importance,
                            },
                        )
                        reasoning_edges.append(criterion_edge)

                    # Create reasoning step nodes
                    prev_step_id = question_id
                    for step in data.get("reasoning", []):
                        step_id = f"reasoning:step:{decision_point.id}:{step.get('step', 0)}"
                        step_confidence = step.get("confidence", 0.7)  # Default confidence if not provided

                        step_node = Node(
                            id=step_id,
                            type=NodeType.REASONING_STEP,
                            title=f"Step {step.get('step', 0)}",
                            body=step.get("description", ""),
                            extra={
                                "decision_point": decision_point.id,
                                "confidence": step_confidence,
                            },
                        )
                        reasoning_nodes.append(step_node)

                        # Connect step to previous step
                        step_edge = Edge(
                            src=prev_step_id,
                            dst=step_id,
                            rel=EdgeRel.NEXT_STEP,
                            properties={
                                "step": step.get("step", 0),
                                "confidence": step_confidence,
                            },
                        )
                        reasoning_edges.append(step_edge)
                        prev_step_id = step_id

                    # Create implication nodes
                    for i, implication in enumerate(data.get("implications", [])):
                        impl_id = f"reasoning:implication:{decision_point.id}:{i}"

                        # Handle both string and dict formats for implications
                        if isinstance(implication, dict):
                            impl_description = implication.get("description", f"Implication {i+1}")
                            impl_confidence = implication.get("confidence", 0.7)
                            impl_severity = implication.get("severity", "medium")
                        else:
                            impl_description = implication
                            impl_confidence = 0.7  # Default confidence
                            impl_severity = "medium"  # Default severity

                        impl_node = Node(
                            id=impl_id,
                            type=NodeType.REASONING_IMPLICATION,
                            title=f"Implication {i+1}",
                            body=impl_description,
                            extra={
                                "decision_point": decision_point.id,
                                "confidence": impl_confidence,
                                "severity": impl_severity,
                            },
                        )
                        reasoning_nodes.append(impl_node)

                        # Connect implication to decision point
                        impl_edge = Edge(
                            src=decision_point.id,
                            dst=impl_id,
                            rel=EdgeRel.HAS_IMPLICATION,
                            properties={
                                "index": i,
                                "confidence": impl_confidence,
                                "severity": impl_severity,
                            },
                        )
                        reasoning_edges.append(impl_edge)

                    return reasoning_nodes, reasoning_edges

                except Exception as e:
                    logger.error(f"Error generating reasoning structure with OpenAI: {e}")
                    return [], []

        # Use the OpenAI processor
        processor = OpenAIKGoTProcessor(openai_client=openai_client, system_prompt=system_prompt)
        logger.info("Using OpenAI for reasoning structure generation")
    else:
        # Use the default Ollama processor
        processor = KGoTProcessor(ollama_client=ollama_client, system_prompt=system_prompt)
        logger.info("Using Ollama for reasoning structure generation")

    # For fast enhancement level, limit the scope of analysis
    if enhancement_level == "fast":
        # Filter to only the most important decision points
        decision_nodes = [n for n in nodes if n.type == NodeType.DECISION]
        adr_nodes = [n for n in nodes if n.type == NodeType.ADR]

        # Prioritize explicit decision nodes and ADRs
        priority_nodes = decision_nodes + adr_nodes

        if priority_nodes:
            # Only process the top 5 most important nodes
            limited_nodes = priority_nodes[:min(5, len(priority_nodes))]
            logger.info(f"Fast mode: Limited analysis to {len(limited_nodes)} high-priority decision points")

            # Generate reasoning structures only for these nodes
            reasoning_nodes, reasoning_edges = processor.process(limited_nodes + nodes, edges, repo_path)
        else:
            # If no priority nodes, process normally but with a limit
            reasoning_nodes, reasoning_edges = processor.process(nodes, edges, repo_path)
    else:
        # For standard and deep enhancement levels, process all nodes
        reasoning_nodes, reasoning_edges = processor.process(nodes, edges, repo_path)

    # Add the new nodes and edges to the original graph
    enhanced_nodes = nodes + reasoning_nodes
    enhanced_edges = edges + reasoning_edges

    logger.info(f"Added {len(reasoning_nodes)} reasoning nodes and {len(reasoning_edges)} reasoning edges")
    return enhanced_nodes, enhanced_edges
