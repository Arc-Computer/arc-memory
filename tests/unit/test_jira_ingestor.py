import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from arc_memory.ingest.jira import JiraIngestor, JiraClient
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel, IssueNode
from arc_memory.errors import IngestError, JiraAuthError


class TestJiraIngestor(unittest.TestCase):

    @patch('arc_memory.ingest.jira.get_cloud_id_from_env')
    @patch('arc_memory.ingest.jira.get_jira_token')
    @patch('arc_memory.ingest.jira.JiraClient')
    def setUp(self, MockJiraClient, mock_get_jira_token, mock_get_cloud_id_from_env):
        self.mock_jira_client = MockJiraClient.return_value
        self.mock_get_jira_token = mock_get_jira_token
        self.mock_get_cloud_id_from_env = mock_get_cloud_id_from_env

        # Default mock behaviors
        self.mock_get_jira_token.return_value = "fake_token"
        self.mock_get_cloud_id_from_env.return_value = "fake_cloud_id"
        self.mock_jira_client.get_current_user.return_value = {"displayName": "Test User"}

    def test_ingest_successful_with_project_keys(self):
        ingestor = JiraIngestor()
        source_configs = {
            "jira": {
                "project_keys": ["PROJ1"]
            }
        }

        # Mock project fetching
        mock_project_data_proj1 = {
            "id": "10001", "key": "PROJ1", "name": "Project 1", "description": "Test Project 1",
            "lead": {"displayName": "Lead User", "accountId": "123"}
        }
        mock_project_data_proj2 = { # This project should be filtered out
            "id": "10002", "key": "PROJ2", "name": "Project 2", "description": "Test Project 2",
            "lead": {"displayName": "Lead User 2", "accountId": "456"}
        }
        # Simulate the behavior of _fetch_all_projects (which is called internally by ingest)
        # If JiraIngestor directly calls client.get_projects, mock that instead.
        # Assuming _fetch_all_projects is an internal helper that uses client.get_projects:
        
        # Let's assume the ingestor's _fetch_all_projects is what we need to control for project filtering
        # or that the filtering logic directly uses the result of client.get_projects.
        # For this example, we'll mock what the client returns from get_projects
        self.mock_jira_client.get_projects.return_value = {
            "values": [mock_project_data_proj1, mock_project_data_proj2],
            "total": 2,
            "isLast": True
        }
        
        # Mock issue fetching for PROJ1
        mock_issue_data_proj1 = {
            "key": "PROJ1-1",
            "fields": {
                "summary": "Test Issue for PROJ1", "description": "Details",
                "created": "2023-01-01T10:00:00.000+0000", "updated": "2023-01-02T10:00:00.000+0000",
                "status": {"name": "Open"}, "issuetype": {"name": "Bug"}, "priority": {"name": "High"},
                "labels": ["test-label"]
            }
        }
        self.mock_jira_client.search_issues.return_value = {
            "issues": [mock_issue_data_proj1],
            "total": 1,
            "isLast": True
        }

        nodes, edges, metadata = ingestor.ingest(
            repo_path=Path("."),
            **(source_configs["jira"]) # Pass specific config for jira
        )

        # Assertions
        self.assertIsNotNone(nodes)
        self.assertIsNotNone(edges)
        self.assertIsNotNone(metadata)

        # Check that only PROJ1 was processed
        # This might be checked by looking at the project nodes created, or logs,
        # or specific metadata returned. For this example, let's check metadata.
        self.assertEqual(metadata.get("project_count"), 1)
        
        project_node_ids = [n.id for n in nodes if n.type == "jira_project"]
        self.assertIn("jira:project:PROJ1", project_node_ids)
        self.assertNotIn("jira:project:PROJ2", project_node_ids) # Ensure PROJ2 was filtered out

        issue_node_ids = [n.id for n in nodes if n.type == NodeType.ISSUE]
        self.assertIn("jira:issue:PROJ1-1", issue_node_ids)
        
        # Verify client.search_issues was called with JQL for PROJ1
        self.mock_jira_client.search_issues.assert_called_once()
        args, kwargs = self.mock_jira_client.search_issues.call_args
        self.assertIn("project = PROJ1", kwargs.get("jql", ""))

        # More detailed assertions on node/edge content can be added here
        self.assertTrue(any(n.title == "Project 1" for n in nodes))
        self.assertTrue(any(n.title == "Test Issue for PROJ1" for n in nodes))


if __name__ == '__main__':
    unittest.main()
