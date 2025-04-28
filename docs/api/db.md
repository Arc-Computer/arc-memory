# Database API

The Database API provides functions for interacting with the Arc Memory knowledge graph database.

## Connection Management

### `init_db(db_path: Optional[Path] = None, test_mode: bool = False) -> sqlite3.Connection`

Initialize a database connection.

**Parameters:**
- `db_path`: Path to the database file. If None, uses the default location.
- `test_mode`: If True, creates an in-memory database for testing.

**Returns:**
- A database connection.

**Example:**
```python
from arc_memory.sql.db import init_db
from pathlib import Path

# Default location
conn = init_db()

# Custom location
conn = init_db(Path("./my-graph.db"))

# Test mode (in-memory database)
conn = init_db(test_mode=True)
```

### `get_connection(db_path: Optional[Path] = None, check_exists: bool = True) -> sqlite3.Connection`

Get a connection to the database.

**Parameters:**
- `db_path`: Path to the database file. If None, uses the default location.
- `check_exists`: If True, checks that the database file exists.

**Returns:**
- A database connection.

**Example:**
```python
from arc_memory.sql.db import get_connection
from pathlib import Path

# Default location
conn = get_connection()

# Custom location
conn = get_connection(Path("./my-graph.db"))

# Don't check if file exists (useful for new databases)
conn = get_connection(Path("./new-graph.db"), check_exists=False)
```

### `ensure_connection(conn_or_path: Union[Any, Path, str]) -> sqlite3.Connection`

Ensure we have a valid database connection. This function accepts either an existing connection or a path.

**Parameters:**
- `conn_or_path`: Either a database connection object or a path to a database file.

**Returns:**
- A valid database connection.

**Raises:**
- `DatabaseError`: If the input is neither a valid connection nor a valid path.

**Example:**
```python
from arc_memory.sql.db import ensure_connection
from pathlib import Path

# From an existing connection
conn = ensure_connection(existing_conn)

# From a path
conn = ensure_connection(Path("./my-graph.db"))

# From a string path
conn = ensure_connection("./my-graph.db")
```

## Node Operations

### `get_node_by_id(conn_or_path: Union[Any, Path, str], node_id: str) -> Optional[Dict[str, Any]]`

Get a node by its ID.

**Parameters:**
- `conn_or_path`: Either a database connection object or a path to a database file.
- `node_id`: The ID of the node.

**Returns:**
- The node as a dictionary, or None if it doesn't exist.

**Example:**
```python
from arc_memory.sql.db import get_node_by_id
from pathlib import Path

# Using a connection
node = get_node_by_id(conn, "commit:abc123")

# Using a path directly
node = get_node_by_id(Path("./my-graph.db"), "commit:abc123")

# Using a string path
node = get_node_by_id("./my-graph.db", "commit:abc123")

if node:
    print(f"Found node: {node['title']}")
else:
    print("Node not found")
```

### `get_node_count(conn_or_path: Union[Any, Path, str]) -> int`

Get the number of nodes in the database.

**Parameters:**
- `conn_or_path`: Either a database connection object or a path to a database file.

**Returns:**
- The number of nodes.

**Example:**
```python
from arc_memory.sql.db import get_node_count

# Using a connection
count = get_node_count(conn)

# Using a path directly
count = get_node_count(Path("./my-graph.db"))

print(f"Database contains {count} nodes")
```

## Edge Operations

### `get_edges_by_src(conn_or_path: Union[Any, Path, str], src_id: str, rel_type: Optional[EdgeRel] = None) -> List[Dict[str, Any]]`

Get edges by source node ID.

**Parameters:**
- `conn_or_path`: Either a database connection object or a path to a database file.
- `src_id`: The ID of the source node.
- `rel_type`: Optional relationship type to filter by.

**Returns:**
- A list of edges as dictionaries.

**Example:**
```python
from arc_memory.sql.db import get_edges_by_src
from arc_memory.schema.models import EdgeRel

# Get all edges from a node
edges = get_edges_by_src(conn, "commit:abc123")

# Filter by relationship type
edges = get_edges_by_src(conn, "commit:abc123", rel_type=EdgeRel.MODIFIES)

for edge in edges:
    print(f"{edge['src']} {edge['rel']} {edge['dst']}")
```

### `get_edges_by_dst(conn_or_path: Union[Any, Path, str], dst_id: str, rel_type: Optional[EdgeRel] = None) -> List[Dict[str, Any]]`

Get edges by destination node ID.

**Parameters:**
- `conn_or_path`: Either a database connection object or a path to a database file.
- `dst_id`: The ID of the destination node.
- `rel_type`: Optional relationship type to filter by.

**Returns:**
- A list of edges as dictionaries.

**Example:**
```python
from arc_memory.sql.db import get_edges_by_dst
from arc_memory.schema.models import EdgeRel

# Get all edges to a node
edges = get_edges_by_dst(conn, "file:src/main.py")

# Filter by relationship type
edges = get_edges_by_dst(conn, "file:src/main.py", rel_type=EdgeRel.MODIFIES)

for edge in edges:
    print(f"{edge['src']} {edge['rel']} {edge['dst']}")
```

### `get_edge_count(conn_or_path: Union[Any, Path, str]) -> int`

Get the number of edges in the database.

**Parameters:**
- `conn_or_path`: Either a database connection object or a path to a database file.

**Returns:**
- The number of edges.

**Example:**
```python
from arc_memory.sql.db import get_edge_count

# Using a connection
count = get_edge_count(conn)

# Using a path directly
count = get_edge_count(Path("./my-graph.db"))

print(f"Database contains {count} edges")
```

## Search Operations

### `search_entities(conn_or_path: Union[Any, Path, str], query: str, limit: int = 10) -> List[Dict[str, Any]]`

Search for nodes by title or body.

**Parameters:**
- `conn_or_path`: Either a database connection object or a path to a database file.
- `query`: The search query.
- `limit`: Maximum number of results to return.

**Returns:**
- A list of matching nodes as dictionaries.

**Example:**
```python
from arc_memory.sql.db import search_entities

# Search for nodes containing "authentication"
results = search_entities(conn, "authentication", limit=5)

for node in results:
    print(f"{node['type']}: {node['title']}")
```

## Database Utilities

### `compress_db(db_path: Optional[Path] = None, output_path: Optional[Path] = None) -> Path`

Compress the database file using zstandard.

**Parameters:**
- `db_path`: Path to the database file. If None, uses the default location.
- `output_path`: Path to save the compressed file. If None, uses `db_path` with `.zst` extension.

**Returns:**
- The path to the compressed file.

**Example:**
```python
from arc_memory.sql.db import compress_db
from pathlib import Path

# Compress the default database
compressed_path = compress_db()

# Compress a specific database
compressed_path = compress_db(Path("./my-graph.db"))

# Compress to a specific output path
compressed_path = compress_db(Path("./my-graph.db"), Path("./backup.zst"))
```

### `decompress_db(compressed_path: Optional[Path] = None, output_path: Optional[Path] = None) -> Path`

Decompress a compressed database file.

**Parameters:**
- `compressed_path`: Path to the compressed file. If None, uses the default location with `.zst` extension.
- `output_path`: Path to save the decompressed file. If None, uses `compressed_path` without `.zst` extension.

**Returns:**
- The path to the decompressed file.

**Example:**
```python
from arc_memory.sql.db import decompress_db
from pathlib import Path

# Decompress the default compressed database
db_path = decompress_db()

# Decompress a specific compressed file
db_path = decompress_db(Path("./my-graph.db.zst"))

# Decompress to a specific output path
db_path = decompress_db(Path("./backup.zst"), Path("./restored.db"))
```

## Best Practices

### Connection Management

1. **Use `ensure_connection` for flexible code:**
   ```python
   from arc_memory.sql.db import ensure_connection, get_node_by_id
   
   def my_function(db_path_or_conn):
       conn = ensure_connection(db_path_or_conn)
       # Now you can use conn safely
       return get_node_by_id(conn, "node:123")
   ```

2. **Close connections when done:**
   ```python
   from contextlib import closing
   from arc_memory.sql.db import get_connection
   
   with closing(get_connection(db_path)) as conn:
       # Use conn within this block
       node = get_node_by_id(conn, "node:123")
   # Connection is automatically closed here
   ```

3. **Reuse connections for multiple operations:**
   ```python
   conn = get_connection(db_path)
   
   # Multiple operations with the same connection
   nodes = get_node_by_id(conn, "node:123")
   edges = get_edges_by_src(conn, "node:123")
   
   # Close when done
   conn.close()
   ```

4. **Use test mode for unit tests:**
   ```python
   def test_my_function():
       # In-memory database that doesn't touch the filesystem
       conn = init_db(test_mode=True)
       
       # Add test data
       add_nodes_and_edges(conn, test_nodes, test_edges)
       
       # Test your function
       result = my_function(conn)
       
       # No need to close in-memory test databases
   ```
