"""
Dependency analyzer for the Cross-Repository Explorer.

This module analyzes cross-repository dependencies.
"""

from typing import Dict, List, Any


def analyze_dependencies(arc, repo_ids: List[str], repo_names: Dict[str, str]) -> None:
    """Analyze cross-repository dependencies.

    Args:
        arc: Arc Memory instance
        repo_ids: List of repository IDs
        repo_names: Dictionary mapping repository IDs to names
    """
    if not repo_ids or len(repo_ids) < 2:
        print("Need at least two repositories to analyze cross-repository dependencies.")
        return

    # Get all nodes from all repositories
    all_nodes = {}
    for repo_id in repo_ids:
        repo_name = repo_names.get(repo_id, repo_id)
        print(f"Analyzing nodes in {repo_name}...")
        
        try:
            # Get all nodes for this repository
            cursor = arc.adapter.conn.execute(
                "SELECT id, type, title FROM nodes WHERE repo_id = ?",
                (repo_id,)
            )
            nodes = cursor.fetchall()
            
            # Store nodes by repository
            all_nodes[repo_id] = {node["id"]: node for node in nodes}
            
            print(f"Found {len(nodes)} nodes in {repo_name}.")
        except Exception as e:
            print(f"Error getting nodes for {repo_name}: {e}")

    # Find cross-repository edges
    cross_repo_edges = []
    print("\nAnalyzing cross-repository dependencies...")
    
    try:
        # Query for edges where source and destination are in different repositories
        for src_repo_id in repo_ids:
            for dst_repo_id in repo_ids:
                if src_repo_id == dst_repo_id:
                    continue
                
                # Get edges from src_repo to dst_repo
                cursor = arc.adapter.conn.execute(
                    """
                    SELECT e.src, e.dst, e.rel, e.extra
                    FROM edges e
                    JOIN nodes n1 ON e.src = n1.id
                    JOIN nodes n2 ON e.dst = n2.id
                    WHERE n1.repo_id = ? AND n2.repo_id = ?
                    """,
                    (src_repo_id, dst_repo_id)
                )
                edges = cursor.fetchall()
                
                if edges:
                    src_name = repo_names.get(src_repo_id, src_repo_id)
                    dst_name = repo_names.get(dst_repo_id, dst_repo_id)
                    print(f"Found {len(edges)} dependencies from {src_name} to {dst_name}.")
                    
                    # Add to cross-repository edges
                    for edge in edges:
                        cross_repo_edges.append({
                            "src_repo": src_repo_id,
                            "dst_repo": dst_repo_id,
                            "src": edge["src"],
                            "dst": edge["dst"],
                            "rel": edge["rel"],
                            "extra": edge["extra"]
                        })
    except Exception as e:
        print(f"Error analyzing cross-repository edges: {e}")

    # Group dependencies by repository pair
    repo_dependencies = {}
    for edge in cross_repo_edges:
        src_repo = edge["src_repo"]
        dst_repo = edge["dst_repo"]
        
        # Create key for repository pair
        repo_pair = f"{src_repo}:{dst_repo}"
        
        if repo_pair not in repo_dependencies:
            repo_dependencies[repo_pair] = []
        
        repo_dependencies[repo_pair].append(edge)

    # Display cross-repository dependencies
    if not cross_repo_edges:
        print("\nNo cross-repository dependencies found.")
        print("This could be because:")
        print("1. The repositories are truly independent")
        print("2. The knowledge graph doesn't have relationship information")
        print("3. The repositories use indirect dependencies not captured in the graph")
        return

    print("\nCross-Repository Dependencies:")
    for repo_pair, edges in repo_dependencies.items():
        src_repo, dst_repo = repo_pair.split(":")
        src_name = repo_names.get(src_repo, src_repo)
        dst_name = repo_names.get(dst_repo, dst_repo)
        
        print(f"\n{src_name} → {dst_name}:")
        
        # Group by source and destination node types
        type_groups = {}
        for edge in edges:
            src_node = all_nodes.get(src_repo, {}).get(edge["src"], {})
            dst_node = all_nodes.get(dst_repo, {}).get(edge["dst"], {})
            
            src_type = src_node.get("type", "unknown")
            dst_type = dst_node.get("type", "unknown")
            
            type_key = f"{src_type}:{dst_type}"
            if type_key not in type_groups:
                type_groups[type_key] = []
            
            type_groups[type_key].append({
                "src": src_node,
                "dst": dst_node,
                "rel": edge["rel"]
            })
        
        # Display grouped dependencies
        for type_key, deps in type_groups.items():
            src_type, dst_type = type_key.split(":")
            print(f"  - {src_type} → {dst_type}: {len(deps)} dependencies")
            
            # Show a few examples
            for i, dep in enumerate(deps[:3]):
                src_title = dep["src"].get("title", dep["src"].get("id", "unknown"))
                dst_title = dep["dst"].get("title", dep["dst"].get("id", "unknown"))
                rel = dep["rel"]
                
                print(f"    {i+1}. {src_title} → {dst_title} ({rel})")
            
            if len(deps) > 3:
                print(f"    ... and {len(deps) - 3} more")

    print("\nDependency analysis complete.")
    print("Note: This is a simplified view of cross-repository dependencies.")
    print("For more detailed analysis, use the Arc Memory SDK directly.")
