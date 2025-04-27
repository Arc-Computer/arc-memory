# Using the Arc Memory SDK in Different Contexts

This guide provides examples of how to use the Arc Memory SDK in various contexts and scenarios.

**Related Documentation:**
- [Building Graphs](./building-graphs.md) - Examples of building knowledge graphs
- [Tracing History](./tracing-history.md) - Examples of tracing history
- [Custom Plugins](./custom-plugins.md) - Creating custom data source plugins
- [API Documentation](../api/build.md) - API reference

## Basic SDK Usage

### Initializing the SDK

```python
from arc_memory.sql.db import init_db, get_node_count, get_edge_count

# Initialize the database
conn = init_db()

# Get basic statistics
node_count = get_node_count(conn)
edge_count = get_edge_count(conn)

print(f"Knowledge graph contains {node_count} nodes and {edge_count} edges")
```

### Building a Knowledge Graph

```python
from arc_memory.build import build_graph
from pathlib import Path

# Build a knowledge graph for a repository
build_graph(
    repo_path=Path("./my-repo"),
    db_path=Path("./my-graph.db"),
    incremental=True,
    max_commits=1000,
    days=90,
    github_token="your-github-token"  # Optional
)
```

### Tracing History

```python
from arc_memory.trace import trace_history_for_file_line
from pathlib import Path

# Trace the history of a specific line in a file
history = trace_history_for_file_line(
    db_path=Path("./my-graph.db"),
    file_path="src/main.py",
    line_number=42,
    max_results=5,
    max_hops=3
)

# Print the history
for item in history:
    print(f"{item['type']}: {item['title']}")
    print(f"  {item['body'][:100]}...")
    print()
```

## Integration with Web Applications

### Flask Web Application

```python
from flask import Flask, request, jsonify
from arc_memory.sql.db import init_db, get_node_by_id
from arc_memory.trace import trace_history_for_file_line
from pathlib import Path

app = Flask(__name__)

# Initialize the database once at startup
conn = init_db(Path("./my-graph.db"))

@app.route("/trace", methods=["GET"])
def trace():
    file_path = request.args.get("file")
    line_number = int(request.args.get("line"))
    
    history = trace_history_for_file_line(
        db_path=Path("./my-graph.db"),
        file_path=file_path,
        line_number=line_number
    )
    
    return jsonify(history)

@app.route("/node/<node_id>", methods=["GET"])
def get_node(node_id):
    node = get_node_by_id(conn, node_id)
    if node is None:
        return jsonify({"error": "Node not found"}), 404
    return jsonify(node)

if __name__ == "__main__":
    app.run(debug=True)
```

### FastAPI Web Application

```python
from fastapi import FastAPI, HTTPException
from arc_memory.sql.db import init_db, get_node_by_id
from arc_memory.trace import trace_history_for_file_line
from pathlib import Path

app = FastAPI()

# Initialize the database once at startup
conn = init_db(Path("./my-graph.db"))

@app.get("/trace")
async def trace(file: str, line: int):
    history = trace_history_for_file_line(
        db_path=Path("./my-graph.db"),
        file_path=file,
        line_number=line
    )
    
    return history

@app.get("/node/{node_id}")
async def get_node(node_id: str):
    node = get_node_by_id(conn, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node
```

## Integration with CI/CD Pipelines

### GitHub Actions Workflow

```yaml
# .github/workflows/arc-memory.yml
name: Arc Memory

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0  # Fetch all history

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install arc-memory

    - name: Build knowledge graph
      run: |
        arc build --token ${{ secrets.GITHUB_TOKEN }}

    - name: Upload graph
      uses: actions/upload-artifact@v3
      with:
        name: knowledge-graph
        path: ~/.arc/graph.db.zst
```

### Jenkins Pipeline

```groovy
pipeline {
    agent {
        docker {
            image 'python:3.10'
        }
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install arc-memory'
            }
        }
        
        stage('Build Graph') {
            steps {
                sh 'arc build --token ${GITHUB_TOKEN}'
            }
        }
        
        stage('Archive') {
            steps {
                archiveArtifacts artifacts: '~/.arc/graph.db.zst', fingerprint: true
            }
        }
    }
}
```

## Integration with VS Code Extensions

### VS Code Extension (TypeScript)

```typescript
import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {
    // Register a command to trace history
    let disposable = vscode.commands.registerCommand('arc-memory.traceHistory', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }
        
        const filePath = editor.document.uri.fsPath;
        const lineNumber = editor.selection.active.line + 1;
        
        // Call the Arc Memory CLI
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('File not in workspace');
            return;
        }
        
        const cwd = workspaceFolder.uri.fsPath;
        
        try {
            const result = cp.execSync(
                `arc trace file "${filePath}" ${lineNumber} --json`,
                { cwd }
            ).toString();
            
            const history = JSON.parse(result);
            
            // Show the results in a webview
            const panel = vscode.window.createWebviewPanel(
                'arcMemoryHistory',
                'Arc Memory: History',
                vscode.ViewColumn.Beside,
                {}
            );
            
            panel.webview.html = getWebviewContent(history);
        } catch (error) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
        }
    });
    
    context.subscriptions.push(disposable);
}

function getWebviewContent(history: any[]): string {
    // Generate HTML to display the history
    let html = '<html><body><h1>History</h1>';
    
    for (const item of history) {
        html += `<div class="item">
            <h2>${item.type}: ${item.title}</h2>
            <p>${item.body}</p>
        </div>`;
    }
    
    html += '</body></html>';
    return html;
}
```

## Integration with Jupyter Notebooks

### Jupyter Notebook

```python
# Import Arc Memory SDK
from arc_memory.sql.db import init_db, get_node_count, search_entities
from arc_memory.trace import trace_history_for_file_line
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx

# Initialize the database
conn = init_db()

# Get basic statistics
node_count = get_node_count(conn)
print(f"Knowledge graph contains {node_count} nodes")

# Search for entities
results = search_entities(conn, "important feature", limit=5)
for result in results:
    print(f"{result.type.value}: {result.title}")
    print(f"  {result.snippet}")
    print()

# Trace history
history = trace_history_for_file_line(
    db_path=Path("~/.arc/graph.db"),
    file_path="src/main.py",
    line_number=42
)

# Visualize the history as a graph
G = nx.DiGraph()

# Add nodes
for item in history:
    G.add_node(item["id"], label=f"{item['type']}: {item['title']}")

# Add edges (simplified)
for i in range(len(history) - 1):
    G.add_edge(history[i]["id"], history[i+1]["id"])

# Plot the graph
plt.figure(figsize=(12, 8))
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_color="skyblue", node_size=1500, arrows=True)
plt.title("History Graph")
plt.show()
```

## Integration with AI Assistants

### Using Arc Memory with LangChain

```python
from langchain.tools import BaseTool
from arc_memory.sql.db import init_db, search_entities
from arc_memory.trace import trace_history_for_file_line
from pathlib import Path
import json

# Define Arc Memory tools
class ArcMemorySearchTool(BaseTool):
    name = "arc_memory_search"
    description = "Search the Arc Memory knowledge graph for entities"
    
    def _run(self, query: str):
        conn = init_db()
        results = search_entities(conn, query, limit=5)
        return json.dumps([{
            "id": r.id,
            "type": r.type.value,
            "title": r.title,
            "snippet": r.snippet
        } for r in results])
    
    def _arun(self, query: str):
        # Async implementation would go here
        return self._run(query)

class ArcMemoryTraceTool(BaseTool):
    name = "arc_memory_trace"
    description = "Trace the history of a specific line in a file"
    
    def _run(self, file_and_line: str):
        file_path, line_number = file_and_line.split(":")
        history = trace_history_for_file_line(
            db_path=Path("~/.arc/graph.db"),
            file_path=file_path,
            line_number=int(line_number)
        )
        return json.dumps(history)
    
    def _arun(self, file_and_line: str):
        # Async implementation would go here
        return self._run(file_and_line)

# Use the tools with an LLM
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI

llm = OpenAI(temperature=0)
tools = [ArcMemorySearchTool(), ArcMemoryTraceTool()]

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Example query
agent.run("What's the history of the authentication feature in our codebase?")
```

### Using Arc Memory with Anthropic's Claude

```python
import anthropic
from arc_memory.sql.db import init_db, search_entities
from arc_memory.trace import trace_history_for_file_line
from pathlib import Path

# Initialize the client
client = anthropic.Anthropic(api_key="your-api-key")

# Function to get context from Arc Memory
def get_arc_memory_context(query):
    conn = init_db()
    results = search_entities(conn, query, limit=5)
    
    context = "Information from Arc Memory:\n\n"
    for result in results:
        context += f"{result.type.value}: {result.title}\n"
        context += f"{result.snippet}\n\n"
    
    return context

# Example usage
user_query = "Why was the authentication system designed this way?"
arc_context = get_arc_memory_context("authentication system design")

message = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": f"""
        {arc_context}
        
        Based on the information above from our codebase history, please answer:
        {user_query}
        """}
    ]
)

print(message.content)
```

## Next Steps

- [Learn about building knowledge graphs](./building-graphs.md)
- [Explore tracing history examples](./tracing-history.md)
- [Create custom plugins](./custom-plugins.md)
- [Check the API documentation](../api/build.md)
