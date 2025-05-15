"""Architecture extraction for Arc Memory.

This module provides functions for extracting architecture components from code entities.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    Edge,
    EdgeRel,
    Node,
    SystemNode,
    ServiceNode,
    ComponentNode,
    InterfaceNode,
)

logger = get_logger(__name__)


def extract_architecture(
    nodes: List[Node],
    edges: List[Edge],
    repo_path: Path,
    repo_id: Optional[str] = None
) -> Tuple[List[Node], List[Edge]]:
    """Extract architecture components from code entities.

    Args:
        nodes: Existing nodes in the knowledge graph.
        edges: Existing edges in the knowledge graph.
        repo_path: Path to the repository.
        repo_id: Optional repository ID. If None, a repository ID will be generated.

    Returns:
        A tuple of (new_nodes, new_edges) to be added to the knowledge graph.
    """
    logger.info(f"Extracting architecture components from {repo_path}")

    new_nodes = []
    new_edges = []

    try:
        # Create default system
        system_id = f"system:{repo_path.name}"
        system_node = SystemNode(
            id=system_id,
            title=repo_path.name,
            name=repo_path.name,
            description=f"System extracted from {repo_path.name}",
            repo_id=repo_id
        )
        new_nodes.append(system_node)

        # Find potential services (top-level directories)
        service_dirs = [d for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

        for service_dir in service_dirs:
            # Skip common non-service directories
            if service_dir.name in ['node_modules', 'venv', '.git', 'build', 'dist', '.github', '.vscode', '__pycache__']:
                continue

            # Create service node
            service_id = f"service:{service_dir.name}"
            service_node = ServiceNode(
                id=service_id,
                title=service_dir.name,
                name=service_dir.name,
                description=f"Service extracted from {service_dir.name} directory",
                system_id=system_id,
                repo_id=repo_id
            )
            new_nodes.append(service_node)

            # Create CONTAINS edge from system to service
            new_edges.append(Edge(
                src=system_id,
                dst=service_id,
                rel=EdgeRel.CONTAINS
            ))

            # Find components (subdirectories or modules)
            component_dirs = [d for d in service_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

            for component_dir in component_dirs:
                # Skip common non-component directories
                if component_dir.name in ['node_modules', 'venv', '.git', 'build', 'dist', '__pycache__']:
                    continue

                # Create component node
                component_id = f"component:{service_dir.name}/{component_dir.name}"
                component_node = ComponentNode(
                    id=component_id,
                    title=component_dir.name,
                    name=component_dir.name,
                    description=f"Component extracted from {component_dir.name} directory",
                    service_id=service_id,
                    repo_id=repo_id
                )
                new_nodes.append(component_node)

                # Create CONTAINS edge from service to component
                new_edges.append(Edge(
                    src=service_id,
                    dst=component_id,
                    rel=EdgeRel.CONTAINS
                ))

                # Find files in component
                files = []
                for root, _, filenames in os.walk(component_dir):
                    for filename in filenames:
                        if filename.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp', '.h', '.hpp')):
                            rel_path = os.path.relpath(os.path.join(root, filename), repo_path)
                            files.append(rel_path)

                # Update component with files
                component_node.files = files

                # Look for potential interfaces
                detect_interfaces(component_dir, component_id, service_id, repo_id, new_nodes, new_edges)

        logger.info(f"Extracted {len(new_nodes)} architecture nodes and {len(new_edges)} relationships")
        return new_nodes, new_edges
    except Exception as e:
        logger.error(f"Error extracting architecture: {e}")
        return [], []


def detect_interfaces(
    component_dir: Path,
    component_id: str,
    service_id: str,
    repo_id: Optional[str],
    nodes: List[Node],
    edges: List[Edge]
) -> None:
    """Detect interfaces in a component.

    Args:
        component_dir: Path to the component directory.
        component_id: ID of the component.
        service_id: ID of the parent service.
        repo_id: Optional repository ID.
        nodes: List of nodes to append to.
        edges: List of edges to append to.
    """
    # Look for common interface patterns
    interface_patterns = {
        'api': ['api.py', 'api.js', 'api.ts', 'routes.py', 'routes.js', 'routes.ts', 'endpoints.py', 'endpoints.js', 'endpoints.ts'],
        'event': ['events.py', 'events.js', 'events.ts', 'pubsub.py', 'pubsub.js', 'pubsub.ts'],
        'interface': ['interface.py', 'interface.js', 'interface.ts', 'interfaces.py', 'interfaces.js', 'interfaces.ts'],
    }

    for interface_type, patterns in interface_patterns.items():
        for pattern in patterns:
            for file_path in component_dir.glob(f"**/{pattern}"):
                # Create interface node
                interface_id = f"interface:{component_dir.name}/{file_path.stem}"
                interface_node = InterfaceNode(
                    id=interface_id,
                    title=f"{file_path.stem} interface",
                    name=file_path.stem,
                    description=f"Interface extracted from {file_path.name}",
                    service_id=service_id,
                    interface_type=interface_type,
                    repo_id=repo_id
                )
                nodes.append(interface_node)

                # Create EXPOSES edge from component to interface
                edges.append(Edge(
                    src=component_id,
                    dst=interface_id,
                    rel=EdgeRel.EXPOSES
                ))
