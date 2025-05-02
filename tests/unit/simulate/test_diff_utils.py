"""Tests for the diff analysis utilities."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Import core implementation functions from diff_utils
from arc_memory.simulate.diff_utils import (
    GitError,
    analyze_diff,
    load_diff_from_file,
    map_files_to_services,
    parse_rev_range,
    serialize_diff,
)

# Import wrapper functions from diff
from arc_memory.simulate.diff import (
    analyze_changes,
    extract_diff,
    load_diff_from_file as wrapper_load_diff_from_file,
    save_diff_to_file,
)


# Tests for core implementation (diff_utils.py)

def test_parse_rev_range():
    """Test parsing Git revision ranges."""
    # Test a standard range
    start, end = parse_rev_range("HEAD~1..HEAD")
    assert start == "HEAD~1"
    assert end == "HEAD"

    # Test a single commit
    start, end = parse_rev_range("HEAD")
    assert start is None
    assert end == "HEAD"

    # Test an empty string
    start, end = parse_rev_range("")
    assert start is None
    assert end == ""


def test_map_files_to_services():
    """Test mapping files to services."""
    # Test Python files
    files = ["app.py", "tests/test_app.py"]
    services = map_files_to_services(files)
    assert "python-service" in services

    # Test JavaScript files
    files = ["app.js", "src/components/App.jsx"]
    services = map_files_to_services(files)
    assert "frontend-service" in services

    # Test API files
    files = ["api/users.py", "src/rest/endpoints.js"]
    services = map_files_to_services(files)
    assert "api-service" in services

    # Test database files
    files = ["db/models.py", "src/sql/queries.js"]
    services = map_files_to_services(files)
    assert "database-service" in services

    # Test unknown files
    files = ["unknown.xyz"]
    services = map_files_to_services(files)
    assert "unknown-service" in services


def test_load_diff_from_file():
    """Test loading a diff from a file."""
    # Create a temporary diff file
    diff_data = {
        "files": [
            {
                "path": "app.py",
                "insertions": 10,
                "deletions": 5,
                "status": "modified"
            }
        ],
        "commit_count": 1,
        "range": "HEAD~1..HEAD"
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(diff_data, f)
        temp_path = f.name

    try:
        # Test loading the diff
        loaded_diff = load_diff_from_file(Path(temp_path))
        assert loaded_diff == diff_data

        # Test loading a non-existent file
        with pytest.raises(FileNotFoundError):
            load_diff_from_file(Path("non_existent_file.json"))

        # Test loading an invalid JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json")
            invalid_path = f.name

        with pytest.raises(json.JSONDecodeError):
            load_diff_from_file(Path(invalid_path))

        os.unlink(invalid_path)

        # Test loading a file with invalid diff format
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"not_a_diff": True}, f)
            invalid_format_path = f.name

        with pytest.raises(ValueError):
            load_diff_from_file(Path(invalid_format_path))

        os.unlink(invalid_format_path)

    finally:
        # Clean up
        os.unlink(temp_path)


@mock.patch("arc_memory.simulate.causal.derive_causal")
def test_analyze_diff(mock_derive_causal):
    """Test analyzing a diff to identify affected services."""
    # Create a simple diff
    diff_data = {
        "files": [
            {
                "path": "app.py",
                "insertions": 10,
                "deletions": 5,
                "status": "modified"
            },
            {
                "path": "api/users.py",
                "insertions": 20,
                "deletions": 10,
                "status": "modified"
            }
        ],
        "commit_count": 1,
        "range": "HEAD~1..HEAD"
    }

    # Mock the causal graph derivation to raise an exception
    # This will force the function to fall back to the simple mapping
    mock_derive_causal.side_effect = Exception("Test exception")

    # Test analyzing the diff
    services = analyze_diff(diff_data, "dummy_db_path")
    assert "python-service" in services
    assert "api-service" in services


@mock.patch("arc_memory.simulate.diff_utils.Repo")
def test_serialize_diff(mock_repo):
    """Test serializing a diff from Git."""
    # Mock the Git repository
    mock_repo_instance = mock.MagicMock()
    mock_repo.return_value = mock_repo_instance

    # Mock the commits
    mock_commit1 = mock.MagicMock()
    mock_commit1.hexsha = "commit1"
    mock_commit1.stats.files = {
        "app.py": {"insertions": 10, "deletions": 5}
    }

    mock_commit2 = mock.MagicMock()
    mock_commit2.hexsha = "commit2"
    mock_commit2.stats.files = {
        "api/users.py": {"insertions": 20, "deletions": 10}
    }

    mock_repo_instance.iter_commits.return_value = [mock_commit1, mock_commit2]

    # Mock the diff
    mock_diff1 = mock.MagicMock()
    mock_diff1.a_path = "app.py"
    mock_diff1.b_path = None
    mock_diff1.new_file = False
    mock_diff1.deleted_file = False
    mock_diff1.renamed = False

    mock_diff2 = mock.MagicMock()
    mock_diff2.a_path = "api/users.py"
    mock_diff2.b_path = None
    mock_diff2.new_file = False
    mock_diff2.deleted_file = False
    mock_diff2.renamed = False

    mock_diff_index = [mock_diff1, mock_diff2]

    # Mock the parent commit
    mock_parent = mock.MagicMock()
    mock_commit1.parents = [mock_parent]
    mock_commit1.diff.return_value = mock_diff_index

    mock_commit2.parents = [mock_parent]
    mock_commit2.diff.return_value = mock_diff_index

    # Test serializing the diff
    with mock.patch("os.getcwd", return_value="/tmp"):
        with mock.patch("pathlib.Path.cwd", return_value=Path("/tmp")):
            diff = serialize_diff("HEAD~1..HEAD")

    # Verify the result
    assert diff["commit_count"] == 2
    assert diff["range"] == "HEAD~1..HEAD"
    assert diff["start_commit"] == "commit2"
    assert diff["end_commit"] == "commit1"
    assert "timestamp" in diff
    assert len(diff["files"]) == 2
    assert diff["stats"]["files_changed"] == 2
    assert diff["stats"]["insertions"] == 30
    assert diff["stats"]["deletions"] == 15

    # Test error handling
    mock_repo.side_effect = Exception("Test error")
    with pytest.raises(GitError):
        with mock.patch("os.getcwd", return_value="/tmp"):
            with mock.patch("pathlib.Path.cwd", return_value=Path("/tmp")):
                serialize_diff("HEAD~1..HEAD")


# Tests for wrapper functions (diff.py)

@mock.patch("arc_memory.simulate.diff_utils.serialize_diff")
def test_extract_diff(mock_serialize_diff):
    """Test extract_diff wrapper function."""
    # Setup mock data
    mock_diff_data = {
        "files": [{"path": "app.py"}],
        "commit_count": 1
    }
    mock_serialize_diff.return_value = mock_diff_data
    
    # Define a mock progress callback
    progress_calls = []
    def mock_progress_callback(message, progress):
        progress_calls.append((message, progress))
    
    # Call the function
    result = extract_diff("HEAD~1..HEAD", progress_callback=mock_progress_callback)
    
    # Verify the result
    assert result == mock_diff_data
    assert len(progress_calls) == 2
    assert "Extracting diff" in progress_calls[0][0]
    assert "Successfully extracted" in progress_calls[1][0]
    
    # Verify the mock was called correctly
    mock_serialize_diff.assert_called_once_with("HEAD~1..HEAD", repo_path=None)


@mock.patch("arc_memory.simulate.diff_utils.analyze_diff")
def test_analyze_changes(mock_analyze_diff):
    """Test analyze_changes wrapper function."""
    # Setup mock data
    mock_services = ["service1", "service2"]
    mock_analyze_diff.return_value = mock_services
    
    diff_data = {
        "files": [{"path": "app.py"}],
        "commit_count": 1
    }
    
    # Define a mock progress callback
    progress_calls = []
    def mock_progress_callback(message, progress):
        progress_calls.append((message, progress))
    
    # Call the function
    result = analyze_changes(diff_data, "db_path", progress_callback=mock_progress_callback)
    
    # Verify the result
    assert result == mock_services
    assert len(progress_calls) == 2
    assert "Analyzing diff" in progress_calls[0][0]
    assert "Identified" in progress_calls[1][0]
    
    # Verify the mock was called correctly
    mock_analyze_diff.assert_called_once_with(diff_data, "db_path")


def test_save_and_load_diff():
    """Test saving and loading diff data."""
    # Create test data
    diff_data = {
        "files": [
            {
                "path": "app.py",
                "insertions": 10,
                "deletions": 5,
                "status": "modified"
            }
        ],
        "commit_count": 1,
        "range": "HEAD~1..HEAD"
    }
    
    try:
        # Test saving the diff
        diff_path = save_diff_to_file(diff_data)
        
        # Test loading the diff using the wrapper
        loaded_diff = wrapper_load_diff_from_file(diff_path)
        
        # Verify the data is the same
        assert loaded_diff == diff_data
        
    finally:
        # Clean up
        if 'diff_path' in locals() and diff_path.exists():
            os.unlink(diff_path)
