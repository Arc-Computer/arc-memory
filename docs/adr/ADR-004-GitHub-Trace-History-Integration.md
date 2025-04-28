# ADR-004: GitHub Trace History Integration

> Status: Accepted
>
> **Date:** 2025-04-28
> 
> **Decision makers:** Jarrod Barnes (Founder), Core Eng Team
> 
> **Context:** Arc Memory's trace history algorithm is a core feature for providing context about code, but it needs to properly integrate GitHub nodes (PRs and issues) to provide comprehensive context.

## 1 · Problem Statement

The Arc Memory trace history algorithm is designed to find the history of a specific line of code by starting from a commit and traversing the knowledge graph. However, GitHub nodes (PRs and issues) may not appear in trace results if there's no direct connection between the starting commit and these nodes. This limits the usefulness of the trace history feature for providing comprehensive context.

Specifically:

1. The benchmark shows that GitHub PRs and issues are being correctly ingested into the knowledge graph
2. However, these nodes don't appear in trace history results when starting from a file line
3. This creates a disconnect between the data available in the graph and what users can access through the trace feature

## 2 · Analysis of Current Implementation

### 2.1 Current Trace Algorithm

The current trace history algorithm:

1. Starts with a specific line in a file
2. Uses git blame to find the commit that last modified that line
3. Performs a breadth-first search (BFS) from that commit node
4. Follows specific edge types based on the node type:
   - Commit → PR via MERGES edges
   - PR → Issue via MENTIONS edges
   - Issue → ADR via DECIDES edges (inbound)
   - etc.
5. Returns a list of nodes representing the history trail

### 2.2 GitHub Integration Gaps

The key issue is that there may not be direct connections between:
- Commits and the PRs that introduced them (missing MERGES edges)
- PRs and the issues they reference (missing MENTIONS edges)
- Issues and other related entities

This creates a gap in the trace history, where GitHub nodes exist in the graph but aren't accessible through the trace algorithm.

## 3 · Considered Approaches

### 3.1 Approach 1: Enhance Trace Algorithm

Modify the `get_connected_nodes` function to:
- Add special handling for GitHub nodes
- Implement fallback mechanisms to find relevant GitHub nodes
- Add heuristics to connect commits to PRs and issues

```python
def get_connected_nodes(conn, node_id, hop_count=0):
    # Existing logic...
    
    # Special handling for GitHub nodes
    if node_type == "commit":
        # Find PRs that merge this commit
        pr_nodes = find_prs_for_commit(conn, commit_hash)
        connected_nodes.extend(pr_nodes)
        
        # Find issues mentioned by these PRs
        for pr_id in pr_nodes:
            issue_nodes = get_nodes_by_edge(conn, pr_id, "MENTIONS", is_source=True)
            connected_nodes.extend(issue_nodes)
    
    # Fallback mechanism
    if hop_count == 0 and not any(n.startswith("PR:") or n.startswith("Issue:") for n in connected_nodes):
        github_nodes = find_relevant_github_nodes(conn, node_id)
        connected_nodes.extend(github_nodes)
        
    return connected_nodes
```

**Pros:**
- Provides immediate access to GitHub nodes in trace results
- Improves user experience by showing more comprehensive context

**Cons:**
- Risks breaking existing functionality
- May return less relevant nodes through fallback mechanisms
- Increases complexity of the trace algorithm

### 3.2 Approach 2: Improve GitHub Ingestor

Enhance the GitHub ingestor to create more direct connections:
- Add MERGES edges from PRs to all commits they contain
- Improve extraction of issue references from PR descriptions and comments
- Create more comprehensive MENTIONS edges

```python
def ingest_github_data(repo, token):
    # Existing logic...
    
    # For each PR, create MERGES edges to all commits
    for pr in prs:
        pr_node = create_pr_node(pr)
        
        # Get all commits in the PR
        commits = get_pr_commits(pr)
        
        # Create MERGES edges to all commits
        for commit in commits:
            commit_node = get_or_create_commit_node(commit)
            create_edge(pr_node, "MERGES", commit_node)
        
        # Extract issue references from PR description and comments
        issues = extract_issue_references(pr)
        
        # Create MENTIONS edges to all referenced issues
        for issue in issues:
            issue_node = get_or_create_issue_node(issue)
            create_edge(pr_node, "MENTIONS", issue_node)
    
    return nodes, edges
```

**Pros:**
- Preserves the existing trace algorithm
- Creates more accurate connections in the knowledge graph
- Improves overall graph quality

**Cons:**
- Requires changes to the GitHub ingestor
- May increase the number of edges in the graph
- Doesn't address existing graphs without these connections

### 3.3 Approach 3: Separate GitHub-Specific Trace Function

Create a separate function specifically for GitHub-related traces:

```python
def trace_github_history(conn, file_path, line_number):
    # Get the commit for the line
    commit_id = get_commit_for_line(file_path, line_number)
    
    # Find PRs related to this commit
    pr_nodes = find_prs_for_commit(conn, commit_id)
    
    # Find issues related to these PRs
    issue_nodes = []
    for pr_id in pr_nodes:
        issues = get_nodes_by_edge(conn, pr_id, "MENTIONS", is_source=True)
        issue_nodes.extend(issues)
    
    return format_results(pr_nodes + issue_nodes)
```

**Pros:**
- Keeps the core trace algorithm unchanged
- Provides a specialized function for GitHub-specific traces
- Allows for different optimization strategies

**Cons:**
- Creates a separate API for GitHub traces
- May confuse users with multiple trace functions
- Duplicates some functionality

## 4 · Decision

After careful consideration, we have decided to adopt **Approach 2: Improve GitHub Ingestor** as our primary strategy, with elements of Approach 3 for benchmarking.

This approach:
1. Preserves the existing trace algorithm which has been well-tested and is core to our product
2. Improves the quality of the knowledge graph by creating more accurate connections
3. Provides a better foundation for future enhancements

For benchmarking purposes, we will implement a separate function to count GitHub nodes in the database directly, which gives a more accurate picture of the GitHub ingestion performance without modifying the trace algorithm.

## 5 · Implementation Plan

### 5.1 GitHub Ingestor Enhancements

1. Modify the GitHub ingestor to create MERGES edges from PRs to all commits they contain
2. Improve extraction of issue references from PR descriptions and comments
3. Create more comprehensive MENTIONS edges between related entities

### 5.2 Benchmark Enhancements

1. Add direct database queries to count GitHub nodes in the benchmark
2. Report PR count, issue count, and mention edge count separately from trace results
3. Add metrics for GitHub ingestion performance

### 5.3 Documentation Updates

1. Update the trace history documentation to clarify how GitHub nodes are integrated
2. Add examples of how to query GitHub nodes in the knowledge graph
3. Document the relationship between commits, PRs, and issues in the graph schema

## 6 · Future Considerations

In the future, we may revisit Approach 1 (enhancing the trace algorithm) once we have more experience with how users interact with GitHub data in the knowledge graph. This would be a more significant change and would require comprehensive testing to ensure it doesn't break existing functionality.

We will also consider adding a specialized GitHub trace function (Approach 3) if users express a need for more GitHub-specific context in their traces.

**Accepted** – 2025-04-28

— Jarrod Barnes

## 7 · Implementation Checklist

- [x] Document the decision in this ADR
- [ ] Enhance GitHub ingestor to create more direct connections
- [x] Update benchmarks to count GitHub nodes directly
- [ ] Add tests for GitHub node connections
- [ ] Update documentation to clarify GitHub integration
- [ ] Consider specialized GitHub trace function in future releases
