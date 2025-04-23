"""Database operations for Arc Memory."""

import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import apsw
import networkx as nx
import zstandard as zstd

from arc_memory.errors import GraphBuildError, GraphQueryError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    BuildManifest,
    Edge,
    EdgeRel,
    Node,
    NodeType,
    SearchResult,
)

logger = get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime and date objects."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Default paths
DEFAULT_DB_PATH = Path.home() / ".arc" / "graph.db"
DEFAULT_COMPRESSED_DB_PATH = Path.home() / ".arc" / "graph.db.zst"
DEFAULT_MANIFEST_PATH = Path.home() / ".arc" / "build.json"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a connection to the database.

    Args:
        db_path: Path to the database file. If None, uses the default path.

    Returns:
        A connection to the database.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not db_path.exists():
        raise GraphQueryError(f"Database file not found: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise GraphQueryError(f"Failed to connect to database: {e}")


def ensure_arc_dir() -> Path:
    """Ensure the .arc directory exists.

    Returns:
        The path to the .arc directory.
    """
    arc_dir = Path.home() / ".arc"
    arc_dir.mkdir(exist_ok=True, parents=True)
    return arc_dir


def init_db(db_path: Optional[Path] = None) -> apsw.Connection:
    """Initialize the database.

    Args:
        db_path: Path to the database file. If None, uses the default path.

    Returns:
        A connection to the database.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Ensure parent directory exists
    db_path.parent.mkdir(exist_ok=True, parents=True)

    # Connect to the database
    conn = apsw.Connection(str(db_path))

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")

    # Create tables if they don't exist
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes(
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT,
            body TEXT,
            extra TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS edges(
            src TEXT NOT NULL,
            dst TEXT NOT NULL,
            rel TEXT NOT NULL,
            properties TEXT,
            PRIMARY KEY (src, dst, rel)
        )
        """
    )

    # Create FTS5 index if it doesn't exist
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_nodes USING fts5(
                body,
                content='nodes',
                content_rowid='id'
            )
            """
        )
    except apsw.SQLError as e:
        logger.error(f"Failed to create FTS5 index: {e}")
        raise GraphBuildError(f"Failed to create FTS5 index: {e}")

    return conn


def compress_db(
    db_path: Optional[Path] = None, output_path: Optional[Path] = None
) -> Path:
    """Compress the database using Zstandard.

    Args:
        db_path: Path to the database file. If None, uses the default path.
        output_path: Path to the output compressed file. If None, uses the default path.

    Returns:
        The path to the compressed database file.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    if output_path is None:
        output_path = DEFAULT_COMPRESSED_DB_PATH

    if not db_path.exists():
        raise GraphBuildError(f"Database file not found: {db_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(exist_ok=True, parents=True)

    try:
        # Read the database file
        with open(db_path, "rb") as f_in:
            db_data = f_in.read()

        # Compress the data
        compressor = zstd.ZstdCompressor(level=3)
        compressed_data = compressor.compress(db_data)

        # Write the compressed data
        with open(output_path, "wb") as f_out:
            f_out.write(compressed_data)

        logger.info(
            f"Compressed database from {db_path.stat().st_size} bytes to {output_path.stat().st_size} bytes"
        )
        return output_path
    except Exception as e:
        logger.error(f"Failed to compress database: {e}")
        raise GraphBuildError(f"Failed to compress database: {e}")


def decompress_db(
    compressed_path: Optional[Path] = None, output_path: Optional[Path] = None
) -> Path:
    """Decompress the database using Zstandard.

    Args:
        compressed_path: Path to the compressed database file. If None, uses the default path.
        output_path: Path to the output database file. If None, uses the default path.

    Returns:
        The path to the decompressed database file.
    """
    if compressed_path is None:
        compressed_path = DEFAULT_COMPRESSED_DB_PATH
    if output_path is None:
        output_path = DEFAULT_DB_PATH

    if not compressed_path.exists():
        raise GraphBuildError(f"Compressed database file not found: {compressed_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(exist_ok=True, parents=True)

    try:
        # Read the compressed file
        with open(compressed_path, "rb") as f_in:
            compressed_data = f_in.read()

        # Decompress the data
        decompressor = zstd.ZstdDecompressor()
        db_data = decompressor.decompress(compressed_data)

        # Write the decompressed data
        with open(output_path, "wb") as f_out:
            f_out.write(db_data)

        logger.info(
            f"Decompressed database from {compressed_path.stat().st_size} bytes to {output_path.stat().st_size} bytes"
        )
        return output_path
    except Exception as e:
        logger.error(f"Failed to decompress database: {e}")
        raise GraphBuildError(f"Failed to decompress database: {e}")


def save_build_manifest(
    manifest: BuildManifest, manifest_path: Optional[Path] = None
) -> None:
    """Save the build manifest to a JSON file.

    Args:
        manifest: The build manifest to save.
        manifest_path: Path to the manifest file. If None, uses the default path.
    """
    if manifest_path is None:
        manifest_path = DEFAULT_MANIFEST_PATH

    # Ensure parent directory exists
    manifest_path.parent.mkdir(exist_ok=True, parents=True)

    try:
        with open(manifest_path, "w") as f:
            f.write(manifest.model_dump_json(indent=2))
        logger.info(f"Saved build manifest to {manifest_path}")
    except Exception as e:
        logger.error(f"Failed to save build manifest: {e}")
        raise GraphBuildError(f"Failed to save build manifest: {e}")


def load_build_manifest(
    manifest_path: Optional[Path] = None,
) -> Optional[BuildManifest]:
    """Load the build manifest from a JSON file.

    Args:
        manifest_path: Path to the manifest file. If None, uses the default path.

    Returns:
        The build manifest, or None if the file doesn't exist.
    """
    if manifest_path is None:
        manifest_path = DEFAULT_MANIFEST_PATH

    if not manifest_path.exists():
        logger.warning(f"Build manifest not found: {manifest_path}")
        return None

    try:
        with open(manifest_path, "r") as f:
            data = json.load(f)
        return BuildManifest.model_validate(data)
    except Exception as e:
        logger.error(f"Failed to load build manifest: {e}")
        return None


def add_nodes_and_edges(
    conn: apsw.Connection, nodes: List[Node], edges: List[Edge]
) -> None:
    """Add nodes and edges to the database.

    Args:
        conn: A connection to the database.
        nodes: The nodes to add.
        edges: The edges to add.
    """
    try:
        # Begin transaction
        with conn:
            # Add nodes
            for node in nodes:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nodes(id, type, title, body, extra)
                    VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        node.id,
                        node.type.value,
                        node.title,
                        node.body,
                        json.dumps(node.extra, cls=DateTimeEncoder),
                    ),
                )

            # Add edges
            for edge in edges:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO edges(src, dst, rel, properties)
                    VALUES(?, ?, ?, ?)
                    """,
                    (
                        edge.src,
                        edge.dst,
                        edge.rel.value,
                        json.dumps(edge.properties, cls=DateTimeEncoder),
                    ),
                )

            # Rebuild FTS index
            conn.execute("INSERT INTO fts_nodes(fts_nodes) VALUES('rebuild')")

        logger.info(f"Added {len(nodes)} nodes and {len(edges)} edges to the database")
    except Exception as e:
        logger.error(f"Failed to add nodes and edges: {e}")
        raise GraphBuildError(f"Failed to add nodes and edges: {e}")


def get_node_count(conn: apsw.Connection) -> int:
    """Get the number of nodes in the database.

    Args:
        conn: A connection to the database.

    Returns:
        The number of nodes.
    """
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM nodes")
        return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Failed to get node count: {e}")
        raise GraphQueryError(f"Failed to get node count: {e}")


def get_edge_count(conn: apsw.Connection) -> int:
    """Get the number of edges in the database.

    Args:
        conn: A connection to the database.

    Returns:
        The number of edges.
    """
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM edges")
        return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Failed to get edge count: {e}")
        raise GraphQueryError(f"Failed to get edge count: {e}")


def search_entities(
    conn: apsw.Connection, query: str, limit: int = 5
) -> List[SearchResult]:
    """Search for entities in the database.

    Args:
        conn: A connection to the database.
        query: The search query.
        limit: The maximum number of results to return.

    Returns:
        A list of search results.
    """
    try:
        cursor = conn.execute(
            """
            SELECT n.id, n.type, n.title, snippet(fts_nodes, 0, '<b>', '</b>', '...', 10) as snippet, rank
            FROM fts_nodes
            JOIN nodes n ON fts_nodes.rowid = n.id
            WHERE fts_nodes MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        results = []
        for row in cursor:
            results.append(
                SearchResult(
                    id=row[0],
                    type=NodeType(row[1]),
                    title=row[2],
                    snippet=row[3],
                    score=row[4],
                )
            )
        return results
    except Exception as e:
        logger.error(f"Failed to search entities: {e}")
        raise GraphQueryError(f"Failed to search entities: {e}")


def get_node_by_id(conn: apsw.Connection, node_id: str) -> Optional[Dict[str, Any]]:
    """Get a node by its ID.

    Args:
        conn: A connection to the database.
        node_id: The ID of the node.

    Returns:
        The node, or None if it doesn't exist.
    """
    try:
        cursor = conn.execute(
            """
            SELECT id, type, title, body, extra
            FROM nodes
            WHERE id = ?
            """,
            (node_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "type": row[1],
            "title": row[2],
            "body": row[3],
            "extra": json.loads(row[4]) if row[4] else {},
        }
    except Exception as e:
        logger.error(f"Failed to get node by ID: {e}")
        raise GraphQueryError(f"Failed to get node by ID: {e}")


def get_edges_by_src(
    conn: apsw.Connection, src_id: str, rel_type: Optional[EdgeRel] = None
) -> List[Dict[str, Any]]:
    """Get edges by source node ID.

    Args:
        conn: A connection to the database.
        src_id: The ID of the source node.
        rel_type: Optional relationship type to filter by.

    Returns:
        A list of edges.
    """
    try:
        if rel_type is None:
            cursor = conn.execute(
                """
                SELECT src, dst, rel, properties
                FROM edges
                WHERE src = ?
                """,
                (src_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT src, dst, rel, properties
                FROM edges
                WHERE src = ? AND rel = ?
                """,
                (src_id, rel_type.value),
            )
        edges = []
        for row in cursor:
            edges.append(
                {
                    "src": row[0],
                    "dst": row[1],
                    "rel": row[2],
                    "properties": json.loads(row[3]) if row[3] else {},
                }
            )
        return edges
    except Exception as e:
        logger.error(f"Failed to get edges by source: {e}")
        raise GraphQueryError(f"Failed to get edges by source: {e}")


def get_edges_by_dst(
    conn: apsw.Connection, dst_id: str, rel_type: Optional[EdgeRel] = None
) -> List[Dict[str, Any]]:
    """Get edges by destination node ID.

    Args:
        conn: A connection to the database.
        dst_id: The ID of the destination node.
        rel_type: Optional relationship type to filter by.

    Returns:
        A list of edges.
    """
    try:
        if rel_type is None:
            cursor = conn.execute(
                """
                SELECT src, dst, rel, properties
                FROM edges
                WHERE dst = ?
                """,
                (dst_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT src, dst, rel, properties
                FROM edges
                WHERE dst = ? AND rel = ?
                """,
                (dst_id, rel_type.value),
            )
        edges = []
        for row in cursor:
            edges.append(
                {
                    "src": row[0],
                    "dst": row[1],
                    "rel": row[2],
                    "properties": json.loads(row[3]) if row[3] else {},
                }
            )
        return edges
    except Exception as e:
        logger.error(f"Failed to get edges by destination: {e}")
        raise GraphQueryError(f"Failed to get edges by destination: {e}")


def build_networkx_graph(conn: apsw.Connection) -> nx.DiGraph:
    """Build a NetworkX directed graph from the database.

    Args:
        conn: A connection to the database.

    Returns:
        A NetworkX directed graph.
    """
    try:
        G = nx.DiGraph()

        # Add nodes
        cursor = conn.execute("SELECT id, type, title, extra FROM nodes")
        for row in cursor:
            G.add_node(
                row[0],
                type=row[1],
                title=row[2],
                extra=json.loads(row[3]) if row[3] else {},
            )

        # Add edges
        cursor = conn.execute("SELECT src, dst, rel, properties FROM edges")
        for row in cursor:
            G.add_edge(
                row[0],
                row[1],
                rel=row[2],
                properties=json.loads(row[3]) if row[3] else {},
            )

        return G
    except Exception as e:
        logger.error(f"Failed to build NetworkX graph: {e}")
        raise GraphQueryError(f"Failed to build NetworkX graph: {e}")


def trace_history(
    conn: apsw.Connection, file_path: str, line_number: int, max_nodes: int = 3
) -> List[Dict[str, Any]]:
    """Trace the history of a file line.

    This is a placeholder implementation. The actual implementation would use
    git blame to find the commit that last modified the line, then follow
    the graph to find related PRs, issues, and ADRs.

    Args:
        conn: A connection to the database.
        file_path: The path to the file.
        line_number: The line number.
        max_nodes: The maximum number of nodes to return.

    Returns:
        A list of nodes in the history trace.
    """
    # This is a placeholder. The actual implementation would:
    # 1. Use git blame to find the commit that last modified the line
    # 2. Follow MERGES edges to find the PR that merged the commit
    # 3. Follow MENTIONS edges to find issues mentioned in the PR
    # 4. Follow DECIDES edges to find ADRs that decided on the file
    # 5. Return the nodes in order (newest first)
    logger.warning("trace_history is not fully implemented yet")
    return []
