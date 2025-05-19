import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import datetime

from arc_memory.ingest.notion import NotionIngestor, NotionClient
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel, DocumentNode
from arc_memory.errors import IngestError, NotionAuthError


class TestNotionIngestor(unittest.TestCase):

    @patch('arc_memory.ingest.notion.get_notion_token')
    @patch('arc_memory.ingest.notion.NotionClient')
    def setUp(self, MockNotionClient, mock_get_notion_token):
        self.mock_notion_client = MockNotionClient.return_value
        self.mock_get_notion_token = mock_get_notion_token

        # Default mock behaviors
        self.mock_get_notion_token.return_value = "fake_token"
        
        # Mock the search to return empty by default to avoid processing if not overridden
        self.mock_notion_client.search.return_value = {"results": [], "has_more": False, "next_cursor": None}


    def test_ingest_with_database_ids(self):
        ingestor = NotionIngestor()
        source_configs = {
            "notion": {
                "database_ids": ["db-id-1"]
            }
        }

        mock_db_data_1 = {
            "id": "db-id-1", "object": "database",
            "title": [{"type": "text", "text": {"content": "Test DB 1"}}],
            "created_time": "2023-01-01T10:00:00.000Z",
            "last_edited_time": "2023-01-01T11:00:00.000Z",
            "url": "https://www.notion.so/db-id-1",
            "parent": {"type": "workspace", "workspace": True}
        }
        
        mock_page_in_db_1 = {
            "id": "page-in-db-1", "object": "page",
            "properties": {"title": {"title": [{"type": "text", "text": {"content": "Page in DB 1"}}]}},
            "created_time": "2023-01-01T10:05:00.000Z",
            "last_edited_time": "2023-01-01T11:05:00.000Z",
            "url": "https://www.notion.so/page-in-db-1",
            "parent": {"type": "database_id", "database_id": "db-id-1"}
        }

        self.mock_notion_client.get_database.side_effect = lambda db_id: {
            "db-id-1": mock_db_data_1
        }.get(db_id, Exception(f"Database {db_id} not found"))

        self.mock_notion_client.query_database.side_effect = lambda database_id, **kwargs: {
            "db-id-1": {"results": [mock_page_in_db_1], "has_more": False, "next_cursor": None}
        }.get(database_id, {"results": [], "has_more": False, "next_cursor": None})
        
        # Mock get_block_children to return empty for simplicity in this specific test
        self.mock_notion_client.get_block_children.return_value = {"results": [], "has_more": False}

        nodes, edges, metadata = ingestor.ingest(
            repo_path=Path("."),
            **(source_configs["notion"]) # Pass specific config for notion
        )

        # Assertions
        self.assertIsNotNone(nodes)
        self.assertIsNotNone(edges)
        self.assertIsNotNone(metadata)

        # Verify get_database was called for the specified ID
        self.mock_notion_client.get_database.assert_called_once_with("db-id-1")
        
        # Verify query_database was called for the specified database
        self.mock_notion_client.query_database.assert_called_once_with("db-id-1", start_cursor=None)

        # Assert that client.search was NOT called because specific IDs were provided
        self.mock_notion_client.search.assert_not_called()
        
        self.assertEqual(metadata.get("database_count"), 1)
        # The page_nodes count will be 1 (from the database) because _process_databases calls _fetch_database_pages,
        # which in turn creates page nodes. The _process_pages is also called, but with an empty list if no page_ids are given.
        self.assertEqual(metadata.get("page_count"), 1) 

        node_ids = [n.id for n in nodes]
        self.assertIn("notion:database:db-id-1", node_ids)
        self.assertIn("notion:page:page-in-db-1", node_ids)
        
        edge_tuples = [(e.src, e.dst, e.rel) for e in edges]
        self.assertIn(("notion:database:db-id-1", "notion:page:page-in-db-1", EdgeRel.CONTAINS), edge_tuples)


if __name__ == '__main__':
    unittest.main()
