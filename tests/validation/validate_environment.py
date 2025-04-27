#!/usr/bin/env python
"""
Validation script for Arc Memory environment.

This script checks if the Arc Memory environment is properly set up.
It can be run during CI/CD or by users to diagnose issues.

Usage:
    python -m tests.validation.validate_environment

Exit codes:
    0: All checks passed
    1: Dependency check failed
    2: Python version check failed
    3: Database initialization failed
    4: Database operations failed
"""

import sys
from pathlib import Path

from arc_memory.dependencies import validate_dependencies, validate_python_version
from arc_memory.errors import ArcError, DatabaseError, DependencyError
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType
from arc_memory.sql.db import add_nodes_and_edges, get_edge_count, get_node_count, init_db


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...")
    try:
        # Check core dependencies first
        missing = validate_dependencies(include_optional=False, raise_error=True)
        print("✅ All required core dependencies are installed.")

        # Check optional dependencies but don't fail if they're missing
        optional_missing = validate_dependencies(include_optional=True, raise_error=False)
        if any(category != "core" for category in optional_missing):
            print("⚠️ Some optional dependencies are missing. Functionality may be limited.")
            for category, deps in optional_missing.items():
                if category != "core":
                    print(f"  - Missing {category} dependencies: {', '.join(deps)}")
        else:
            print("✅ All optional dependencies are installed.")

        return True
    except DependencyError as e:
        print(f"❌ Dependency check failed: {e}")
        return False


def check_python_version():
    """Check if the Python version meets the requirements."""
    print("Checking Python version...")
    try:
        validate_python_version(min_version=(3, 10, 0), raise_error=True)
        print(f"✅ Python version {sys.version.split()[0]} meets the requirements.")
        return True
    except DependencyError as e:
        print(f"❌ Python version check failed: {e}")
        return False


def check_database_initialization():
    """Check if the database can be initialized."""
    print("Checking database initialization...")
    try:
        # Try to initialize the database in test mode
        conn = init_db(test_mode=True)
        print("✅ Database initialization successful (test mode).")

        # Try to initialize a real database in a temporary location
        import tempfile
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / "test.db"

        conn_real = init_db(db_path)
        print(f"✅ Database initialization successful (real mode at {db_path}).")

        temp_dir.cleanup()
        return True
    except DatabaseError as e:
        print(f"❌ Database initialization failed: {e}")
        return False


def check_database_operations():
    """Check if basic database operations work."""
    print("Checking database operations...")
    try:
        # Initialize the database in test mode
        conn = init_db(test_mode=True)

        # Check initial counts
        node_count = get_node_count(conn)
        edge_count = get_edge_count(conn)
        print(f"Initial counts: {node_count} nodes, {edge_count} edges")

        # Add some test data
        from datetime import datetime

        nodes = [
            Node(
                id="test:1",
                type=NodeType.COMMIT,
                title="Test Node",
                body="Test Body",
                ts=datetime.now(),
                extra={}
            )
        ]

        edges = [
            Edge(
                src="test:1",
                dst="test:2",
                rel=EdgeRel.MENTIONS,
                properties={}
            )
        ]

        # Add the data
        add_nodes_and_edges(conn, nodes, edges)

        # Check the counts again
        new_node_count = get_node_count(conn)
        new_edge_count = get_edge_count(conn)
        print(f"After adding data: {new_node_count} nodes, {new_edge_count} edges")

        if new_node_count > node_count and new_edge_count > edge_count:
            print("✅ Database operations successful.")
            return True
        else:
            print("❌ Database operations failed: counts did not increase.")
            return False
    except ArcError as e:
        print(f"❌ Database operations failed: {e}")
        return False


def main():
    """Run all validation checks."""
    print("Running Arc Memory environment validation...")
    print("=" * 50)

    # Check dependencies
    deps_ok = check_dependencies()
    print()

    # Check Python version
    python_ok = check_python_version()
    print()

    # Check database initialization
    db_init_ok = check_database_initialization()
    print()

    # Check database operations
    db_ops_ok = check_database_operations()
    print()

    # Summary
    print("=" * 50)
    print("Validation Summary:")
    print(f"Dependencies: {'✅ PASS' if deps_ok else '❌ FAIL'}")
    print(f"Python Version: {'✅ PASS' if python_ok else '❌ FAIL'}")
    print(f"Database Initialization: {'✅ PASS' if db_init_ok else '❌ FAIL'}")
    print(f"Database Operations: {'✅ PASS' if db_ops_ok else '❌ FAIL'}")
    print("=" * 50)

    # Exit with appropriate code
    if not deps_ok:
        sys.exit(1)
    elif not python_ok:
        sys.exit(2)
    elif not db_init_ok:
        sys.exit(3)
    elif not db_ops_ok:
        sys.exit(4)
    else:
        print("All checks passed! Your Arc Memory environment is properly set up.")
        sys.exit(0)


if __name__ == "__main__":
    main()
