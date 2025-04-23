#!/usr/bin/env python3
"""Test script for building the knowledge graph with GitHub App authentication."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from arc_memory.ingest.github import ingest_github
from arc_memory.logging_conf import configure_logging, get_logger

def main():
    """Test building the knowledge graph with GitHub App authentication."""
    configure_logging(debug=True)
    logger = get_logger(__name__)
    
    # Get repository path
    repo_path = Path.cwd()
    logger.info(f"Repository path: {repo_path}")
    
    # Ingest GitHub data
    logger.info("Ingesting GitHub data...")
    github_nodes, github_edges, github_metadata = ingest_github(
        repo_path=repo_path,
        token=None,  # This will trigger the GitHub App authentication flow
        last_processed=None,
    )
    
    # Print results
    logger.info(f"GitHub nodes: {len(github_nodes)}")
    logger.info(f"GitHub edges: {len(github_edges)}")
    logger.info(f"GitHub metadata: {github_metadata}")
    
    # Print some node details
    if github_nodes:
        logger.info("Sample nodes:")
        for node in github_nodes[:5]:
            logger.info(f"  {node.type}: {node.title}")

if __name__ == "__main__":
    main()
