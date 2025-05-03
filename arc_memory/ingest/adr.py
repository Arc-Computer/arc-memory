"""ADR ingestion for Arc Memory."""

import glob
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from markdown_it import MarkdownIt

from arc_memory.errors import ADRParseError, IngestError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import ADRNode, Edge, EdgeRel, NodeType


def parse_adr_date(date_value: Any, adr_file: Path) -> Optional[datetime]:
    """Parse a date value from an ADR frontmatter.

    This function attempts to parse a date value using multiple formats
    and provides detailed error messages when parsing fails.

    Args:
        date_value: The date value to parse (string, date, datetime, etc.)
        adr_file: The path to the ADR file (for error reporting)

    Returns:
        A datetime object if parsing succeeds, None otherwise.
    """
    logger = get_logger(__name__)

    if date_value is None:
        logger.warning(
            f"Missing date in ADR: {adr_file}. "
            f"Add a 'date: YYYY-MM-DD' field to the frontmatter."
        )
        return None

    # Handle datetime objects directly
    if isinstance(date_value, datetime):
        return date_value

    # Handle date objects
    if hasattr(date_value, 'year') and hasattr(date_value, 'month') and hasattr(date_value, 'day'):
        try:
            return datetime(date_value.year, date_value.month, date_value.day)
        except (ValueError, AttributeError):
            pass

    # Convert to string if not already
    if not isinstance(date_value, str):
        # If it's a date-like object (like a YAML date), try to convert it
        if hasattr(date_value, 'year') and hasattr(date_value, 'month') and hasattr(date_value, 'day'):
            try:
                # Convert to datetime
                return datetime(date_value.year, date_value.month, date_value.day)
            except (ValueError, AttributeError):
                pass

        # Try to convert to string
        try:
            date_str = str(date_value)
            logger.info(
                f"Converting non-string date '{date_value}' to string '{date_str}' in ADR: {adr_file}"
            )
            # Continue processing with the string version
        except Exception:
            logger.warning(
                f"Could not parse date '{date_value}' in ADR: {adr_file}. "
                f"Date value is not a string and cannot be converted. "
                f"Use format 'YYYY-MM-DD' in the frontmatter."
            )
            return None
    else:
        date_str = date_value

    # Ensure we're working with a trimmed string
    date_str = date_str.strip()

    # Try different date formats
    date_formats = [
        ("%Y-%m-%d", "YYYY-MM-DD (e.g., 2023-11-15)"),
        ("%Y-%m-%dT%H:%M:%S", "YYYY-MM-DDThh:mm:ss (e.g., 2023-11-15T14:30:00)"),
        ("%Y-%m-%dT%H:%M:%S.%f", "YYYY-MM-DDThh:mm:ss.fff (e.g., 2023-11-15T14:30:00.123)"),
        ("%Y/%m/%d", "YYYY/MM/DD (e.g., 2023/11/15)"),
        ("%d-%m-%Y", "DD-MM-YYYY (e.g., 15-11-2023)"),
        ("%d/%m/%Y", "DD/MM/YYYY (e.g., 15/11/2023)"),
        ("%B %d, %Y", "Month DD, YYYY (e.g., November 15, 2023)"),
        ("%b %d, %Y", "Mon DD, YYYY (e.g., Nov 15, 2023)"),
    ]

    for date_format, format_desc in date_formats:
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            continue

    # If all formats fail, try fromisoformat as a last resort
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        # Collect all supported formats for the error message
        supported_formats = "\n".join([f"- {desc}" for _, desc in date_formats])
        logger.warning(
            f"Could not parse date '{date_str}' in ADR: {adr_file}. "
            f"Supported date formats are:\n{supported_formats}\n"
            f"Using current time as fallback."
        )
        return None

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


class ADRIngestor:
    """Ingestor plugin for Architectural Decision Records (ADRs)."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "adr"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [NodeType.ADR]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.DECIDES]

    def ingest(
        self,
        repo_path: Path,
        glob_pattern: str = "**/adr-*.md",
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

                    ts = datetime.now()
                    if "date" in frontmatter:
                        date_str = frontmatter["date"]
                        parsed_date = parse_adr_date(date_str, adr_file)
                        if parsed_date:
                            ts = parsed_date

                    adr_node = ADRNode(
                        id=adr_id,
                        type=NodeType.ADR,
                        title=title,
                        body=content,
                        ts=ts,
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


# For backward compatibility
def ingest_adrs(
    repo_path: Path,
    glob_pattern: str = "**/adr/**/*.md",
    last_processed: Optional[Dict[str, Any]] = None,
) -> Tuple[List[ADRNode], List[Edge], Dict[str, Any]]:
    """Ingest ADRs from a repository.

    This function is maintained for backward compatibility.
    New code should use the ADRIngestor class directly.

    Args:
        repo_path: Path to the repository.
        glob_pattern: Glob pattern to find ADR files.
        last_processed: Metadata from the last build for incremental processing.

    Returns:
        A tuple of (nodes, edges, metadata).
    """
    ingestor = ADRIngestor()
    return ingestor.ingest(repo_path, glob_pattern, last_processed)
