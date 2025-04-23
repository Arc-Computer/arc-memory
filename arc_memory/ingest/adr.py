"""ADR ingestion for Arc Memory."""

import glob
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from markdown_it import MarkdownIt

from arc_memory.errors import ADRParseError, IngestError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import ADRNode, Edge, EdgeRel, NodeType

logger = get_logger(__name__)


def parse_adr_frontmatter(content: str) -> Dict[str, Any]:
    """Parse frontmatter from an ADR file.

    Args:
        content: The content of the ADR file.

    Returns:
        A dictionary of frontmatter values.

    Raises:
        ADRParseError: If the frontmatter couldn't be parsed.
    """
    # Try to extract YAML frontmatter between --- markers
    frontmatter_match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if frontmatter_match:
        try:
            return yaml.safe_load(frontmatter_match.group(1))
        except Exception as e:
            logger.error(f"Failed to parse YAML frontmatter: {e}")
            raise ADRParseError(f"Failed to parse YAML frontmatter: {e}")

    # Try to extract frontmatter from > blockquotes at the beginning
    blockquote_lines = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith(">"):
            blockquote_lines.append(line[1:].strip())
        elif not line and blockquote_lines:
            # Empty line after blockquotes
            continue
        elif blockquote_lines:
            # End of blockquotes
            break

    if blockquote_lines:
        frontmatter = {}
        for line in blockquote_lines:
            # Look for key-value pairs like "**Key** Value"
            key_value_match = re.search(r"\*\*(.*?)\*\*\s*(.*)", line)
            if key_value_match:
                key = key_value_match.group(1).lower().replace(" ", "_")
                value = key_value_match.group(2).strip()
                frontmatter[key] = value
            elif ":" in line:
                # Look for key-value pairs like "Key: Value"
                key, value = line.split(":", 1)
                key = key.lower().replace(" ", "_")
                frontmatter[key] = value.strip()
        return frontmatter

    # No frontmatter found
    logger.warning("No frontmatter found in ADR")
    return {}


def parse_adr_title(content: str) -> str:
    """Parse the title from an ADR file.

    Args:
        content: The content of the ADR file.

    Returns:
        The title of the ADR.
    """
    # Look for the first heading
    heading_match = re.search(r"^#\s+(.*?)$", content, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()

    # Fall back to the filename
    return "Untitled ADR"


def ingest_adrs(
    repo_path: Path,
    glob_pattern: str = "**/adr/**/*.md",
    last_processed: Optional[Dict[str, Any]] = None,
) -> Tuple[List[ADRNode], List[Edge], Dict[str, Any]]:
    """Ingest ADRs from a repository.

    Args:
        repo_path: Path to the repository.
        glob_pattern: Glob pattern to find ADR files.
        last_processed: Metadata from the last build for incremental processing.

    Returns:
        A tuple of (nodes, edges, metadata).

    Raises:
        IngestError: If there's an error during ingestion.
    """
    logger.info(f"Ingesting ADRs from {repo_path} with pattern {glob_pattern}")
    if last_processed:
        logger.info("Performing incremental build")

    try:
        # Find ADR files
        adr_files = glob.glob(str(repo_path / glob_pattern), recursive=True)
        logger.info(f"Found {len(adr_files)} ADR files")

        # Filter for incremental builds
        if last_processed and "files" in last_processed:
            last_processed_files = last_processed["files"]
            filtered_files = []
            for adr_file in adr_files:
                rel_path = os.path.relpath(adr_file, repo_path)
                if rel_path not in last_processed_files:
                    # New file
                    filtered_files.append(adr_file)
                else:
                    # Check if modified
                    mtime = os.path.getmtime(adr_file)
                    mtime_iso = datetime.fromtimestamp(mtime).isoformat()
                    if mtime_iso > last_processed_files[rel_path]:
                        filtered_files.append(adr_file)
            logger.info(f"Filtered to {len(filtered_files)} modified ADR files")
            adr_files = filtered_files

        # Process ADR files
        nodes = []
        edges = []
        processed_files = {}

        for adr_file in adr_files:
            rel_path = os.path.relpath(adr_file, repo_path)
            logger.info(f"Processing ADR: {rel_path}")

            try:
                # Read file
                with open(adr_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parse frontmatter
                frontmatter = parse_adr_frontmatter(content)

                # Parse title
                title = parse_adr_title(content)

                # Create ADR node
                adr_id = f"adr:{os.path.basename(adr_file)}"
                status = frontmatter.get("status", "Unknown")
                decision_makers = []
                if "decision_makers" in frontmatter:
                    if isinstance(frontmatter["decision_makers"], list):
                        decision_makers = frontmatter["decision_makers"]
                    else:
                        decision_makers = [frontmatter["decision_makers"]]

                created_at = datetime.now()
                if "date" in frontmatter:
                    try:
                        created_at = datetime.fromisoformat(frontmatter["date"])
                    except ValueError:
                        # Try other date formats
                        pass

                adr_node = ADRNode(
                    id=adr_id,
                    type=NodeType.ADR,
                    title=title,
                    body=content,
                    created_at=created_at,
                    status=status,
                    decision_makers=decision_makers,
                    path=rel_path,
                    extra=frontmatter,
                )
                nodes.append(adr_node)

                # Store file modification time
                mtime = os.path.getmtime(adr_file)
                processed_files[rel_path] = datetime.fromtimestamp(mtime).isoformat()

                # In a real implementation, we would:
                # 1. Parse the ADR to find mentioned files and commits
                # 2. Create DECIDES edges to those entities
                # For now, we'll just create a placeholder edge
                edge = Edge(
                    src=adr_id,
                    dst=f"file:{rel_path}",
                    rel=EdgeRel.DECIDES,
                )
                edges.append(edge)
            except ADRParseError as e:
                logger.error(f"Failed to parse ADR {rel_path}: {e}")
                # Continue with other ADRs
            except Exception as e:
                logger.error(f"Error processing ADR {rel_path}: {e}")
                # Continue with other ADRs

        # Create metadata
        metadata = {
            "adr_count": len(nodes),
            "timestamp": datetime.now().isoformat(),
            "files": processed_files,
        }

        logger.info(f"Processed {len(nodes)} ADR nodes and {len(edges)} edges")
        return nodes, edges, metadata
    except Exception as e:
        logger.exception("Unexpected error during ADR ingestion")
        raise IngestError(f"Failed to ingest ADRs: {e}")
