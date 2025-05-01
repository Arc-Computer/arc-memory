"""Causal graph derivation for Arc Memory simulation.

This module provides functions for deriving a static causal graph from Arc's
Temporal Knowledge Graph.
"""

import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple

import networkx as nx

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import EdgeRel
from arc_memory.schema.models import NodeType
from arc_memory.sql.db import get_connection
from arc_memory.sql.db import get_edges_by_src
from arc_memory.sql.db import get_edges_by_dst
from arc_memory.sql.db import get_node_by_id
from arc_memory.sql.db import build_networkx_graph

logger = get_logger(__name__)


class CausalGraph:
    """A static causal graph derived from Arc's Temporal Knowledge Graph."""

    def __init__(self, graph: nx.DiGraph):
        """Initialize the causal graph.

        Args:
            graph: A NetworkX directed graph
        """
        self.graph = graph
        self.service_to_files = defaultdict(set)
        self.file_to_services = defaultdict(set)

    def map_file_to_service(self, file_path: str, service_name: str) -> None:
        """Map a file to a service.

        Args:
            file_path: The path to the file
            service_name: The name of the service
        """
        self.service_to_files[service_name].add(file_path)
        self.file_to_services[file_path].add(service_name)

    def get_services_for_file(self, file_path: str) -> Set[str]:
        """Get services associated with a file.

        Args:
            file_path: The path to the file

        Returns:
            A set of service names
        """
        return self.file_to_services.get(file_path, set())

    def get_files_for_service(self, service_name: str) -> Set[str]:
        """Get files associated with a service.

        Args:
            service_name: The name of the service

        Returns:
            A set of file paths
        """
        return self.service_to_files.get(service_name, set())

    def get_related_services(self, service_name: str) -> Set[str]:
        """Get services related to a service.

        Args:
            service_name: The name of the service

        Returns:
            A set of related service names
        """
        related_services = set()

        # Get files for this service
        files = self.get_files_for_service(service_name)

        # For each file, find other services that use it
        for file_path in files:
            for other_service in self.get_services_for_file(file_path):
                if other_service != service_name:
                    related_services.add(other_service)

        return related_services

    def get_impact_path(self, source_service: str, target_service: str) -> List[str]:
        """Get the impact path from one service to another.

        Args:
            source_service: The source service
            target_service: The target service

        Returns:
            A list of service names representing the path
        """
        try:
            # Create a service-level graph
            service_graph = nx.DiGraph()

            # Add services as nodes
            for service in self.service_to_files.keys():
                service_graph.add_node(service)

            # Add edges between related services
            for service in self.service_to_files.keys():
                for related_service in self.get_related_services(service):
                    service_graph.add_edge(service, related_service)

            # Find the shortest path
            if nx.has_path(service_graph, source_service, target_service):
                return nx.shortest_path(service_graph, source_service, target_service)
            else:
                return []
        except nx.NetworkXNoPath:
            return []

    def save_to_file(self, output_path: str) -> None:
        """Save the causal graph to a file.

        Args:
            output_path: The path to save the graph to
        """
        data = {
            "service_to_files": {k: list(v) for k, v in self.service_to_files.items()},
            "file_to_services": {k: list(v) for k, v in self.file_to_services.items()}
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_from_file(cls, input_path: str) -> 'CausalGraph':
        """Load a causal graph from a file.

        Args:
            input_path: The path to load the graph from

        Returns:
            A CausalGraph object
        """
        with open(input_path, 'r') as f:
            data = json.load(f)

        graph = nx.DiGraph()
        causal_graph = cls(graph)

        # Restore the mappings
        for service, files in data["service_to_files"].items():
            for file in files:
                causal_graph.map_file_to_service(file, service)

        return causal_graph


def derive_causal(db_path: str) -> CausalGraph:
    """Extract a Static Causal Graph (SCG) from Arc's Temporal Knowledge Graph.

    Args:
        db_path: Path to the knowledge graph database

    Returns:
        A CausalGraph object
    """
    logger.info(f"Deriving causal graph from {db_path}")

    try:
        # Check if the database file exists
        db_file = Path(db_path)
        if not db_file.exists():
            logger.warning(f"Database file not found: {db_path}")
            return CausalGraph(nx.DiGraph())

        # Connect to the database
        conn = get_connection(db_path)

        # Build a NetworkX graph from the database
        graph = build_networkx_graph(conn)

        # Create a causal graph
        causal_graph = CausalGraph(graph)

        # Map files to services based on commit patterns
        map_files_to_services(conn, causal_graph)

        # Map files to services based on directory structure
        map_files_to_services_by_directory(causal_graph)

        # Log some statistics
        logger.info(f"Causal graph derived with {len(causal_graph.service_to_files)} services and {len(causal_graph.file_to_services)} files")

        return causal_graph

    except Exception as e:
        logger.error(f"Error deriving causal graph: {e}")
        # Return an empty causal graph
        return CausalGraph(nx.DiGraph())


def map_files_to_services(conn: sqlite3.Connection, causal_graph: CausalGraph) -> None:
    """Map files to services based on commit patterns.

    Args:
        conn: A connection to the database
        causal_graph: The causal graph to update
    """
    try:
        # Get all file nodes - the path is stored in the extra JSON field
        cursor = conn.execute("SELECT id, extra FROM nodes WHERE type = 'file'")
        file_nodes = {}
        for row in cursor.fetchall():
            node_id = row[0]
            extra_json = row[1]
            if extra_json:
                try:
                    extra = json.loads(extra_json)
                    if 'path' in extra:
                        file_nodes[node_id] = extra['path']
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse extra JSON for node {node_id}")

        # If we didn't find any paths in the extra field, try the title field
        if not file_nodes:
            cursor = conn.execute("SELECT id, title FROM nodes WHERE type = 'file'")
            file_nodes = {row[0]: row[1] for row in cursor.fetchall()}
            logger.debug(f"Fallback to title field used. Found {len(file_nodes)} file nodes.")

        # Get all commit nodes
        cursor = conn.execute("SELECT id FROM nodes WHERE type = 'commit'")
        commit_ids = [row[0] for row in cursor.fetchall()]

        # For each commit, find the files it modifies
        commit_to_files = defaultdict(set)
        for commit_id in commit_ids:
            edges = get_edges_by_src(conn, commit_id, EdgeRel.MODIFIES)
            for edge in edges:
                dst_id = edge["dst"]
                if dst_id in file_nodes:
                    commit_to_files[commit_id].add(file_nodes[dst_id])

        # Group files that are frequently modified together
        file_groups = cluster_files_by_commits(commit_to_files)

        # Map each file group to a service
        for i, file_group in enumerate(file_groups):
            service_name = derive_service_name(file_group)
            for file_path in file_group:
                causal_graph.map_file_to_service(file_path, service_name)

    except Exception as e:
        logger.error(f"Error mapping files to services: {e}")


def cluster_files_by_commits(commit_to_files: Dict[str, Set[str]]) -> List[Set[str]]:
    """Cluster files that are frequently modified together.

    Args:
        commit_to_files: A mapping from commit IDs to sets of file paths

    Returns:
        A list of file groups (sets of file paths)
    """
    # Create a graph where files are nodes and edges represent co-occurrence in commits
    file_graph = nx.Graph()

    # Add all files as nodes
    all_files = set()
    for files in commit_to_files.values():
        all_files.update(files)

    for file in all_files:
        file_graph.add_node(file)

    # Add edges between files that are modified in the same commit
    for files in commit_to_files.values():
        files_list = list(files)
        for i in range(len(files_list)):
            for j in range(i + 1, len(files_list)):
                if file_graph.has_edge(files_list[i], files_list[j]):
                    # Increment weight if edge already exists
                    file_graph[files_list[i]][files_list[j]]['weight'] += 1
                else:
                    # Create new edge with weight 1
                    file_graph.add_edge(files_list[i], files_list[j], weight=1)

    # Find connected components (groups of files)
    file_groups = list(nx.connected_components(file_graph))

    return file_groups


def map_files_to_services_by_directory(causal_graph: CausalGraph) -> None:
    """Map files to services based on directory structure.

    Args:
        causal_graph: The causal graph to update
    """
    # Get all files
    all_files = set(causal_graph.file_to_services.keys())

    # Group files by directory
    dir_to_files = defaultdict(set)
    for file_path in all_files:
        directory = os.path.dirname(file_path)
        if directory:
            dir_to_files[directory].add(file_path)

    # Map each directory to a service
    for directory, files in dir_to_files.items():
        # Skip directories with too few files
        if len(files) < 3:
            continue

        service_name = derive_service_name_from_directory(directory)
        for file_path in files:
            # Only map if the file isn't already mapped to a service
            if not causal_graph.get_services_for_file(file_path):
                causal_graph.map_file_to_service(file_path, service_name)


def derive_service_name(file_group: Set[str]) -> str:
    """Derive a service name from a group of files.

    Args:
        file_group: A set of file paths

    Returns:
        A service name
    """
    # Try to find a common directory
    common_dirs = set()
    for file_path in file_group:
        directory = os.path.dirname(file_path)
        if directory:
            common_dirs.add(directory)

    if len(common_dirs) == 1:
        # If there's a single common directory, use it as the service name
        return f"{list(common_dirs)[0]}-service"

    # Try to find common prefixes in file names
    file_names = [os.path.basename(file_path) for file_path in file_group]
    common_prefix = os.path.commonprefix(file_names)
    if common_prefix and len(common_prefix) > 3:
        return f"{common_prefix.rstrip('_.-')}-service"

    # Try to infer from file extensions
    extensions = [os.path.splitext(file_path)[1].lower() for file_path in file_group if os.path.splitext(file_path)[1]]
    if extensions:
        # Count occurrences of each extension
        ext_counts = defaultdict(int)
        for ext in extensions:
            ext_counts[ext] += 1

        # Use the most common extension
        most_common_ext = max(ext_counts.items(), key=lambda x: x[1])[0]
        if most_common_ext:
            return f"{most_common_ext.lstrip('.')}-service"

    # Fallback: use a generic name with a hash of the file paths
    import hashlib
    hash_obj = hashlib.md5()
    for file_path in sorted(file_group):
        hash_obj.update(file_path.encode('utf-8'))
    return f"service-{hash_obj.hexdigest()[:8]}"


def derive_service_name_from_directory(directory: str) -> str:
    """Derive a service name from a directory path.

    Args:
        directory: A directory path

    Returns:
        A service name
    """
    # Use the last component of the directory path
    components = directory.split('/')
    if components:
        last_component = components[-1]
        if last_component:
            return f"{last_component}-service"

    # Fallback: use the full directory path
    return f"{directory.replace('/', '-')}-service"


def get_affected_services(causal_graph: CausalGraph, file_paths: List[str]) -> List[str]:
    """Get services affected by changes to the specified files.

    Args:
        causal_graph: The causal graph
        file_paths: A list of file paths

    Returns:
        A list of affected service names
    """
    affected_services = set()

    for file_path in file_paths:
        # Get services directly associated with this file
        services = causal_graph.get_services_for_file(file_path)
        affected_services.update(services)

        # If no services are directly associated, try to infer from directory
        if not services:
            directory = os.path.dirname(file_path)
            if directory:
                service_name = derive_service_name_from_directory(directory)
                affected_services.add(service_name)

    return list(affected_services)
