"""Notion ingestion for Arc Memory."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from arc_memory.auth.notion import get_notion_token
from arc_memory.errors import IngestError, NotionAuthError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import DocumentNode, Edge, EdgeRel, Node, NodeType

logger = get_logger(__name__)

# Constants
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"  # Notion API version
USER_AGENT = "Arc-Memory/0.7.4"


class NotionClient:
    """Client for Notion API."""

    def __init__(self, token: str):
        """Initialize the Notion client.

        Args:
            token: Notion token to use for API calls.
        """
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
            "User-Agent": USER_AGENT,
        }

    def _make_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to the Notion API.

        Args:
            method: HTTP method to use.
            endpoint: API endpoint to call.
            params: Query parameters.
            data: Request body.

        Returns:
            Response data.

        Raises:
            NotionError: If authentication fails.
            IngestError: If the API request fails.
        """
        url = f"{NOTION_API_URL}{endpoint}"

        try:
            logger.debug(f"Making {method} request to {url}")

            response = requests.request(
                method, url, headers=self.headers, params=params, json=data
            )

            # Handle authentication errors
            if response.status_code == 401:
                logger.error("Notion API authentication failed: Unauthorized (401)")
                raise NotionAuthError("Notion authentication failed: Invalid token or expired token")

            if response.status_code == 403:
                logger.error("Notion API authentication failed: Forbidden (403)")
                raise NotionAuthError("Notion authentication failed: Insufficient permissions")

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "5"))
                logger.warning(f"Rate limited by Notion API. Retry after {retry_after} seconds.")
                raise IngestError(f"Notion API rate limit exceeded. Retry after {retry_after} seconds.")

            # Handle other errors
            if response.status_code >= 400:
                error_data = response.json()
                error_message = error_data.get("message", f"HTTP error {response.status_code}")
                logger.error(f"Notion API error: {error_message}")
                raise IngestError(f"Notion API error: {error_message}")

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Notion API request failed: {e}")
            raise IngestError(f"Notion API request failed: {e}")

    def search(self, query: str = "", filter: Dict = None, start_cursor: str = None, page_size: int = 100) -> Dict[str, Any]:
        """Search for Notion objects.

        Args:
            query: Search query.
            filter: Filter to apply to the search.
            start_cursor: Cursor for pagination.
            page_size: Number of results to return.

        Returns:
            Search results.
        """
        data = {
            "query": query,
            "page_size": page_size,
        }

        if filter:
            data["filter"] = filter

        if start_cursor:
            data["start_cursor"] = start_cursor

        return self._make_request("POST", "/search", data=data)

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get a page by ID.

        Args:
            page_id: The ID of the page.

        Returns:
            Page data.
        """
        return self._make_request("GET", f"/pages/{page_id}")

    def get_block_children(self, block_id: str, start_cursor: str = None, page_size: int = 100) -> Dict[str, Any]:
        """Get children of a block.

        Args:
            block_id: The ID of the block.
            start_cursor: Cursor for pagination.
            page_size: Number of results to return.

        Returns:
            Block children data.
        """
        params = {"page_size": page_size}
        if start_cursor:
            params["start_cursor"] = start_cursor

        return self._make_request("GET", f"/blocks/{block_id}/children", params=params)

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get a database by ID.

        Args:
            database_id: The ID of the database.

        Returns:
            Database data.
        """
        return self._make_request("GET", f"/databases/{database_id}")

    def query_database(self, database_id: str, filter: Dict = None, sorts: List[Dict] = None, start_cursor: str = None, page_size: int = 100) -> Dict[str, Any]:
        """Query a database.

        Args:
            database_id: The ID of the database.
            filter: Filter to apply to the query.
            sorts: Sort criteria.
            start_cursor: Cursor for pagination.
            page_size: Number of results to return.

        Returns:
            Query results.
        """
        data = {"page_size": page_size}

        if filter:
            data["filter"] = filter

        if sorts:
            data["sorts"] = sorts

        if start_cursor:
            data["start_cursor"] = start_cursor

        return self._make_request("POST", f"/databases/{database_id}/query", data=data)


class NotionIngestor:
    """Ingestor plugin for Notion pages and databases."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "notion"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [NodeType.DOCUMENT]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MENTIONS, EdgeRel.CONTAINS]

    def ingest(
        self,
        repo_path: Optional[Path] = None,
        token: Optional[str] = None,
        database_ids: Optional[List[str]] = None,
        page_ids: Optional[List[str]] = None,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest Notion pages and databases.

        Args:
            repo_path: Path to the repository (optional, used for creating edges).
            token: Notion token to use for API calls.
            last_processed: Metadata from the last build for incremental processing.

        Returns:
            A tuple of (nodes, edges, metadata).

        Raises:
            IngestError: If there's an error during ingestion.
        """
        logger.info("Ingesting Notion pages and databases")
        if last_processed:
            logger.info("Performing incremental build")

        try:
            # Get Notion token
            notion_token = get_notion_token(token, allow_failure=True)
            if not notion_token:
                logger.warning("No Notion token found. Skipping Notion ingestion.")
                return [], [], {"page_count": 0, "database_count": 0, "timestamp": datetime.now().isoformat()}

            # Initialize Notion client
            client = NotionClient(notion_token)

            # Initialize collections for nodes and edges
            nodes = []
            edges = []

            # Get last updated timestamp for incremental builds
            last_updated = None
            if last_processed and "timestamp" in last_processed:
                try:
                    last_updated = datetime.fromisoformat(last_processed["timestamp"])
                    logger.info(f"Using last updated timestamp: {last_updated}")
                except (ValueError, TypeError):
                    logger.warning("Invalid timestamp in last_processed, performing full build")

            # Fetch pages and databases
            processed_pages = []
            processed_databases = []

            if page_ids:
                logger.info(f"Fetching specific pages by IDs: {page_ids}")
                for page_id in page_ids:
                    try:
                        page_data = client.get_page(page_id)
                        processed_pages.append(page_data)
                    except IngestError as e:
                        logger.warning(f"Failed to fetch page with ID '{page_id}': {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error fetching page ID '{page_id}': {e}")
            else:
                # Search for all pages if no specific page_ids are given
                logger.info("No specific page IDs provided, fetching all accessible pages.")
                processed_pages.extend(self._fetch_all_pages(client, last_updated))
            
            page_nodes, page_edges = self._process_pages(client, processed_pages)
            nodes.extend(page_nodes)
            edges.extend(page_edges)

            if database_ids:
                logger.info(f"Fetching specific databases by IDs: {database_ids}")
                for db_id in database_ids:
                    try:
                        db_data = client.get_database(db_id)
                        processed_databases.append(db_data)
                    except IngestError as e:
                        logger.warning(f"Failed to fetch database with ID '{db_id}': {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error fetching database ID '{db_id}': {e}")
            else:
                # Search for all databases if no specific database_ids are given
                logger.info("No specific database IDs provided, fetching all accessible databases.")
                processed_databases.extend(self._fetch_all_databases(client, last_updated))

            db_nodes, db_edges = self._process_databases(client, processed_databases)
            nodes.extend(db_nodes)
            edges.extend(db_edges)
            
            # Create metadata
            metadata = {
                "page_count": len(page_nodes),
                "database_count": len(db_nodes),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Processed {metadata['page_count']} Notion pages and {metadata['database_count']} databases")
            return nodes, edges, metadata
        except Exception as e:
            logger.exception("Unexpected error during Notion ingestion")
            raise IngestError(f"Failed to ingest Notion data: {e}")

    def _fetch_all_pages(self, client: NotionClient, last_updated: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch all pages from Notion.

        Args:
            client: Notion client.
            last_updated: Only fetch pages updated after this timestamp.

        Returns:
            List of pages.
        """
        all_pages = []
        has_more = True
        start_cursor = None

        # Filter for pages only
        filter_data = {"value": "page", "property": "object"}

        while has_more:
            try:
                response = client.search("", filter=filter_data, start_cursor=start_cursor)
                results = response.get("results", [])
                all_pages.extend(results)

                # Check if there are more pages
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

                if not start_cursor:
                    has_more = False

                logger.info(f"Fetched {len(results)} Notion pages, has more: {has_more}")
            except Exception as e:
                logger.error(f"Error fetching Notion pages: {e}")
                break

        # Filter by last_updated if provided
        if last_updated:
            filtered_pages = []
            for page in all_pages:
                last_edited_time = page.get("last_edited_time")
                if last_edited_time:
                    page_updated = datetime.fromisoformat(last_edited_time.replace("Z", "+00:00"))
                    if page_updated > last_updated:
                        filtered_pages.append(page)
            logger.info(f"Filtered from {len(all_pages)} to {len(filtered_pages)} pages based on last_updated")
            return filtered_pages

        return all_pages

    def _fetch_all_databases(self, client: NotionClient, last_updated: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch all databases from Notion.

        Args:
            client: Notion client.
            last_updated: Only fetch databases updated after this timestamp.

        Returns:
            List of databases.
        """
        all_databases = []
        has_more = True
        start_cursor = None

        # Filter for databases only
        filter_data = {"value": "database", "property": "object"}

        while has_more:
            try:
                response = client.search("", filter=filter_data, start_cursor=start_cursor)
                results = response.get("results", [])
                all_databases.extend(results)

                # Check if there are more databases
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

                if not start_cursor:
                    has_more = False

                logger.info(f"Fetched {len(results)} Notion databases, has more: {has_more}")
            except Exception as e:
                logger.error(f"Error fetching Notion databases: {e}")
                break

        # Filter by last_updated if provided
        if last_updated:
            filtered_databases = []
            for db in all_databases:
                last_edited_time = db.get("last_edited_time")
                if last_edited_time:
                    db_updated = datetime.fromisoformat(last_edited_time.replace("Z", "+00:00"))
                    if db_updated > last_updated:
                        filtered_databases.append(db)
            logger.info(f"Filtered from {len(all_databases)} to {len(filtered_databases)} databases based on last_updated")
            return filtered_databases

        return all_databases

    def _process_pages(self, client: NotionClient, pages: List[Dict[str, Any]]) -> Tuple[List[Node], List[Edge]]:
        """Process Notion pages into nodes and edges.

        Args:
            client: Notion client.
            pages: List of pages to process.

        Returns:
            Tuple of (nodes, edges).
        """
        nodes = []
        edges = []

        for page in pages:
            page_id = page.get("id")
            if not page_id:
                continue

            # Get page properties
            title = self._extract_page_title(page)
            last_edited_time = page.get("last_edited_time")
            created_time = page.get("created_time")
            url = page.get("url")

            # Parse timestamps
            created_at = None
            if created_time:
                created_at = datetime.fromisoformat(created_time.replace("Z", "+00:00"))

            updated_at = None
            if last_edited_time:
                updated_at = datetime.fromisoformat(last_edited_time.replace("Z", "+00:00"))

            # Create page node
            node_id = f"notion:page:{page_id}"
            page_node = DocumentNode(
                id=node_id,
                type=NodeType.DOCUMENT,
                title=title,
                body=self._get_page_content(client, page_id),
                ts=created_at,
                created_at=created_at,
                updated_at=updated_at,
                path=url or f"https://notion.so/{page_id.replace('-', '')}",
                format="notion",
                url=url,
                metadata={
                    "source": "notion",
                    "notion_id": page_id,
                    "notion_type": "page",
                    "parent": self._get_parent_info(page),
                }
            )
            nodes.append(page_node)

            # Create parent-child edge if parent exists
            parent_info = self._get_parent_info(page)
            if parent_info and "id" in parent_info:
                parent_id = parent_info["id"]
                parent_type = parent_info["type"]

                # Create edge from parent to page
                parent_edge = Edge(
                    src=f"notion:{parent_type}:{parent_id}",
                    dst=node_id,
                    rel=EdgeRel.CONTAINS,
                    properties={
                        "source": "notion",
                    }
                )
                edges.append(parent_edge)

        return nodes, edges

    def _process_databases(self, client: NotionClient, databases: List[Dict[str, Any]]) -> Tuple[List[Node], List[Edge]]:
        """Process Notion databases into nodes and edges.

        Args:
            client: Notion client.
            databases: List of databases to process.

        Returns:
            Tuple of (nodes, edges).
        """
        nodes = []
        edges = []

        for db in databases:
            db_id = db.get("id")
            if not db_id:
                continue

            # Get database properties
            title = self._extract_database_title(db)
            last_edited_time = db.get("last_edited_time")
            created_time = db.get("created_time")
            url = db.get("url")

            # Parse timestamps
            created_at = None
            if created_time:
                created_at = datetime.fromisoformat(created_time.replace("Z", "+00:00"))

            updated_at = None
            if last_edited_time:
                updated_at = datetime.fromisoformat(last_edited_time.replace("Z", "+00:00"))

            # Create database node
            node_id = f"notion:database:{db_id}"
            db_node = DocumentNode(
                id=node_id,
                type=NodeType.DOCUMENT,
                title=title,
                body=f"Notion Database: {title}",
                ts=created_at,
                created_at=created_at,
                updated_at=updated_at,
                path=url or f"https://notion.so/{db_id.replace('-', '')}",
                format="notion",
                url=url,
                metadata={
                    "source": "notion",
                    "notion_id": db_id,
                    "notion_type": "database",
                    "parent": self._get_parent_info(db),
                    "properties": db.get("properties", {}),
                }
            )
            nodes.append(db_node)

            # Create parent-child edge if parent exists
            parent_info = self._get_parent_info(db)
            if parent_info and "id" in parent_info:
                parent_id = parent_info["id"]
                parent_type = parent_info["type"]

                # Create edge from parent to database
                parent_edge = Edge(
                    src=f"notion:{parent_type}:{parent_id}",
                    dst=node_id,
                    rel=EdgeRel.CONTAINS,
                    properties={
                        "source": "notion",
                    }
                )
                edges.append(parent_edge)

            # Process database entries (pages in the database)
            db_pages = self._fetch_database_pages(client, db_id)
            for page in db_pages:
                page_id = page.get("id")
                if not page_id:
                    continue

                # Create edge from database to page
                db_page_edge = Edge(
                    src=node_id,
                    dst=f"notion:page:{page_id}",
                    rel=EdgeRel.CONTAINS,
                    properties={
                        "source": "notion",
                    }
                )
                edges.append(db_page_edge)

        return nodes, edges

    def _fetch_database_pages(self, client: NotionClient, database_id: str) -> List[Dict[str, Any]]:
        """Fetch all pages in a database.

        Args:
            client: Notion client.
            database_id: ID of the database.

        Returns:
            List of pages in the database.
        """
        all_pages = []
        has_more = True
        start_cursor = None

        while has_more:
            try:
                response = client.query_database(database_id, start_cursor=start_cursor)
                results = response.get("results", [])
                all_pages.extend(results)

                # Check if there are more pages
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

                if not start_cursor:
                    has_more = False

                logger.info(f"Fetched {len(results)} pages from database {database_id}, has more: {has_more}")
            except Exception as e:
                logger.error(f"Error fetching pages from database {database_id}: {e}")
                break

        return all_pages

    def _extract_page_title(self, page: Dict[str, Any]) -> str:
        """Extract the title from a page.

        Args:
            page: Page data.

        Returns:
            Page title.
        """
        # Try to get title from properties
        properties = page.get("properties", {})
        title_prop = properties.get("title", {})
        title_content = title_prop.get("title", [])

        if title_content:
            title_parts = []
            for part in title_content:
                text = part.get("text", {}).get("content", "")
                if text:
                    title_parts.append(text)
            if title_parts:
                return " ".join(title_parts)

        # Fallback to page ID
        return f"Notion Page {page.get('id', 'Unknown')}"

    def _extract_database_title(self, database: Dict[str, Any]) -> str:
        """Extract the title from a database.

        Args:
            database: Database data.

        Returns:
            Database title.
        """
        # Try to get title from title field
        title = database.get("title", [])

        if title:
            title_parts = []
            for part in title:
                text = part.get("text", {}).get("content", "")
                if text:
                    title_parts.append(text)
            if title_parts:
                return " ".join(title_parts)

        # Fallback to database ID
        return f"Notion Database {database.get('id', 'Unknown')}"

    def _get_parent_info(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Get parent information from a Notion object.

        Args:
            obj: Notion object data.

        Returns:
            Parent information.
        """
        parent = obj.get("parent", {})
        parent_type = None
        parent_id = None

        if "page_id" in parent:
            parent_type = "page"
            parent_id = parent["page_id"]
        elif "database_id" in parent:
            parent_type = "database"
            parent_id = parent["database_id"]
        elif "workspace" in parent and parent["workspace"] is True:
            parent_type = "workspace"
            parent_id = "workspace"

        if parent_type and parent_id:
            return {
                "type": parent_type,
                "id": parent_id
            }

        return None

    def _get_page_content(self, client: NotionClient, page_id: str) -> str:
        """Get the content of a page.

        Args:
            client: Notion client.
            page_id: ID of the page.

        Returns:
            Page content as markdown.
        """
        try:
            blocks = self._fetch_all_blocks(client, page_id)
            return self._blocks_to_markdown(blocks)
        except Exception as e:
            logger.error(f"Error getting content for page {page_id}: {e}")
            return ""

    def _fetch_all_blocks(self, client: NotionClient, block_id: str) -> List[Dict[str, Any]]:
        """Fetch all blocks for a block.

        Args:
            client: Notion client.
            block_id: ID of the block.

        Returns:
            List of blocks.
        """
        all_blocks = []
        has_more = True
        start_cursor = None

        while has_more:
            try:
                response = client.get_block_children(block_id, start_cursor=start_cursor)
                results = response.get("results", [])
                all_blocks.extend(results)

                # Check if there are more blocks
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

                if not start_cursor:
                    has_more = False

                logger.debug(f"Fetched {len(results)} blocks from {block_id}, has more: {has_more}")
            except Exception as e:
                logger.error(f"Error fetching blocks for {block_id}: {e}")
                break

        return all_blocks

    def _blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert blocks to markdown.

        Args:
            blocks: List of blocks.

        Returns:
            Markdown representation of blocks.
        """
        markdown = []

        for block in blocks:
            block_type = block.get("type")
            if not block_type:
                continue

            block_content = block.get(block_type, {})

            if block_type == "paragraph":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                if text:
                    markdown.append(text)
                    markdown.append("")
            elif block_type == "heading_1":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                if text:
                    markdown.append(f"# {text}")
                    markdown.append("")
            elif block_type == "heading_2":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                if text:
                    markdown.append(f"## {text}")
                    markdown.append("")
            elif block_type == "heading_3":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                if text:
                    markdown.append(f"### {text}")
                    markdown.append("")
            elif block_type == "bulleted_list_item":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                if text:
                    markdown.append(f"- {text}")
            elif block_type == "numbered_list_item":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                if text:
                    markdown.append(f"1. {text}")
            elif block_type == "to_do":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                checked = block_content.get("checked", False)
                if text:
                    markdown.append(f"- {'[x]' if checked else '[ ]'} {text}")
            elif block_type == "code":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                language = block_content.get("language", "")
                if text:
                    markdown.append(f"```{language}")
                    markdown.append(text)
                    markdown.append("```")
                    markdown.append("")
            elif block_type == "quote":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                if text:
                    markdown.append(f"> {text}")
                    markdown.append("")
            elif block_type == "divider":
                markdown.append("---")
                markdown.append("")
            elif block_type == "callout":
                text = self._rich_text_to_markdown(block_content.get("rich_text", []))
                emoji = block_content.get("icon", {}).get("emoji", "")
                if text:
                    markdown.append(f"> {emoji} {text}")
                    markdown.append("")

        return "\n".join(markdown)

    def _rich_text_to_markdown(self, rich_text: List[Dict[str, Any]]) -> str:
        """Convert rich text to markdown.

        Args:
            rich_text: List of rich text objects.

        Returns:
            Markdown representation of rich text.
        """
        result = []

        for text_obj in rich_text:
            text = text_obj.get("text", {}).get("content", "")
            if not text:
                continue

            annotations = text_obj.get("annotations", {})

            # Apply annotations
            if annotations.get("bold"):
                text = f"**{text}**"
            if annotations.get("italic"):
                text = f"*{text}*"
            if annotations.get("strikethrough"):
                text = f"~~{text}~~"
            if annotations.get("code"):
                text = f"`{text}`"

            # Handle links
            link = text_obj.get("text", {}).get("link")
            if link and "url" in link:
                text = f"[{text}]({link['url']})"

            result.append(text)

        return "".join(result)


def extract_notion_page_references(text: str) -> List[str]:
    """Extract Notion page references from text.

    Args:
        text: The text to extract references from.

    Returns:
        A list of Notion page IDs.
    """
    # Match patterns like https://www.notion.so/Page-Title-1234567890abcdef1234567890abcdef
    pattern = r'https?://(?:www\.)?notion\.so/(?:[^/]+/)?([a-f0-9]{32})'
    matches = re.findall(pattern, text)
    return matches
