"""Semantic search module for Arc Memory.

This module provides functions to process natural language queries against
the knowledge graph, leveraging LLMs to understand the query intent and
extract relevant information from the graph.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from arc_memory.llm.ollama_client import OllamaClient, ensure_ollama_available
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Node, NodeType
from arc_memory.sql.db import get_connection
from arc_memory.trace import (
    format_trace_results,
    get_node_by_id,
    get_connected_nodes,
    trace_history_for_file_line,
)

logger = get_logger(__name__)

# System prompt for the LLM to process natural language queries
QUERY_SYSTEM_PROMPT = """You are a specialized AI assistant for the Arc Memory knowledge graph system.
Your task is to parse and understand natural language queries about a codebase and its development history.

The knowledge graph contains the following types of nodes:
- commit: Git commits with code changes
- pr: Pull requests that merge changes
- issue: GitHub issues or Linear tickets describing problems or features
- adr: Architecture Decision Records documenting major technical decisions
- file: Source code files in the repository

These nodes are connected by the following relationships:
- MODIFIES: Connects commits to the files they modify
- MERGES: Connects PRs to the commits they merge
- MENTIONS: Connects PRs or issues to other entities they reference
- DECIDES: Connects ADRs to the issues they resolve

Given a user's question, identify:
1. The primary entity types the user is asking about (commits, PRs, issues, ADRs, files)
2. Any temporal constraints (e.g., "last month", "before version 2.0")
3. Any specific attributes to filter on (e.g., author, status, title keywords)
4. The type of relationship or information the user wants to know

Format your response as valid JSON with the following structure:
{
  "understanding": "Brief explanation of what the user is asking in your own words",
  "entity_types": ["commit", "pr", ...],  // The node types to search for
  "temporal_constraints": {  // Optional temporal constraints
    "before": "YYYY-MM-DD",  // Optional date constraint (before)
    "after": "YYYY-MM-DD",   // Optional date constraint (after)
    "version": "x.y.z"       // Optional version constraint
  },
  "attributes": {  // Attributes to filter on, specific to each entity type
    "commit": {"author": "name"},
    "pr": {"status": "merged"},
    "issue": {"labels": ["bug", "feature"]},
    "title_keywords": ["authentication", "login"]
  },
  "relationship_focus": "MENTIONS"  // Optional specific relationship to focus on
}

Only include fields that are relevant to the query. If information is not specified or implied in the user's question, do not include it in the JSON response.
"""

def process_query(
    db_path: Path,
    query: str,
    max_results: int = 5,
    max_hops: int = 3
) -> Dict[str, Any]:
    """Process a natural language query against the knowledge graph.
    
    This function:
    1. Uses an LLM to understand the query intent
    2. Converts the intent into appropriate graph queries
    3. Retrieves and ranks relevant nodes
    4. Generates a natural language response with citations
    
    Args:
        db_path: Path to the knowledge graph database
        query: Natural language query text
        max_results: Maximum number of results to return
        max_hops: Maximum number of hops in the graph traversal
        
    Returns:
        A dictionary containing the query results with these keys:
        - understanding: How the system understood the query
        - summary: One-line summary of the answer
        - answer: Detailed answer text
        - results: List of relevant nodes with metadata
        - confidence: Confidence score (1-10)
    """
    try:
        # Ensure Ollama is available
        if not ensure_ollama_available():
            return {
                "error": "Ollama is not available. Please install it from https://ollama.ai"
            }
        
        # Connect to the database
        conn = get_connection(db_path)
        
        # Step 1: Process the query using LLM to understand intent
        query_intent = _process_query_intent(query)
        logger.debug(f"Query intent: {query_intent}")
        
        if not query_intent:
            return {
                "error": "Failed to process query intent",
                "understanding": "I couldn't understand your question. Please try rephrasing it."
            }
        
        # Step 2: Search for relevant nodes based on the query intent
        relevant_nodes = _search_knowledge_graph(
            conn,
            query_intent,
            max_results=max_results,
            max_hops=max_hops
        )
        
        if not relevant_nodes:
            return {
                "understanding": query_intent.get("understanding", "Query understood, but no results found"),
                "summary": "No relevant information found",
                "results": []
            }
        
        # Step 3: Generate a response using the LLM with the relevant nodes
        response = _generate_response(query, query_intent, relevant_nodes)
        
        # Close the database connection
        conn.close()
        
        # Return the complete response
        return response
        
    except Exception as e:
        logger.exception(f"Error processing query: {e}")
        return {
            "error": str(e),
            "understanding": "An error occurred while processing your query"
        }


def _process_query_intent(query: str) -> Optional[Dict[str, Any]]:
    """Process the query intent using an LLM.
    
    Args:
        query: The natural language query
        
    Returns:
        A dictionary with the parsed query intent, or None if processing failed
    """
    try:
        # Create Ollama client
        client = OllamaClient()
        
        # Generate response with thinking for better reasoning
        llm_response = client.generate_with_thinking(
            prompt=f"Parse this natural language query about a code repository: \"{query}\"",
            system=QUERY_SYSTEM_PROMPT
        )
        
        # Extract JSON from the response
        return _extract_json_from_llm_response(llm_response)
        
    except Exception as e:
        logger.exception(f"Error in query intent processing: {e}")
        return None


def _extract_json_from_llm_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM response text.
    
    Args:
        response: The raw LLM response text
        
    Returns:
        Parsed JSON object or None if extraction failed
    """
    try:
        # Check for JSON block format
        if "```json" in response:
            # Extract content between ```json and ```
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            # Extract content between ``` and ```
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()
        else:
            # Try to find JSON-like structure with braces
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end].strip()
            else:
                # No JSON-like structure found
                logger.warning(f"No JSON structure found in: {response}")
                return None
        
        # Parse the JSON
        return json.loads(json_str)
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}, response: {response}")
        
        # Fallback: Try regex to find JSON-like structure
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning(f"Regex fallback also failed to parse JSON")
                return None
        
        return None
    except Exception as e:
        logger.exception(f"Error extracting JSON: {e}")
        return None


def _search_knowledge_graph(
    conn: sqlite3.Connection,
    query_intent: Dict[str, Any],
    max_results: int = 5,
    max_hops: int = 3
) -> List[Dict[str, Any]]:
    """Search the knowledge graph based on the query intent.
    
    Args:
        conn: SQLite connection
        query_intent: The parsed query intent
        max_results: Maximum number of results to return
        max_hops: Maximum number of hops in the graph traversal
        
    Returns:
        List of relevant nodes with metadata
    """
    try:
        # Extract search parameters from query intent
        entity_types = query_intent.get("entity_types", [])
        attributes = query_intent.get("attributes", {})
        title_keywords = attributes.get("title_keywords", [])
        
        # Prepare SQL query parts
        conditions = []
        params = []
        
        # Filter by entity types if specified
        if entity_types:
            entity_types_str = ", ".join("?" for _ in entity_types)
            conditions.append(f"type IN ({entity_types_str})")
            params.extend(entity_types)
        
        # Filter by title keywords if specified
        if title_keywords:
            keyword_conditions = []
            for keyword in title_keywords:
                keyword_conditions.append("title LIKE ?")
                params.append(f"%{keyword}%")
            
            if keyword_conditions:
                conditions.append(f"({' OR '.join(keyword_conditions)})")
        
        # Handle entity-specific attributes
        for entity_type, attrs in attributes.items():
            if entity_type != "title_keywords" and isinstance(attrs, dict):
                for key, value in attrs.items():
                    if isinstance(value, list):
                        # For list values, check if any item is in the JSON field
                        for item in value:
                            conditions.append(f"(type = ? AND extra LIKE ?)")
                            params.extend([entity_type, f"%\"{key}\"%{item}%"])
                    else:
                        # For scalar values, check exact match in the JSON field
                        conditions.append(f"(type = ? AND extra LIKE ?)")
                        params.extend([entity_type, f"%\"{key}\":\"{value}\"%"])
        
        # Build the final SQL query
        sql = "SELECT id, type, title, body, extra FROM nodes"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        # Add ordering and limit
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(max_results * 2)  # Get more than needed for relevance filtering
        
        # Execute the query
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # Convert rows to Node objects
        nodes = []
        for row in rows:
            id_val, type_val, title, body, extra_json = row
            
            # Parse node type
            node_type = NodeType(type_val) if type_val in [e.value for e in NodeType] else None
            
            # Parse extra JSON
            try:
                extra = json.loads(extra_json) if extra_json else {}
            except json.JSONDecodeError:
                extra = {}
            
            # Create and add the node
            node = Node(
                id=id_val,
                type=node_type,
                title=title,
                body=body,
                extra=extra
            )
            nodes.append(node)
        
        # If we didn't find enough direct matches, expand the search using graph relationships
        if len(nodes) < max_results and max_hops > 0:
            expanded_nodes = _expand_search(conn, nodes, max_hops, max_results)
            nodes.extend(expanded_nodes)
        
        # Score and rank nodes by relevance to the query
        scored_nodes = _score_nodes(nodes, query_intent)
        
        # Limit to max_results
        top_nodes = scored_nodes[:max_results]
        
        # Format the results
        formatted_results = format_trace_results(top_nodes)
        
        # Add relevance scores to the formatted results
        for i, result in enumerate(formatted_results):
            result["relevance"] = 10 - i  # Simple relevance scoring, 10 being most relevant
        
        return formatted_results
        
    except Exception as e:
        logger.exception(f"Error searching knowledge graph: {e}")
        return []


def _expand_search(
    conn: sqlite3.Connection,
    seed_nodes: List[Node],
    max_hops: int,
    max_results: int
) -> List[Node]:
    """Expand the search from seed nodes using graph relationships.
    
    Args:
        conn: SQLite connection
        seed_nodes: Initial set of nodes to expand from
        max_hops: Maximum number of hops in the graph traversal
        max_results: Maximum number of results to return
        
    Returns:
        List of additional nodes found through graph traversal
    """
    try:
        # Keep track of visited nodes to avoid duplicates
        visited_ids = set(node.id for node in seed_nodes)
        expanded_nodes = []
        
        # Queue for BFS traversal
        from collections import deque
        queue = deque([(node.id, 1) for node in seed_nodes])  # (node_id, hop_count)
        
        # Perform BFS traversal
        while queue and len(expanded_nodes) < max_results:
            node_id, hop_count = queue.popleft()
            
            # Skip if max hops reached
            if hop_count > max_hops:
                continue
            
            # Get connected nodes
            connected_ids = get_connected_nodes(conn, node_id)
            
            # Process each connected node
            for connected_id in connected_ids:
                if connected_id not in visited_ids:
                    visited_ids.add(connected_id)
                    
                    # Get the node from the database
                    node = get_node_by_id(conn, connected_id)
                    if node:
                        expanded_nodes.append(node)
                        
                        # Add to queue for further expansion
                        if hop_count < max_hops:
                            queue.append((connected_id, hop_count + 1))
                    
                    # Check if we have enough nodes
                    if len(expanded_nodes) >= max_results:
                        break
        
        return expanded_nodes
        
    except Exception as e:
        logger.exception(f"Error expanding search: {e}")
        return []


def _score_nodes(nodes: List[Node], query_intent: Dict[str, Any]) -> List[Node]:
    """Score and rank nodes by relevance to the query.
    
    Args:
        nodes: List of nodes to score
        query_intent: The parsed query intent
        
    Returns:
        List of nodes sorted by relevance score (most relevant first)
    """
    try:
        scored_nodes = []
        
        # Extract scoring criteria from query intent
        entity_types = query_intent.get("entity_types", [])
        title_keywords = query_intent.get("attributes", {}).get("title_keywords", [])
        temporal_constraints = query_intent.get("temporal_constraints", {})
        
        for node in nodes:
            score = 0
            
            # Score based on entity type
            if entity_types and node.type and node.type.value in entity_types:
                score += 5
            
            # Score based on title keywords
            if title_keywords and node.title:
                for keyword in title_keywords:
                    if keyword.lower() in node.title.lower():
                        score += 3
            
            # Score based on temporal constraints
            if temporal_constraints and node.ts:
                # Handle "after" constraint
                if "after" in temporal_constraints:
                    after_date = datetime.fromisoformat(temporal_constraints["after"])
                    if node.ts > after_date:
                        score += 2
                
                # Handle "before" constraint
                if "before" in temporal_constraints:
                    before_date = datetime.fromisoformat(temporal_constraints["before"])
                    if node.ts < before_date:
                        score += 2
                
                # Handle version constraint (for commits and PRs)
                if "version" in temporal_constraints and node.type in [NodeType.COMMIT, NodeType.PR]:
                    # Check if version is mentioned in title or body
                    version = temporal_constraints["version"]
                    if (node.title and version in node.title) or (node.body and version in node.body):
                        score += 4
            
            # Add to scored nodes list
            scored_nodes.append((node, score))
        
        # Sort by score (descending) and return just the nodes
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in scored_nodes]
        
    except Exception as e:
        logger.exception(f"Error scoring nodes: {e}")
        return nodes  # Return unsorted nodes on error


def _generate_response(
    query: str,
    query_intent: Dict[str, Any],
    relevant_nodes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate a natural language response to the query.
    
    Args:
        query: The original natural language query
        query_intent: The parsed query intent
        relevant_nodes: List of relevant nodes with metadata
        
    Returns:
        A dictionary with the response including summary, answer, and results
    """
    try:
        # Create Ollama client
        client = OllamaClient()
        
        # Prepare context from relevant nodes
        context_str = json.dumps(relevant_nodes, indent=2)
        
        # Define the system prompt for response generation
        system_prompt = """You are an expert AI assistant for Arc Memory, a knowledge graph for code repositories.
Given a user's question and a set of relevant graph nodes, create a comprehensive, accurate answer.

Your response should include:
1. A brief summary (1-2 sentences)
2. A detailed answer that synthesizes information from the provided nodes
3. Clear reasoning that connects the evidence to your answer
4. A confidence score (1-10) indicating how well the available information answers the question

Format your response as valid JSON with the following structure:
{
  "summary": "One-line summary of the answer",
  "answer": "Detailed response to the question",
  "reasoning": "Explanation of how you arrived at this answer",
  "confidence": 7  // Score from 1-10
}

Base your response ONLY on the provided context and be honest about limitations in the available information.
"""
        
        # Generate the response with the LLM
        llm_prompt = f"""User's question: {query}

Query understanding: {query_intent.get('understanding', 'Not available')}

Relevant information from the knowledge graph:
{context_str}

Based on this information, please answer the user's question."""
        
        # Generate response with thinking for better reasoning
        llm_response = client.generate_with_thinking(
            prompt=llm_prompt,
            system=system_prompt
        )
        
        # Extract JSON from the response
        response_json = _extract_json_from_llm_response(llm_response)
        
        if not response_json:
            # Fallback for parsing errors
            return {
                "understanding": query_intent.get("understanding", "Query understood, but response processing failed"),
                "summary": "Unable to generate a structured response",
                "answer": "I encountered an error while processing the information from the knowledge graph.",
                "results": relevant_nodes,
                "confidence": 1
            }
        
        # Combine the response with the original query understanding and relevant nodes
        final_response = {
            "understanding": query_intent.get("understanding", "Not available"),
            "summary": response_json.get("summary", "No summary available"),
            "answer": response_json.get("answer", "No detailed answer available"),
            "results": relevant_nodes,
            "confidence": response_json.get("confidence", 5)
        }
        
        # Add reasoning to each result if available
        if "reasoning" in response_json:
            # Add overall reasoning to the response
            final_response["reasoning"] = response_json["reasoning"]
            
            # Distribute reasoning to individual results
            # For now, add the same reasoning to the first result
            if relevant_nodes:
                relevant_nodes[0]["reasoning"] = response_json["reasoning"]
        
        return final_response
        
    except Exception as e:
        logger.exception(f"Error generating response: {e}")
        return {
            "understanding": query_intent.get("understanding", "Query understood, but response generation failed"),
            "summary": "Error generating response",
            "answer": f"An error occurred while generating the response: {e}",
            "results": relevant_nodes,
            "confidence": 1
        } 