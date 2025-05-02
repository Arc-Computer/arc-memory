"""Causal graph utilities for Arc Memory simulation.

This module provides functions for building and manipulating causal graphs
from the knowledge graph, which are used to identify relationships between
services, files, and other entities in the codebase.
"""

import json
from typing import Dict, Any, List, Optional

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def build_causal_graph(db_path: str) -> Dict[str, Any]:
    """Build a causal graph from the knowledge graph.
    
    Args:
        db_path: Path to the knowledge graph database
        
    Returns:
        A dictionary representing the causal graph
    """
    logger.info(f"Building causal graph from knowledge graph at {db_path}")
    
    try:
        # Import here to avoid circular imports
        from arc_memory.sql.db import get_connection
        
        # Connect to the database
        conn = get_connection(db_path)
        
        # Get all file nodes
        cursor = conn.execute(
            """
            SELECT id, title, extra
            FROM nodes
            WHERE type = 'file'
            """
        )
        
        # Build a mapping of files to services
        file_to_services = {}
        service_to_files = {}
        
        # Process each file
        for row in cursor:
            file_id = row[0]
            file_path = row[1]
            
            # Skip if file_path is None
            if not file_path:
                continue
            
            # Extract the service name from the file path
            # This is a simple heuristic - in a real implementation,
            # we would use more sophisticated methods
            parts = file_path.split('/')
            if len(parts) > 1:
                service_name = parts[0]
                
                # Add to mappings
                if file_path not in file_to_services:
                    file_to_services[file_path] = []
                
                if service_name not in file_to_services[file_path]:
                    file_to_services[file_path].append(service_name)
                
                if service_name not in service_to_files:
                    service_to_files[service_name] = []
                
                if file_path not in service_to_files[service_name]:
                    service_to_files[service_name].append(file_path)
        
        # Get service dependencies from edges
        cursor = conn.execute(
            """
            SELECT src, dst, rel
            FROM edges
            WHERE rel = 'DEPENDS_ON'
            """
        )
        
        # Build a mapping of service dependencies
        service_dependencies = {}
        
        # Process each dependency
        for row in cursor:
            src = row[0]
            dst = row[1]
            
            # Extract service names
            src_service = src.split(':')[-1]
            dst_service = dst.split(':')[-1]
            
            # Add to mapping
            if src_service not in service_dependencies:
                service_dependencies[src_service] = []
            
            if dst_service not in service_dependencies[src_service]:
                service_dependencies[src_service].append(dst_service)
        
        # Build the causal graph
        causal_graph = {
            "file_to_services": file_to_services,
            "service_to_files": service_to_files,
            "service_dependencies": service_dependencies
        }
        
        logger.info(f"Built causal graph with {len(file_to_services)} files and {len(service_to_files)} services")
        return causal_graph
    except Exception as e:
        logger.error(f"Error building causal graph: {e}")
        
        # Return a minimal causal graph
        return {
            "file_to_services": {},
            "service_to_files": {},
            "service_dependencies": {}
        }
