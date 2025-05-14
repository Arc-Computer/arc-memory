#!/bin/bash

# Colors for better terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Arc Memory: Code Review Assistant Demo ===${NC}\n"

echo -e "${BLUE}Step 1: Running LLM-Powered Code Review Assistant on a file${NC}"
echo -e "This will use the knowledge graph and LLMs to provide an intelligent code review..."
echo -e "${YELLOW}Command: python docs/examples/agents/llm_powered_code_review.py --repo . --files docs/examples/agents/llm_powered_code_review.py${NC}\n"

# Run the LLM-powered code review assistant
python docs/examples/agents/llm_powered_code_review.py --repo . --files docs/examples/agents/llm_powered_code_review.py

# Step 2 and 3 removed as they're not working correctly yet

echo -e "\n${BLUE}Step 2: SDK Integration Example${NC}"
echo -e "Here's how easy it is to integrate Arc Memory into your own tools:"
echo -e "${YELLOW}Code example:${NC}"
echo -e "from arc_memory.sdk import Arc\n"
echo -e "# Initialize Arc"
echo -e "arc = Arc(repo_path=\"./\")\n"
echo -e "# Query the knowledge graph"
echo -e "results = arc.query(\"What changes were made to the refresh functionality?\")\n"

echo -e "\n${GREEN}=== Demo Complete ===${NC}"
echo -e "Arc Memory gives you and your agents the context needed to understand code,"
echo -e "predict impact, and make safer changes. This is just the beginning!"
