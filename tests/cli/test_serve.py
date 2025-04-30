"""Tests for the serve command."""

import unittest
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from arc_memory.cli import app

runner = CliRunner()


class TestServeCommand(unittest.TestCase):
    """Tests for the serve command."""

    @patch("arc_memory.cli.serve.subprocess.run")
    @patch("arc_memory.cli.serve.importlib.util.find_spec")
    @patch("arc_memory.cli.serve.get_config")
    def test_serve_start_default(self, mock_get_config, mock_find_spec, mock_run):
        """Test the serve start command with default settings."""
        # Setup mocks
        mock_get_config.return_value = {
            "mcp": {
                "host": "127.0.0.1",
                "port": 8000
            }
        }
        mock_find_spec.return_value = MagicMock()  # MCP server is installed

        # Run command
        result = runner.invoke(app, ["serve", "start"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Starting Arc MCP Server", result.stdout)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0:3], [unittest.mock.ANY, "-m", "arc_mcp_server"])

    @patch("arc_memory.cli.serve.subprocess.run")
    @patch("arc_memory.cli.serve.importlib.util.find_spec")
    @patch("arc_memory.cli.serve.get_config")
    def test_serve_start_custom_host_port(self, mock_get_config, mock_find_spec, mock_run):
        """Test the serve start command with custom host and port."""
        # Setup mocks
        mock_get_config.return_value = {
            "mcp": {
                "host": "127.0.0.1",
                "port": 8000
            }
        }
        mock_find_spec.return_value = MagicMock()  # MCP server is installed

        # Run command
        result = runner.invoke(app, ["serve", "start", "--host", "0.0.0.0", "--port", "8080"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Starting Arc MCP Server", result.stdout)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0:3], [unittest.mock.ANY, "-m", "arc_mcp_server"])
        self.assertIn("--host", cmd)
        self.assertIn("0.0.0.0", cmd)
        self.assertIn("--port", cmd)
        self.assertIn("8080", cmd)

    @patch("arc_memory.cli.serve.subprocess.run")
    @patch("arc_memory.cli.serve.importlib.util.find_spec")
    @patch("arc_memory.cli.serve.get_config")
    def test_serve_start_stdio(self, mock_get_config, mock_find_spec, mock_run):
        """Test the serve start command with stdio mode."""
        # Setup mocks
        mock_get_config.return_value = {
            "mcp": {
                "host": "127.0.0.1",
                "port": 8000
            }
        }
        mock_find_spec.return_value = MagicMock()  # MCP server is installed

        # Run command
        result = runner.invoke(app, ["serve", "start", "--stdio"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Starting Arc MCP Server", result.stdout)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0:3], [unittest.mock.ANY, "-m", "arc_mcp_server"])
        self.assertIn("--stdio", cmd)

    @patch("arc_memory.cli.serve.subprocess.check_call")
    @patch("arc_memory.cli.serve.subprocess.run")
    @patch("arc_memory.cli.serve.importlib.util.find_spec")
    @patch("arc_memory.cli.serve.get_config")
    def test_serve_start_install_mcp(self, mock_get_config, mock_find_spec, mock_run, mock_check_call):
        """Test the serve start command when MCP server is not installed."""
        # Setup mocks
        mock_get_config.return_value = {
            "mcp": {
                "host": "127.0.0.1",
                "port": 8000
            }
        }
        mock_find_spec.return_value = None  # MCP server is not installed

        # Run command
        result = runner.invoke(app, ["serve", "start"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("arc-mcp-server not found. Installing...", result.stdout)
        mock_check_call.assert_called_once()
        mock_run.assert_called_once()

    @patch("socket.socket")
    @patch("arc_memory.cli.serve.get_config")
    def test_serve_status_running(self, mock_get_config, mock_socket):
        """Test the serve status command when the server is running."""
        # Setup mocks
        mock_get_config.return_value = {
            "mcp": {
                "host": "127.0.0.1",
                "port": 8000
            }
        }
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect_ex.return_value = 0  # Server is running
        mock_socket.return_value = mock_socket_instance

        # Run command
        result = runner.invoke(app, ["serve", "status"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MCP server is running on 127.0.0.1:8000", result.stdout)

    @patch("socket.socket")
    @patch("arc_memory.cli.serve.get_config")
    def test_serve_status_not_running(self, mock_get_config, mock_socket):
        """Test the serve status command when the server is not running."""
        # Setup mocks
        mock_get_config.return_value = {
            "mcp": {
                "host": "127.0.0.1",
                "port": 8000
            }
        }
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect_ex.return_value = 1  # Server is not running
        mock_socket.return_value = mock_socket_instance

        # Run command
        result = runner.invoke(app, ["serve", "status"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MCP server is not running on 127.0.0.1:8000", result.stdout)
        self.assertIn("Run arc serve start to start the server", result.stdout)
