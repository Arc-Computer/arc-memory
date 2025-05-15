"""SQLite adapter for Arc Memory.

This module provides a SQLite implementation of the DatabaseAdapter protocol.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from arc_memory.errors import DatabaseError, DatabaseInitializationError, GraphBuildError, GraphQueryError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType

logger = get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class SQLiteAdapter:
    """SQLite implementation of the DatabaseAdapter protocol."""

    def __init__(self):
        """Initialize the SQLite adapter."""
        self.conn = None
        self.db_path = None

    def get_name(self) -> str:
        """Get the name of the database adapter.

        Returns:
            The name of the database adapter.
        """
        return "sqlite"

    def get_supported_versions(self) -> List[str]:
        """Get the supported versions of the database.

        Returns:
            A list of supported database versions.
        """
        return ["3.0.0", "3.1.0"]

    def connect(self, connection_params: Dict[str, Any]) -> None:
        """Connect to the database.

        Args:
            connection_params: Parameters for connecting to the database.
                - db_path: Path to the database file.
                - check_exists: Whether to check if the database file exists.

        Raises:
            DatabaseError: If connecting to the database fails.
        """
        db_path = connection_params.get("db_path")
        check_exists = connection_params.get("check_exists", True)

        if db_path is None:
            raise DatabaseError(
                "Database path not provided",
                details={"hint": "Provide a 'db_path' parameter"}
            )

        self.db_path = Path(db_path)

        # Check if the database exists
        if check_exists and not self.db_path.exists():
            compressed_path = self.db_path.with_suffix(self.db_path.suffix + ".zst")
            if compressed_path.exists():
                # Decompress the database
                try:
                    import zstandard as zstd
                    with open(compressed_path, "rb") as f_in:
                        dctx = zstd.ZstdDecompressor()
                        with open(self.db_path, "wb") as f_out:
                            dctx.copy_stream(f_in, f_out)
                    logger.info(f"Decompressed database from {compressed_path} to {self.db_path}")
                except ImportError:
                    error_msg = (
                        "Failed to import 'zstandard' module. "
                        "Please install it with: pip install zstandard"
                    )
                    logger.error(error_msg)
                    raise DatabaseError(
                        error_msg,
                        details={"missing_dependency": "zstandard"}
                    )
                except Exception as e:
                    error_msg = f"Failed to decompress database: {e}"
                    logger.error(error_msg)
                    raise DatabaseError(
                        error_msg,
                        details={
                            "db_path": str(self.db_path),
                            "compressed_path": str(compressed_path),
                            "error": str(e),
                        }
                    )
            else:
                error_msg = (
                    f"Database file not found: {self.db_path} "
                    f"and no compressed version found: {compressed_path}"
                )
                logger.error(error_msg)
                raise DatabaseError(
                    error_msg,
                    details={
                        "db_path": str(self.db_path),
                        "compressed_path": str(compressed_path),
                    }
                )

        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(exist_ok=True, parents=True)

            # Connect to the database
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
            return
        except Exception as e:
            error_msg = f"Failed to connect to database: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "db_path": str(self.db_path),
                    "error": str(e),
                }
            )

    def disconnect(self) -> None:
        """Disconnect from the database.

        Raises:
            DatabaseError: If disconnecting from the database fails.
        """
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn = None
                logger.info(f"Disconnected from database: {self.db_path}")
            except Exception as e:
                error_msg = f"Failed to disconnect from database: {e}"
                logger.error(error_msg)
                raise DatabaseError(
                    error_msg,
                    details={
                        "db_path": str(self.db_path),
                        "error": str(e),
                    }
                )

    def is_connected(self) -> bool:
        """Check if the adapter is connected to the database.

        Returns:
            True if connected, False otherwise.
        """
        return self.conn is not None

    def init_db(self, params: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the database schema.

        Args:
            params: Optional parameters for database initialization.

        Raises:
            DatabaseInitializationError: If initializing the database fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            # Create repositories table if it doesn't exist
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS repositories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT,
                    local_path TEXT NOT NULL,
                    default_branch TEXT DEFAULT 'main',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
                """
            )

            # Create tables if they don't exist
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes(
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT,
                    body TEXT,
                    timestamp TEXT,
                    repo_id TEXT,
                    extra TEXT
                )
                """
            )

            # Create index on timestamp column
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_nodes_timestamp ON nodes(timestamp)
                """
            )

            # Create index on repo_id column
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_nodes_repo_id ON nodes(repo_id)
                """
            )

            self.conn.execute(
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

            # Create metadata table
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata(
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )

            # Create refresh_timestamps table
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS refresh_timestamps(
                    source TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL
                )
                """
            )

            logger.info(f"Initialized database schema: {self.db_path}")

            # Run migrations automatically
            try:
                from arc_memory.migrations.add_timestamp_column import migrate_database
                migrate_success = migrate_database(self.db_path)
                if migrate_success:
                    logger.info(f"Successfully ran timestamp column migration for {self.db_path}")
                else:
                    logger.warning(f"Failed to run timestamp column migration for {self.db_path}")

                # Run repository migration
                from arc_memory.migrations.add_repo_id_column import migrate_database as migrate_repo_id
                repo_migrate_success = migrate_repo_id(self.db_path)
                if repo_migrate_success:
                    logger.info(f"Successfully ran repository migration for {self.db_path}")
                else:
                    logger.warning(f"Failed to run repository migration for {self.db_path}")

                # Run architecture schema migration
                from arc_memory.migrations.add_architecture_schema import migrate_database as migrate_architecture
                arch_migrate_success = migrate_architecture(self.db_path)
                if arch_migrate_success:
                    logger.info(f"Successfully ran architecture schema migration for {self.db_path}")
                else:
                    logger.warning(f"Failed to run architecture schema migration for {self.db_path}")
            except Exception as migrate_error:
                logger.warning(f"Error running database migrations: {migrate_error}")
                # Don't fail initialization if migrations fail
                # The database is still usable, just might not have the latest schema
        except Exception as e:
            error_msg = f"Failed to initialize database schema: {e}"
            logger.error(error_msg)
            raise DatabaseInitializationError(
                error_msg,
                details={
                    "db_path": str(self.db_path),
                    "error": str(e),
                }
            )

    def add_nodes_and_edges(self, nodes: List[Node], edges: List[Edge]) -> None:
        """Add nodes and edges to the database.

        Args:
            nodes: The nodes to add.
            edges: The edges to add.

        Raises:
            GraphBuildError: If adding nodes and edges fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            # Begin transaction
            self.conn.execute("BEGIN TRANSACTION")

            # Add nodes
            for node in nodes:
                # Extract timestamp from node
                timestamp_str = None
                if hasattr(node, 'ts') and node.ts:
                    timestamp_str = node.ts.isoformat()

                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO nodes(id, type, title, body, timestamp, repo_id, extra)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node.id,
                        node.type.value,
                        node.title,
                        node.body,
                        timestamp_str,
                        node.repo_id,
                        json.dumps(node.extra, cls=DateTimeEncoder),
                    ),
                )

            # Add edges
            for edge in edges:
                self.conn.execute(
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

            # Commit transaction
            self.conn.execute("COMMIT")

            logger.info(f"Added {len(nodes)} nodes and {len(edges)} edges to database")
        except Exception as e:
            error_msg = f"Failed to add nodes and edges: {e}"
            logger.error(error_msg)
            raise GraphBuildError(
                error_msg,
                details={
                    "db_path": str(self.db_path),
                    "error": str(e),
                }
            )

    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by its ID.

        Args:
            node_id: The ID of the node.

        Returns:
            The node as a dictionary, or None if it doesn't exist.

        Raises:
            GraphQueryError: If getting the node fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            cursor = self.conn.execute(
                """
                SELECT id, type, title, body, timestamp, extra
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
                "timestamp": row[4],
                "extra": json.loads(row[5]) if row[5] else {},
            }
        except Exception as e:
            error_msg = f"Failed to get node by ID: {e}"
            logger.error(error_msg)
            raise GraphQueryError(
                f"Failed to get node by ID '{node_id}': {e}",
                details={
                    "node_id": node_id,
                    "error": str(e),
                }
            )

    def get_node_count(self) -> int:
        """Get the number of nodes in the database.

        Returns:
            The number of nodes.

        Raises:
            GraphQueryError: If getting the node count fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM nodes")
            return cursor.fetchone()[0]
        except Exception as e:
            error_msg = f"Failed to get node count: {e}"
            logger.error(error_msg)
            raise GraphQueryError(
                error_msg,
                details={
                    "db_path": str(self.db_path),
                    "error": str(e),
                }
            )

    def get_edge_count(self) -> int:
        """Get the number of edges in the database.

        Returns:
            The number of edges.

        Raises:
            GraphQueryError: If getting the edge count fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM edges")
            return cursor.fetchone()[0]
        except Exception as e:
            error_msg = f"Failed to get edge count: {e}"
            logger.error(error_msg)
            raise GraphQueryError(
                error_msg,
                details={
                    "db_path": str(self.db_path),
                    "error": str(e),
                }
            )

    def get_edges_by_src(self, src_id: str, rel_type: Optional[EdgeRel] = None) -> List[Dict[str, Any]]:
        """Get edges by source node ID.

        Args:
            src_id: The ID of the source node.
            rel_type: Optional relationship type to filter by.

        Returns:
            A list of edges as dictionaries.

        Raises:
            GraphQueryError: If getting the edges fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            if rel_type is None:
                cursor = self.conn.execute(
                    """
                    SELECT src, dst, rel, properties
                    FROM edges
                    WHERE src = ?
                    """,
                    (src_id,),
                )
            else:
                cursor = self.conn.execute(
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
            error_msg = f"Failed to get edges by source: {e}"
            logger.error(error_msg)
            raise GraphQueryError(
                f"Failed to get edges by source node '{src_id}': {e}",
                details={
                    "src_id": src_id,
                    "rel_type": rel_type.value if rel_type else None,
                    "error": str(e),
                }
            )

    def get_edges_by_dst(self, dst_id: str, rel_type: Optional[EdgeRel] = None) -> List[Dict[str, Any]]:
        """Get edges by destination node ID.

        Args:
            dst_id: The ID of the destination node.
            rel_type: Optional relationship type to filter by.

        Returns:
            A list of edges as dictionaries.

        Raises:
            GraphQueryError: If getting the edges fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            if rel_type is None:
                cursor = self.conn.execute(
                    """
                    SELECT src, dst, rel, properties
                    FROM edges
                    WHERE dst = ?
                    """,
                    (dst_id,),
                )
            else:
                cursor = self.conn.execute(
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
            error_msg = f"Failed to get edges by destination: {e}"
            logger.error(error_msg)
            raise GraphQueryError(
                f"Failed to get edges by destination node '{dst_id}': {e}",
                details={
                    "dst_id": dst_id,
                    "rel_type": rel_type.value if rel_type else None,
                    "error": str(e),
                }
            )

    def search_entities(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for entities in the database.

        Args:
            query: The search query.
            limit: The maximum number of results to return.

        Returns:
            A list of search results.

        Raises:
            GraphQueryError: If searching entities fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            try:
                # Try using FTS5 first
                cursor = self.conn.execute(
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
                cursor = self.conn.execute(
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
                    {
                        "id": row[0],
                        "type": row[1],
                        "title": row[2] or "",
                        "snippet": snippet,
                        "score": row[4] if len(row) > 4 else 1.0,
                    }
                )
            return results
        except Exception as e:
            error_msg = f"Failed to search entities: {e}"
            logger.error(error_msg)
            raise GraphQueryError(
                f"Failed to search entities: {e}",
                details={
                    "query": query,
                    "limit": limit,
                    "error": str(e),
                }
            )

    def begin_transaction(self) -> Any:
        """Begin a transaction.

        Returns:
            A transaction object.

        Raises:
            DatabaseError: If beginning the transaction fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            # Explicitly begin a transaction
            self.conn.execute("BEGIN")
            return self.conn
        except Exception as e:
            error_msg = f"Failed to begin transaction: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "db_path": str(self.db_path),
                    "error": str(e),
                }
            )

    def commit_transaction(self, transaction: Any) -> None:
        """Commit a transaction.

        Args:
            transaction: The transaction to commit. For SQLite, this is ignored
                         as we use the connection directly.

        Raises:
            DatabaseError: If committing the transaction fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            # For SQLite, we use the connection's commit method
            self.conn.commit()
        except Exception as e:
            error_msg = f"Failed to commit transaction: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "db_path": str(self.db_path),
                    "error": str(e),
                }
            )

    def rollback_transaction(self, transaction: Any) -> None:
        """Rollback a transaction.

        Args:
            transaction: The transaction to rollback. For SQLite, this is ignored
                         as we use the connection directly.

        Raises:
            DatabaseError: If rolling back the transaction fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            # For SQLite, we use the connection's rollback method
            self.conn.rollback()
        except Exception as e:
            error_msg = f"Failed to rollback transaction: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "db_path": str(self.db_path),
                    "error": str(e),
                }
            )

    def save_metadata(self, key: str, value: Any) -> None:
        """Save metadata to the database.

        Args:
            key: The metadata key.
            value: The metadata value.

        Raises:
            DatabaseError: If saving the metadata fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            # Convert value to JSON string
            value_str = json.dumps(value, cls=DateTimeEncoder)

            # Insert or replace the metadata
            self.conn.execute(
                """
                INSERT OR REPLACE INTO metadata(key, value)
                VALUES(?, ?)
                """,
                (key, value_str),
            )
            self.conn.commit()
        except Exception as e:
            error_msg = f"Failed to save metadata: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "key": key,
                    "error": str(e),
                }
            )

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the database.

        Args:
            key: The metadata key.
            default: The default value to return if the key doesn't exist.

        Returns:
            The metadata value, or the default if not found.

        Raises:
            DatabaseError: If getting the metadata fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            cursor = self.conn.execute(
                """
                SELECT value
                FROM metadata
                WHERE key = ?
                """,
                (key,),
            )
            row = cursor.fetchone()
            if row is None:
                return default
            return json.loads(row[0])
        except Exception as e:
            error_msg = f"Failed to get metadata: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "key": key,
                    "error": str(e),
                }
            )

    def get_all_metadata(self) -> Dict[str, Any]:
        """Get all metadata from the database.

        Returns:
            A dictionary of all metadata.

        Raises:
            DatabaseError: If getting the metadata fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            cursor = self.conn.execute(
                """
                SELECT key, value
                FROM metadata
                """
            )
            metadata = {}
            for row in cursor:
                metadata[row[0]] = json.loads(row[1])
            return metadata
        except Exception as e:
            error_msg = f"Failed to get all metadata: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "error": str(e),
                }
            )

    def save_refresh_timestamp(self, source: str, timestamp: datetime) -> None:
        """Save the last refresh timestamp for a source.

        Args:
            source: The source name (e.g., 'github', 'linear').
            timestamp: The timestamp of the last refresh.

        Raises:
            DatabaseError: If saving the timestamp fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            # Convert timestamp to ISO format
            timestamp_str = timestamp.isoformat()

            # Insert or replace the timestamp
            self.conn.execute(
                """
                INSERT OR REPLACE INTO refresh_timestamps(source, timestamp)
                VALUES(?, ?)
                """,
                (source, timestamp_str),
            )
            self.conn.commit()
        except Exception as e:
            error_msg = f"Failed to save refresh timestamp: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "source": source,
                    "timestamp": timestamp.isoformat() if timestamp else None,
                    "error": str(e),
                }
            )

    def get_refresh_timestamp(self, source: str) -> Optional[datetime]:
        """Get the last refresh timestamp for a source.

        Args:
            source: The source name (e.g., 'github', 'linear').

        Returns:
            The timestamp of the last refresh, or None if not found.

        Raises:
            DatabaseError: If getting the timestamp fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            cursor = self.conn.execute(
                """
                SELECT timestamp
                FROM refresh_timestamps
                WHERE source = ?
                """,
                (source,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return datetime.fromisoformat(row[0])
        except Exception as e:
            error_msg = f"Failed to get refresh timestamp: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "source": source,
                    "error": str(e),
                }
            )

    def get_all_refresh_timestamps(self) -> Dict[str, datetime]:
        """Get all refresh timestamps.

        Returns:
            A dictionary mapping source names to refresh timestamps.

        Raises:
            DatabaseError: If getting the timestamps fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            cursor = self.conn.execute(
                """
                SELECT source, timestamp
                FROM refresh_timestamps
                """
            )
            timestamps = {}
            for row in cursor:
                timestamps[row[0]] = datetime.fromisoformat(row[1])
            return timestamps
        except Exception as e:
            error_msg = f"Failed to get all refresh timestamps: {e}"
            logger.error(error_msg)
            raise DatabaseError(
                error_msg,
                details={
                    "error": str(e),
                }
            )

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Tuple]:
        """Execute a raw SQL query on the database.

        This method allows executing arbitrary SQL queries on the database.
        It should be used with caution, as it bypasses the adapter's abstraction.

        Args:
            query: The SQL query to execute.
            params: Optional parameters for the query.

        Returns:
            A list of tuples containing the query results.

        Raises:
            GraphQueryError: If executing the query fails.
        """
        if not self.is_connected():
            raise DatabaseError("Not connected to database")

        try:
            if params:
                cursor = self.conn.execute(query, params)
            else:
                cursor = self.conn.execute(query)

            return cursor.fetchall()
        except Exception as e:
            error_msg = f"Failed to execute query: {e}"
            logger.error(error_msg)
            raise GraphQueryError(
                error_msg,
                details={
                    "query": query,
                    "params": params,
                    "error": str(e),
                }
            )
