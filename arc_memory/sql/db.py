"""Database operations for Arc Memory."""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# These imports are handled dynamically to support graceful degradation
# when dependencies are missing
# import apsw
# import networkx as nx
# import zstandard as zstd

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


def get_connection(db_path: Optional[Path] = None, check_exists: bool = True) -> sqlite3.Connection:
    """Get a connection to the database.

    Args:
        db_path: Path to the database file. If None, uses the default path.
        check_exists: Whether to check if the database file exists.

    Returns:
        A connection to the database.

    Raises:
        DatabaseNotFoundError: If the database file doesn't exist and check_exists is True.
        DatabaseError: If connecting to the database fails.
    """
    from arc_memory.errors import DatabaseNotFoundError, DatabaseError

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Check if the database exists
    if check_exists and not db_path.exists():
        compressed_path = db_path.with_suffix(db_path.suffix + ".zst")

        # Check if compressed database exists and try to decompress it
        if compressed_path.exists():
            try:
                logger.info(f"Found compressed database at {compressed_path}. Decompressing...")
                decompress_db(compressed_path, db_path)
            except Exception as e:
                error_msg = f"Database not found at {db_path} and failed to decompress from {compressed_path}: {e}"
                logger.error(error_msg)
                raise DatabaseNotFoundError(
                    error_msg,
                    details={
                        "db_path": str(db_path),
                        "compressed_path": str(compressed_path),
                        "error": str(e),
                    }
                )
        else:
            error_msg = (
                f"Database not found at {db_path} or {compressed_path}. "
                "Run 'arc build' to create the database."
            )
            logger.error(error_msg)
            raise DatabaseNotFoundError(
                error_msg,
                details={
                    "db_path": str(db_path),
                    "compressed_path": str(compressed_path),
                }
            )

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        error_msg = f"Failed to connect to database: {e}"
        logger.error(error_msg)
        raise DatabaseError(
            error_msg,
            details={
                "db_path": str(db_path),
                "error": str(e),
            }
        )


def ensure_arc_dir() -> Path:
    """Ensure the .arc directory exists.

    Returns:
        The path to the .arc directory.
    """
    arc_dir = Path.home() / ".arc"
    arc_dir.mkdir(exist_ok=True, parents=True)
    return arc_dir


def init_db(db_path: Optional[Path] = None, test_mode: bool = False) -> Any:
    """Initialize the database.

    Args:
        db_path: Path to the database file. If None, uses the default path.
        test_mode: Whether to run in test mode (without actual database operations).

    Returns:
        A connection to the database (either a real connection or a mock connection in test mode).

    Raises:
        DatabaseInitializationError: If initializing the database fails.
    """
    from arc_memory.errors import DatabaseInitializationError

    # If test mode is enabled, use the mock database
    if test_mode:
        try:
            from arc_memory.sql.test_db import init_test_db
            logger.info("Initializing database in test mode")
            return init_test_db()
        except ImportError as e:
            error_msg = f"Failed to import test database module: {e}"
            logger.error(error_msg)
            raise DatabaseInitializationError(
                error_msg,
                details={"error": str(e)}
            )

    # Check dependencies first
    try:
        import apsw
    except ImportError:
        error_msg = (
            "Failed to import 'apsw' module. "
            "Please install it with: pip install apsw>=3.40.0"
        )
        logger.error(error_msg)
        raise DatabaseInitializationError(
            error_msg,
            details={"missing_dependency": "apsw"}
        )

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Ensure parent directory exists
    try:
        db_path.parent.mkdir(exist_ok=True, parents=True)
    except Exception as e:
        error_msg = f"Failed to create directory for database: {e}"
        logger.error(error_msg)
        raise DatabaseInitializationError(
            error_msg,
            details={
                "db_path": str(db_path),
                "error": str(e),
            }
        )

    # Connect to the database
    try:
        conn = apsw.Connection(str(db_path))
    except Exception as e:
        error_msg = f"Failed to connect to database: {e}"
        logger.error(error_msg)
        raise DatabaseInitializationError(
            error_msg,
            details={
                "db_path": str(db_path),
                "error": str(e),
            }
        )

    # Enable WAL mode for better concurrency
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception as e:
        error_msg = f"Failed to enable WAL mode: {e}"
        logger.error(error_msg)
        # This is not critical, so we'll continue

    # Create tables if they don't exist
    try:
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
    except Exception as e:
        error_msg = f"Failed to create tables: {e}"
        logger.error(error_msg)
        raise DatabaseInitializationError(
            error_msg,
            details={
                "db_path": str(db_path),
                "error": str(e),
            }
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
    except Exception as e:
        error_msg = f"Failed to create FTS5 index: {e}"
        logger.error(error_msg)
        # FTS5 is optional, so we'll continue but log the error
        logger.warning(
            "Full-text search will not be available. "
            "This may be due to an older version of SQLite or missing FTS5 support."
        )

    # Verify the database is working
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM nodes")
        node_count = cursor.fetchone()[0]
        logger.debug(f"Database initialized with {node_count} nodes")
    except Exception as e:
        error_msg = f"Failed to query database: {e}"
        logger.error(error_msg)
        raise DatabaseInitializationError(
            error_msg,
            details={
                "db_path": str(db_path),
                "error": str(e),
            }
        )

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

    Raises:
        GraphBuildError: If compressing the database fails.
        DependencyError: If zstandard is not installed.
    """
    from arc_memory.errors import DependencyError

    # Check if zstandard is installed
    try:
        import zstandard as zstd
    except ImportError:
        error_msg = (
            "Failed to import 'zstandard' module. "
            "Please install it with: pip install zstandard>=0.20.0"
        )
        logger.error(error_msg)
        raise DependencyError(
            error_msg,
            details={"missing_dependency": "zstandard"}
        )

    if db_path is None:
        db_path = DEFAULT_DB_PATH
    if output_path is None:
        output_path = DEFAULT_COMPRESSED_DB_PATH

    if not db_path.exists():
        error_msg = f"Database file not found: {db_path}"
        logger.error(error_msg)
        raise GraphBuildError(
            error_msg,
            details={"db_path": str(db_path)}
        )

    # Ensure output directory exists
    try:
        output_path.parent.mkdir(exist_ok=True, parents=True)
    except Exception as e:
        error_msg = f"Failed to create directory for compressed database: {e}"
        logger.error(error_msg)
        raise GraphBuildError(
            error_msg,
            details={
                "output_path": str(output_path),
                "error": str(e),
            }
        )

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
        error_msg = f"Failed to compress database: {e}"
        logger.error(error_msg)
        raise GraphBuildError(
            error_msg,
            details={
                "db_path": str(db_path),
                "output_path": str(output_path),
                "error": str(e),
            }
        )


def decompress_db(
    compressed_path: Optional[Path] = None, output_path: Optional[Path] = None
) -> Path:
    """Decompress the database using Zstandard.

    Args:
        compressed_path: Path to the compressed database file. If None, uses the default path.
        output_path: Path to the output database file. If None, uses the default path.

    Returns:
        The path to the decompressed database file.

    Raises:
        GraphBuildError: If decompressing the database fails.
        DependencyError: If zstandard is not installed.
    """
    from arc_memory.errors import DependencyError

    # Check if zstandard is installed
    try:
        import zstandard as zstd
    except ImportError:
        error_msg = (
            "Failed to import 'zstandard' module. "
            "Please install it with: pip install zstandard>=0.20.0"
        )
        logger.error(error_msg)
        raise DependencyError(
            error_msg,
            details={"missing_dependency": "zstandard"}
        )

    if compressed_path is None:
        compressed_path = DEFAULT_COMPRESSED_DB_PATH
    if output_path is None:
        output_path = DEFAULT_DB_PATH

    if not compressed_path.exists():
        error_msg = f"Compressed database file not found: {compressed_path}"
        logger.error(error_msg)
        raise GraphBuildError(
            error_msg,
            details={"compressed_path": str(compressed_path)}
        )

    # Ensure output directory exists
    try:
        output_path.parent.mkdir(exist_ok=True, parents=True)
    except Exception as e:
        error_msg = f"Failed to create directory for decompressed database: {e}"
        logger.error(error_msg)
        raise GraphBuildError(
            error_msg,
            details={
                "output_path": str(output_path),
                "error": str(e),
            }
        )

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
        error_msg = f"Failed to decompress database: {e}"
        logger.error(error_msg)
        raise GraphBuildError(
            error_msg,
            details={
                "compressed_path": str(compressed_path),
                "output_path": str(output_path),
                "error": str(e),
            }
        )


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


def ensure_connection(conn_or_path: Union[Any, Path, str]) -> sqlite3.Connection:
    """Ensure we have a valid database connection.

    This function accepts either:
    - An existing database connection object
    - A path to a database file (as Path or string)

    It returns a valid database connection in all cases, opening a new
    connection if a path was provided.

    Args:
        conn_or_path: Either a database connection object or a path to a database file.

    Returns:
        A valid database connection.

    Raises:
        DatabaseError: If the input is neither a valid connection nor a valid path.
    """
    from arc_memory.errors import DatabaseError

    # Case 1: Already a connection object
    if hasattr(conn_or_path, 'execute') or hasattr(conn_or_path, 'cursor'):
        return conn_or_path

    # Case 2: A Path object or string path
    if isinstance(conn_or_path, (Path, str)):
        path = Path(conn_or_path) if isinstance(conn_or_path, str) else conn_or_path
        return get_connection(path)

    # Case 3: Invalid input
    raise DatabaseError(
        f"Expected a database connection or path, got {type(conn_or_path).__name__}",
        details={
            "type": type(conn_or_path).__name__,
            "value": str(conn_or_path),
            "hint": "Pass either a database connection object or a Path to the database file."
        }
    )


def add_nodes_and_edges(
    conn: Any, nodes: List[Node], edges: List[Edge]
) -> None:
    """Add nodes and edges to the database.

    Args:
        conn: A connection to the database (real or mock).
        nodes: The nodes to add.
        edges: The edges to add.

    Raises:
        GraphBuildError: If adding nodes and edges fails.
    """
    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        try:
            from arc_memory.sql.test_db import add_test_nodes_and_edges
            add_test_nodes_and_edges(conn, nodes, edges)
            return
        except ImportError as e:
            logger.error(f"Failed to import test database module: {e}")
            raise GraphBuildError(f"Failed to add nodes and edges in test mode: {e}")

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
            try:
                conn.execute("INSERT INTO fts_nodes(fts_nodes) VALUES('rebuild')")
            except Exception as e:
                # FTS index is optional, so we'll continue but log the error
                logger.warning(f"Failed to rebuild FTS index: {e}")

        logger.info(f"Added {len(nodes)} nodes and {len(edges)} edges to the database")
    except Exception as e:
        logger.error(f"Failed to add nodes and edges: {e}")
        raise GraphBuildError(
            f"Failed to add nodes and edges: {e}",
            details={
                "node_count": len(nodes),
                "edge_count": len(edges),
                "error": str(e),
            }
        )


def get_node_count(conn: Any) -> int:
    """Get the number of nodes in the database.

    Args:
        conn: A connection to the database (real or mock).

    Returns:
        The number of nodes.

    Raises:
        GraphQueryError: If getting the node count fails.
    """
    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        try:
            from arc_memory.sql.test_db import get_test_node_count
            return get_test_node_count(conn)
        except ImportError as e:
            logger.error(f"Failed to import test database module: {e}")
            raise GraphQueryError(f"Failed to get node count in test mode: {e}")

    try:
        cursor = conn.execute("SELECT COUNT(*) FROM nodes")
        return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Failed to get node count: {e}")
        raise GraphQueryError(
            f"Failed to get node count: {e}",
            details={"error": str(e)}
        )


def get_edge_count(conn: Any) -> int:
    """Get the number of edges in the database.

    Args:
        conn: A connection to the database (real or mock).

    Returns:
        The number of edges.

    Raises:
        GraphQueryError: If getting the edge count fails.
    """
    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        try:
            from arc_memory.sql.test_db import get_test_edge_count
            return get_test_edge_count(conn)
        except ImportError as e:
            logger.error(f"Failed to import test database module: {e}")
            raise GraphQueryError(f"Failed to get edge count in test mode: {e}")

    try:
        cursor = conn.execute("SELECT COUNT(*) FROM edges")
        return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Failed to get edge count: {e}")
        raise GraphQueryError(
            f"Failed to get edge count: {e}",
            details={"error": str(e)}
        )


def search_entities(
    conn: Any, query: str, limit: int = 5
) -> List[SearchResult]:
    """Search for entities in the database.

    Args:
        conn: A connection to the database (real or mock).
        query: The search query.
        limit: The maximum number of results to return.

    Returns:
        A list of search results.

    Raises:
        GraphQueryError: If searching entities fails.
    """
    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        try:
            from arc_memory.sql.test_db import search_test_entities
            return search_test_entities(conn, query, limit)
        except ImportError as e:
            logger.error(f"Failed to import test database module: {e}")
            raise GraphQueryError(f"Failed to search entities in test mode: {e}")

    try:
        try:
            # Try using FTS5 first
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
        except Exception as e:
            # Fall back to basic search if FTS5 fails
            logger.warning(f"FTS5 search failed, falling back to basic search: {e}")
            cursor = conn.execute(
                """
                SELECT id, type, title, body, 1.0 as score
                FROM nodes
                WHERE title LIKE ? OR body LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", limit),
            )

        results = []
        for row in cursor:
            snippet = row[3] if len(row) > 3 else ""
            if len(snippet) > 100:
                snippet = snippet[:100] + "..."

            results.append(
                SearchResult(
                    id=row[0],
                    type=NodeType(row[1]),
                    title=row[2] or "",
                    snippet=snippet,
                    score=row[4] if len(row) > 4 else 1.0,
                )
            )
        return results
    except Exception as e:
        logger.error(f"Failed to search entities: {e}")
        raise GraphQueryError(
            f"Failed to search entities: {e}",
            details={
                "query": query,
                "limit": limit,
                "error": str(e),
            }
        )


def get_node_by_id(conn_or_path: Union[Any, Path, str], node_id: str) -> Optional[Dict[str, Any]]:
    """Get a node by its ID.

    Args:
        conn_or_path: Either a database connection object or a path to a database file.
        node_id: The ID of the node.

    Returns:
        The node, or None if it doesn't exist.

    Raises:
        GraphQueryError: If getting the node fails.
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        try:
            from arc_memory.sql.test_db import get_test_node_by_id
            return get_test_node_by_id(conn, node_id)
        except ImportError as e:
            logger.error(f"Failed to import test database module: {e}")
            raise GraphQueryError(f"Failed to get node by ID in test mode: {e}")

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
        raise GraphQueryError(
            f"Failed to get node by ID '{node_id}': {e}",
            details={
                "node_id": node_id,
                "error": str(e),
                "hint": "Make sure you're passing a valid database connection or path."
            }
        )


def get_edges_by_src(
    conn_or_path: Union[Any, Path, str], src_id: str, rel_type: Optional[EdgeRel] = None
) -> List[Dict[str, Any]]:
    """Get edges by source node ID.

    Args:
        conn_or_path: Either a database connection object or a path to a database file.
        src_id: The ID of the source node.
        rel_type: Optional relationship type to filter by.

    Returns:
        A list of edges.

    Raises:
        GraphQueryError: If getting the edges fails.
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        try:
            from arc_memory.sql.test_db import get_test_edges_by_src
            return get_test_edges_by_src(conn, src_id, rel_type)
        except ImportError as e:
            logger.error(f"Failed to import test database module: {e}")
            raise GraphQueryError(f"Failed to get edges by source in test mode: {e}")

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
        raise GraphQueryError(
            f"Failed to get edges by source node '{src_id}': {e}",
            details={
                "src_id": src_id,
                "rel_type": rel_type.value if rel_type else None,
                "error": str(e),
                "hint": "Make sure you're passing a valid database connection or path."
            }
        )


def get_edges_by_dst(
    conn_or_path: Union[Any, Path, str], dst_id: str, rel_type: Optional[EdgeRel] = None
) -> List[Dict[str, Any]]:
    """Get edges by destination node ID.

    Args:
        conn_or_path: Either a database connection object or a path to a database file.
        dst_id: The ID of the destination node.
        rel_type: Optional relationship type to filter by.

    Returns:
        A list of edges.

    Raises:
        GraphQueryError: If getting the edges fails.
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        try:
            from arc_memory.sql.test_db import get_test_edges_by_dst
            return get_test_edges_by_dst(conn, dst_id, rel_type)
        except ImportError as e:
            logger.error(f"Failed to import test database module: {e}")
            raise GraphQueryError(f"Failed to get edges by destination in test mode: {e}")

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
        raise GraphQueryError(
            f"Failed to get edges by destination node '{dst_id}': {e}",
            details={
                "dst_id": dst_id,
                "rel_type": rel_type.value if rel_type else None,
                "error": str(e),
                "hint": "Make sure you're passing a valid database connection or path."
            }
        )


def build_networkx_graph(conn: Any) -> Any:
    """Build a NetworkX directed graph from the database.

    Args:
        conn: A connection to the database (real or mock).

    Returns:
        A NetworkX directed graph.

    Raises:
        GraphQueryError: If building the graph fails.
        DependencyError: If NetworkX is not installed.
    """
    from arc_memory.errors import DependencyError

    # Check if NetworkX is installed
    try:
        import networkx as nx
    except ImportError:
        error_msg = (
            "Failed to import 'networkx' module. "
            "Please install it with: pip install networkx>=3.0"
        )
        logger.error(error_msg)
        raise DependencyError(
            error_msg,
            details={"missing_dependency": "networkx"}
        )

    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        # Create a graph from the mock database
        G = nx.DiGraph()

        # Add nodes
        for node_id, node in conn.nodes.items():
            G.add_node(
                node_id,
                type=node.type.value,
                title=node.title,
                extra=node.extra,
            )

        # Add edges
        for edge in conn.edges:
            G.add_edge(
                edge.src,
                edge.dst,
                rel=edge.rel.value,
                properties=edge.properties,
            )

        return G

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
        raise GraphQueryError(
            f"Failed to build NetworkX graph: {e}",
            details={"error": str(e)}
        )


def trace_history(
    conn: Any, file_path: str, line_number: int, max_nodes: int = 3
) -> List[Dict[str, Any]]:
    """Trace the history of a file line.

    This is a placeholder implementation. The actual implementation would use
    git blame to find the commit that last modified the line, then follow
    the graph to find related PRs, issues, and ADRs.

    Args:
        conn: A connection to the database (real or mock).
        file_path: The path to the file.
        line_number: The line number.
        max_nodes: The maximum number of nodes to return.

    Returns:
        A list of nodes in the history trace.
    """
    # Check if we're using a test database
    if hasattr(conn, 'nodes') and hasattr(conn, 'edges'):
        # Return mock data for test mode
        logger.info(f"Tracing history for {file_path}:{line_number} in test mode")
        return [
            {
                "id": "commit:test-commit-id",
                "type": "commit",
                "title": "Test commit",
                "body": "This is a test commit for tracing history",
                "timestamp": datetime.now().isoformat(),
                "author": "Test User",
            }
        ]

    # This is a placeholder. The actual implementation would:
    # 1. Use git blame to find the commit that last modified the line
    # 2. Follow MERGES edges to find the PR that merged the commit
    # 3. Follow MENTIONS edges to find issues mentioned in the PR
    # 4. Follow DECIDES edges to find ADRs that decided on the file
    # 5. Return the nodes in order (newest first)
    logger.warning("trace_history is not fully implemented yet")
    return []
