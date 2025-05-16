"""Semantic analysis for Arc Memory.

This module provides functions for enhancing the knowledge graph with
semantic understanding derived from natural language processing and LLMs.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from arc_memory.llm.ollama_client import OllamaClient
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    ConceptNode,
    Edge,
    EdgeRel,
    Node,
    NodeType,
)

# Import OpenAI client conditionally to avoid hard dependency
try:
    from arc_memory.llm.openai_client import OpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = get_logger(__name__)


def enhance_with_semantic_analysis(
    nodes: List[Node],
    edges: List[Edge],
    repo_path: Optional[Path] = None,
    enhancement_level: str = "standard",
    ollama_client: Optional[OllamaClient] = None,
    openai_client: Optional[Any] = None,
    llm_provider: str = "ollama",
    llm_model: Optional[str] = None,
) -> Tuple[List[Node], List[Edge]]:
    """Enhance nodes and edges with semantic analysis.

    Args:
        nodes: List of nodes to enhance.
        edges: List of edges to enhance.
        repo_path: Path to the repository (for accessing file content).
        enhancement_level: Level of enhancement to apply.
        ollama_client: Optional Ollama client for LLM processing.
        openai_client: Optional OpenAI client for LLM processing.
        llm_provider: The LLM provider to use ("ollama" or "openai").
        llm_model: Optional model name to use with the LLM provider.

    Returns:
        Enhanced nodes and edges.
    """
    logger.info(f"Enhancing knowledge graph with semantic analysis ({enhancement_level} level)")

    # Initialize LLM client if not provided
    if llm_provider == "openai":
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI package not installed. Falling back to Ollama.")
            llm_provider = "ollama"

        if openai_client is None and OPENAI_AVAILABLE:
            try:
                openai_client = OpenAIClient()
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Falling back to Ollama.")
                llm_provider = "ollama"

    # If using Ollama or fallback from OpenAI
    if llm_provider == "ollama" and ollama_client is None:
        ollama_client = OllamaClient()

    # Apply different levels of enhancement
    if enhancement_level == "fast":
        # Basic enhancement - extract key concepts
        if llm_provider == "openai" and openai_client is not None:
            new_nodes, new_edges = extract_key_concepts_openai(nodes, edges, openai_client)
        else:
            new_nodes, new_edges = extract_key_concepts(nodes, edges, ollama_client)
    elif enhancement_level == "standard":
        # Standard enhancement - extract concepts and relationships
        if llm_provider == "openai" and openai_client is not None:
            concept_nodes, concept_edges = extract_key_concepts_openai(nodes, edges, openai_client)
            relationship_edges = infer_semantic_relationships(nodes + concept_nodes, edges, ollama_client)
        else:
            concept_nodes, concept_edges = extract_key_concepts(nodes, edges, ollama_client)
            relationship_edges = infer_semantic_relationships(nodes + concept_nodes, edges, ollama_client)
        new_nodes, new_edges = concept_nodes, concept_edges + relationship_edges
    elif enhancement_level == "deep":
        # Deep enhancement - full semantic analysis
        if llm_provider == "openai" and openai_client is not None:
            concept_nodes, concept_edges = extract_key_concepts_openai(nodes, edges, openai_client)
            relationship_edges = infer_semantic_relationships(nodes + concept_nodes, edges, ollama_client)
            architecture_nodes, architecture_edges = detect_architecture(nodes, edges, repo_path, ollama_client)
        else:
            concept_nodes, concept_edges = extract_key_concepts(nodes, edges, ollama_client)
            relationship_edges = infer_semantic_relationships(nodes + concept_nodes, edges, ollama_client)
            architecture_nodes, architecture_edges = detect_architecture(nodes, edges, repo_path, ollama_client)
        new_nodes = concept_nodes + architecture_nodes
        new_edges = concept_edges + relationship_edges + architecture_edges
    else:
        # No enhancement
        return nodes, edges

    # Combine original and new nodes/edges
    all_nodes = nodes + new_nodes
    all_edges = edges + new_edges

    logger.info(f"Added {len(new_nodes)} semantic nodes and {len(new_edges)} semantic edges")
    return all_nodes, all_edges


def _extract_json_from_llm_response(response: str) -> Dict[str, Any]:
    """Extract and parse JSON from LLM response text.

    This function handles various ways LLMs might format JSON in their responses,
    including with markdown code blocks, irregular whitespace, and other common issues.

    Args:
        response: The raw text response from an LLM.

    Returns:
        Parsed JSON as a Python dictionary.

    Raises:
        ValueError: If JSON could not be extracted and parsed.
    """
    import json

    # First, remove any thinking section if present
    response = re.sub(r'<think>[\s\S]*?</think>', '', response)

    # Try different patterns to extract JSON
    patterns = [
        # JSON with code fence
        r'```(?:json)?\s*([\s\S]*?)\s*```',
        # JSON with XML/HTML-like tags
        r'<json>([\s\S]*?)</json>',
        # Just extract anything that looks like JSON
        r'(\{[\s\S]*\})',
        # Array responses
        r'(\[[\s\S]*\])'
    ]

    extracted_text = None

    # Try each pattern
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            extracted_text = match.group(1).strip()
            break

    # If no pattern matched, use the entire response
    if not extracted_text:
        extracted_text = response.strip()

    # Remove any non-JSON text before or after the structure
    # First, try to find the first '{' or '['
    start_idx = min(
        (extracted_text.find('{') if extracted_text.find('{') != -1 else len(extracted_text)),
        (extracted_text.find('[') if extracted_text.find('[') != -1 else len(extracted_text))
    )

    if start_idx < len(extracted_text):
        extracted_text = extracted_text[start_idx:]

    # Find last '}' or ']'
    end_idx = max(extracted_text.rfind('}'), extracted_text.rfind(']'))
    if end_idx != -1:
        extracted_text = extracted_text[:end_idx+1]

    # Attempt to parse the extracted JSON
    try:
        parsed_json = json.loads(extracted_text)
        return parsed_json
    except json.JSONDecodeError as e:
        logger.debug(f"Initial JSON parsing failed: {e}. Attempting to fix...")

        # If parsing fails, try to fix common JSON formatting issues
        # Replace single quotes with double quotes
        fixed_text = extracted_text.replace("'", "\"")

        # Fix unquoted keys
        fixed_text = re.sub(r'(\s*?)(\w+)(\s*?):', r'\1"\2"\3:', fixed_text)

        # Fix missing commas between objects in arrays
        fixed_text = re.sub(r'(\})\s*(\{)', r'\1,\2', fixed_text)

        # Fix missing commas between array elements
        fixed_text = re.sub(r'(\])\s*(\[)', r'\1,\2', fixed_text)

        # Fix trailing commas in arrays and objects
        fixed_text = re.sub(r',\s*\}', r'}', fixed_text)
        fixed_text = re.sub(r',\s*\]', r']', fixed_text)

        # Fix missing commas after values in objects
        # This pattern looks for cases where a value is followed directly by a key without a comma
        fixed_text = re.sub(r'("[^"]*?")\s*("[^"]*?"\s*:)', r'\1,\2', fixed_text)
        fixed_text = re.sub(r'(true|false|null|\d+)\s*("[^"]*?"\s*:)', r'\1,\2', fixed_text)

        # Try to parse again
        try:
            parsed_json = json.loads(fixed_text)
            logger.info("Successfully parsed JSON after applying fixes")
            return parsed_json
        except json.JSONDecodeError as e2:
            logger.debug(f"JSON parsing still failed after fixes: {e2}. Trying more aggressive fixes...")

            # If still failing, try more aggressive fixes
            try:
                # Try to fix the specific comma delimiter issues mentioned in the error
                if "Expecting ',' delimiter" in str(e2):
                    error_parts = str(e2).split(":")
                    if len(error_parts) >= 3:
                        # Extract line and column information
                        line_col_info = error_parts[2].strip()
                        line_col_match = re.search(r'line (\d+) column (\d+)', line_col_info)
                        if line_col_match:
                            line = int(line_col_match.group(1))
                            column = int(line_col_match.group(2))

                            # Split the text into lines
                            lines = fixed_text.split('\n')
                            if 0 < line <= len(lines):
                                # Insert a comma at the problematic position
                                problem_line = lines[line-1]
                                if 0 < column <= len(problem_line):
                                    # Check if this is a common pattern where a comma is missing between key-value pairs
                                    # This specifically targets the pattern where column 22 is often the issue
                                    # (which is right after the "confidence" value in the JSON structure)
                                    if column == 22:
                                        # This is likely the pattern we're seeing in the errors
                                        if '"confidence": 0' in problem_line:
                                            fixed_line = problem_line.replace('"confidence": 0', '"confidence": 0,')
                                            lines[line-1] = fixed_line
                                            logger.debug(f"Fixed missing comma after confidence value at line {line}")
                                        elif '"confidence": ' in problem_line:
                                            # More general case for any confidence value
                                            fixed_line = re.sub(r'("confidence": \d+(?:\.\d+)?)\s+', r'\1, ', problem_line)
                                            lines[line-1] = fixed_line
                                            logger.debug(f"Fixed missing comma after confidence value at line {line}")
                                        else:
                                            # General case for column 22 - insert a comma
                                            fixed_line = problem_line[:column-1] + ',' + problem_line[column-1:]
                                            lines[line-1] = fixed_line
                                            logger.debug(f"Inserted comma at line {line}, column {column}")
                                    else:
                                        # General case - insert a comma at the problematic position
                                        fixed_line = problem_line[:column-1] + ',' + problem_line[column-1:]
                                        lines[line-1] = fixed_line
                                        logger.debug(f"Inserted comma at line {line}, column {column}")

                                    fixed_text = '\n'.join(lines)

                # Additional fix for common pattern in o4-mini responses
                # Look for missing commas after confidence values (a common issue in the JSON responses)
                fixed_text = re.sub(r'("confidence": \d+\.\d+)\s+(")', r'\1,\2', fixed_text)
                fixed_text = re.sub(r'("confidence": \d+)\s+(")', r'\1,\2', fixed_text)

                # More aggressive fix for all numeric values followed by a key
                fixed_text = re.sub(r'(\d+(?:\.\d+)?)\s+(")', r'\1,\2', fixed_text)

                # Handle the specific case of column 200 error (seen in adr:adr-006-blast-radius-prediction.md)
                if "column 200" in str(e2) or "line 1 column 200" in str(e2):
                    # This is likely a long line with missing comma
                    # Try to find a pattern of a value followed by a key without a comma
                    fixed_text = re.sub(r'(\d+|true|false|null|"[^"]*?")\s+("[^"]*?":\s*)', r'\1,\2', fixed_text)

                    # For line 1 column 200 specifically, try a more aggressive approach
                    # Split the text into chunks and insert commas between them
                    if "line 1 column 200" in str(e2):
                        logger.debug("Applying special fix for line 1 column 200 error")
                        # If it's a single line, try to insert a comma at position 199
                        lines = fixed_text.split('\n')
                        if len(lines) >= 1 and len(lines[0]) > 199:
                            # Insert a comma at position 199
                            lines[0] = lines[0][:199] + ',' + lines[0][199:]
                            fixed_text = '\n'.join(lines)
                            logger.debug("Inserted comma at position 199 in line 1")

                # Try to parse with the more aggressively fixed text
                parsed_json = json.loads(fixed_text)
                logger.info("Successfully parsed JSON after applying aggressive fixes")
                return parsed_json
            except json.JSONDecodeError:
                # If still failing, try a more lenient approach with json5
                try:
                    import json5
                    parsed_json = json5.loads(fixed_text)
                    logger.info("Successfully parsed JSON using json5")
                    return parsed_json
                except (ImportError, Exception) as e3:
                    # If all parsing attempts fail, log the error and raise ValueError
                    logger.error(f"Failed to parse JSON from LLM response: {e}")
                    logger.debug(f"Original text: {extracted_text[:100]}...")
                    logger.debug(f"Fixed text: {fixed_text[:100]}...")
                    raise ValueError(f"Failed to parse JSON from LLM response: {e}")


def extract_key_concepts(
    nodes: List[Node],
    edges: List[Edge],
    ollama_client: OllamaClient,
    llm_model: Optional[str] = None,
) -> Tuple[List[Node], List[Edge]]:
    """Extract key concepts from node content using Ollama.

    Args:
        nodes: List of nodes to analyze.
        edges: List of edges between nodes.
        ollama_client: Ollama client for LLM processing.
        llm_model: Optional model name to use with Ollama.

    Returns:
        New concept nodes and edges.
    """
    logger.info("Extracting key concepts from node content using Ollama")

    # Collect text content from nodes
    text_content = []
    for node in nodes:
        if node.title:
            text_content.append(node.title)
        if node.body:
            text_content.append(node.body)

    # Skip if no content to analyze
    if not text_content:
        return [], []

    # Combine text content (limit to avoid token limits)
    combined_text = "\n".join(text_content)
    if len(combined_text) > 10000:
        combined_text = combined_text[:10000]

    # Create prompt for concept extraction
    prompt = f"""
    Analyze the following text and extract key domain concepts.
    For each concept, provide:
    1. A name (1-3 words)
    2. A clear definition (1-2 sentences)
    3. Related terms or concepts

    Format your response as JSON with the following structure:
    {{
        "concepts": [
            {{
                "name": "concept_name",
                "definition": "concept_definition",
                "related_terms": ["term1", "term2"]
            }}
        ]
    }}

    Here's the text to analyze:
    ```
    {combined_text}
    ```

    Return ONLY the JSON object, nothing else.
    """

    try:
        # Generate response from LLM
        model_to_use = llm_model or "qwen3:4b"
        response = ollama_client.generate(
            model=model_to_use,
            prompt=prompt,
            options={"temperature": 0.2}
        )

        # Extract and parse JSON using our robust function
        try:
            data = _extract_json_from_llm_response(response)
        except ValueError:
            # If parsing fails, create a minimal default structure
            logger.warning("Falling back to minimal default structure due to JSON parsing error")
            data = {"concepts": []}

        # Create concept nodes and edges
        return _create_concept_nodes_and_edges(data, nodes)

    except Exception as e:
        logger.error(f"Error extracting concepts with Ollama: {e}")
        return [], []


def extract_key_concepts_openai(
    nodes: List[Node],
    edges: List[Edge],
    openai_client: Any,
    llm_model: Optional[str] = None,
) -> Tuple[List[Node], List[Edge]]:
    """Extract key concepts from node content using OpenAI.

    Args:
        nodes: List of nodes to analyze.
        edges: List of edges between nodes.
        openai_client: OpenAI client for LLM processing.
        llm_model: Optional model name to use with OpenAI.

    Returns:
        New concept nodes and edges.
    """
    logger.info("Extracting key concepts from node content using OpenAI")

    # Collect text content from nodes
    text_content = []
    for node in nodes:
        if node.title:
            text_content.append(node.title)
        if node.body:
            text_content.append(node.body)

    # Skip if no content to analyze
    if not text_content:
        return [], []

    # Combine text content (limit to avoid token limits)
    combined_text = "\n".join(text_content)
    if len(combined_text) > 10000:
        combined_text = combined_text[:10000]

    # Create prompt for concept extraction
    prompt = f"""
    Analyze the following text and extract key domain concepts.
    For each concept, provide:
    1. A name (1-3 words)
    2. A clear definition (1-2 sentences)
    3. Related terms or concepts

    Format your response as JSON with the following structure:
    {{
        "concepts": [
            {{
                "name": "concept_name",
                "definition": "concept_definition",
                "related_terms": ["term1", "term2"]
            }}
        ]
    }}

    Here's the text to analyze:
    ```
    {combined_text}
    ```

    Return ONLY the JSON object, nothing else.
    """

    try:
        # Generate response from OpenAI
        model_to_use = llm_model or "gpt-4.1"
        response = openai_client.generate(
            model=model_to_use,
            prompt=prompt,
            options={"temperature": 0.2}
        )

        # Extract and parse JSON using our robust function
        try:
            data = _extract_json_from_llm_response(response)
        except ValueError:
            # If parsing fails, create a minimal default structure
            logger.warning("Falling back to minimal default structure due to JSON parsing error")
            data = {"concepts": []}

        # Create concept nodes and edges
        return _create_concept_nodes_and_edges(data, nodes)

    except Exception as e:
        logger.error(f"Error extracting concepts with OpenAI: {e}")
        return [], []


def _create_concept_nodes_and_edges(data: Dict[str, Any], nodes: List[Node]) -> Tuple[List[Node], List[Edge]]:
    """Create concept nodes and edges from extracted data.

    Args:
        data: Extracted concept data.
        nodes: List of nodes to analyze.

    Returns:
        New concept nodes and edges.
    """
    concept_nodes = []
    concept_edges = []

    for concept_data in data.get("concepts", []):
        # Create concept node
        concept_name = concept_data.get("name", "Unknown Concept")
        concept_id = f"concept:{concept_name.lower().replace(' ', '_')}"

        concept_node = ConceptNode(
            id=concept_id,
            type=NodeType.CONCEPT,
            title=concept_name,
            name=concept_name,
            definition=concept_data.get("definition", ""),
            related_terms=concept_data.get("related_terms", []),
        )
        concept_nodes.append(concept_node)

        # Create edges to related nodes
        for node in nodes:
            # Check if concept is mentioned in node title or body
            if (node.title and concept_name.lower() in node.title.lower()) or \
               (node.body and concept_name.lower() in node.body.lower()):
                # Create edge from node to concept
                edge = Edge(
                    src=node.id,
                    dst=concept_id,
                    rel=EdgeRel.MENTIONS,
                    properties={"confidence": 0.8},
                )
                concept_edges.append(edge)

    logger.info(f"Extracted {len(concept_nodes)} concept nodes")
    return concept_nodes, concept_edges


def infer_semantic_relationships(
    nodes: List[Node],
    edges: List[Edge],
    ollama_client: OllamaClient,
    llm_model: Optional[str] = None,
) -> List[Edge]:
    """Infer semantic relationships between nodes.

    Args:
        nodes: List of nodes to analyze.
        edges: Existing edges between nodes.
        ollama_client: Ollama client for LLM processing.
        llm_model: Optional model name to use with Ollama.

    Returns:
        New inferred edges.
    """
    logger.info("Inferring semantic relationships between nodes")

    # This is a placeholder implementation
    # In a real implementation, we would use the LLM to infer relationships
    # between nodes based on their content

    # For now, return an empty list
    return []


def detect_architecture(
    nodes: List[Node],
    edges: List[Edge],
    repo_path: Optional[Path],
    ollama_client: OllamaClient,
    llm_model: Optional[str] = None,
) -> Tuple[List[Node], List[Edge]]:
    """Detect architectural patterns in the codebase.

    Args:
        nodes: List of nodes to analyze.
        edges: Existing edges between nodes.
        repo_path: Path to the repository.
        ollama_client: Ollama client for LLM processing.
        llm_model: Optional model name to use with Ollama.

    Returns:
        New architecture nodes and edges.
    """
    logger.info("Detecting architectural patterns")

    # This is a placeholder implementation
    # In a real implementation, we would analyze the codebase structure
    # to detect architectural patterns

    # For now, return empty lists
    return [], []
