import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
from pathlib import Path
import sqlite3 # For direct DB inspection if needed

from arc_memory.sdk import Arc
from arc_memory.sdk.errors import BuildError
from arc_memory.errors import IngestError, JiraAuthError, NotionAuthError # For simulating errors


class TestSDKBuild(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for the database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_arc_sdk.db"
        
        # Initialize Arc instance with a temporary DB path
        # We also need a dummy repo_path for Arc initialization
        self.dummy_repo_path = Path(self.test_dir) / "dummy_repo"
        self.dummy_repo_path.mkdir()
        
        # Initialize Arc, it will create the DB at self.db_path
        # We need to ensure the .arc directory mechanism doesn't interfere
        # by forcing the db_path through connection_params
        self.arc = Arc(
            repo_path=self.dummy_repo_path, 
            connection_params={"db_path": str(self.db_path)}
        )

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    @patch('arc_memory.ingest.jira.JiraClient')
    @patch('arc_memory.ingest.jira.get_jira_token', return_value="fake_token")
    @patch('arc_memory.ingest.jira.get_cloud_id_from_env', return_value="fake_cloud_id")
    def test_build_with_jira_source_config_and_summary(self, mock_get_cloud_id, mock_get_token, MockJiraClient):
        mock_jira_client_instance = MockJiraClient.return_value
        mock_jira_client_instance.get_current_user.return_value = {"displayName": "Test User"}

        # Configure mock JiraClient to return minimal data
        mock_project_data = {
            "id": "10001", "key": "TESTPROJ", "name": "Test Project",
            "lead": {"displayName": "Lead User", "accountId": "123"}
        }
        mock_issue_data = {
            "key": "TESTPROJ-1",
            "fields": {
                "summary": "Test Issue 1", "description": "A test issue.",
                "created": "2023-01-01T12:00:00.000+0000", "updated": "2023-01-01T12:00:00.000+0000",
                "status": {"name": "To Do"}, "issuetype": {"name": "Task"}
            }
        }
        
        # Mock _fetch_all_projects behavior or the client method it uses
        # Assuming JiraIngestor._fetch_all_projects calls client.get_projects
        mock_jira_client_instance.get_projects.return_value = {
            "values": [mock_project_data], "total": 1, "isLast": True
        }
        # Mock _fetch_all_issues behavior or the client method it uses
        # Assuming JiraIngestor._fetch_all_issues calls client.search_issues
        mock_jira_client_instance.search_issues.return_value = {
            "issues": [mock_issue_data], "total": 1, "isLast": True
        }

        source_configs = {
            "jira": {
                "project_keys": ["TESTPROJ"]
                # cloud_id will use the mocked get_cloud_id_from_env
            }
        }

        # include_jira=True is important, or source_configs for jira might be ignored
        # if the default for include_jira is False in Arc.build()
        # However, having "jira" in source_configs should implicitly include it.
        # For clarity, one might set include_jira=True.
        # For this test, we assume the presence of "jira" in source_configs is enough.
        # We'll also disable other ingestors to simplify the test.
        build_result = self.arc.build(
            source_configs=source_configs,
            include_github=False, 
            include_linear=False,
            include_adr=False, # Assuming ADR is another default ingestor
            include_architecture=False # Assuming architecture is processed
        )

        self.assertIsNotNone(build_result)
        
        # Assert the structure of ingestor_summary
        ingestor_summary = build_result.get("ingestor_summary", [])
        jira_summary = next((s for s in ingestor_summary if s["name"] == "jira"), None)
        
        self.assertIsNotNone(jira_summary, "Jira summary not found in build results")
        self.assertEqual(jira_summary["status"], "success")
        
        # Expected: 1 project node, 1 issue node
        self.assertEqual(jira_summary["nodes_processed"], 2) 
        # Expected: 1 PART_OF edge (issue to project)
        self.assertEqual(jira_summary["edges_processed"], 1) 
        self.assertIsNone(jira_summary["error_message"])

        # Check total_nodes_added in the main result
        # This depends on other default ingestors (like 'git'). 
        # For an isolated test, ensure only Jira runs or account for others.
        # If only Jira ran (and assuming git ingestor is minimal/empty for dummy_repo):
        # We expect 2 nodes from Jira + potentially 1 from git (repo node) + 1 from default repo if any.
        # Let's focus on Jira's contribution being present.
        # A more robust check would be to query the DB for these specific nodes.
        self.assertGreaterEqual(build_result.get("total_nodes_added", 0), 2)


    @patch('arc_memory.ingest.jira.JiraClient')
    @patch('arc_memory.ingest.jira.get_jira_token', return_value="fake_token")
    @patch('arc_memory.ingest.jira.get_cloud_id_from_env', return_value="fake_cloud_id")
    def test_build_jira_ingestor_failure_reporting(self, mock_get_cloud_id, mock_get_token, MockJiraClient):
        mock_jira_client_instance = MockJiraClient.return_value
        
        # Simulate an API error during project fetching
        mock_jira_client_instance.get_current_user.side_effect = JiraAuthError("Failed to authenticate with Jira API")

        source_configs = {
            "jira": {
                "project_keys": ["ANYPROJ"]
            }
        }
        
        # Disable other ingestors to focus on Jira failure
        build_result = self.arc.build(
            source_configs=source_configs,
            include_github=False,
            include_linear=False,
            include_adr=False,
            include_architecture=False
        )

        self.assertIsNotNone(build_result)
        ingestor_summary = build_result.get("ingestor_summary", [])
        jira_summary = next((s for s in ingestor_summary if s["name"] == "jira"), None)

        self.assertIsNotNone(jira_summary, "Jira summary not found")
        self.assertEqual(jira_summary["status"], "failure")
        self.assertEqual(jira_summary["nodes_processed"], 0)
        self.assertEqual(jira_summary["edges_processed"], 0)
        self.assertIn("Failed to authenticate with Jira API", jira_summary["error_message"])
        
        # Total nodes should not include nodes from failed Jira ingestor
        # It might include nodes from other successful default ingestors (e.g., git)
        git_summary = next((s for s in ingestor_summary if s["name"] == "git"), None)
        expected_total_nodes = 0
        if git_summary and git_summary['status'] == 'success':
            expected_total_nodes += git_summary['nodes_processed']
        
        self.assertEqual(build_result.get("total_nodes_added", 0), expected_total_nodes)


if __name__ == '__main__':
    unittest.main()
