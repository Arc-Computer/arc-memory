#!/bin/bash

# Colors for better terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Arc Memory Demo Runner ===${NC}\n"

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY environment variable is not set.${NC}"
    echo -e "Please set your OpenAI API key with:"
    echo -e "${YELLOW}export OPENAI_API_KEY=your-api-key${NC}"
    exit 1
fi

# Disable debug logging to suppress "OpenAI API returned unexpected response" messages
export OPENAI_DEBUG=0
export ARC_DEBUG=0

# Check if knowledge graph exists
if [ ! -f ~/.arc/graph.db ]; then
    echo -e "${YELLOW}Warning: Knowledge graph not found at ~/.arc/graph.db${NC}"
    echo -e "The demos will build a new graph, which may take some time."
fi

echo -e "${BLUE}Running Demo 1: Code Review Assistant${NC}"
echo -e "${YELLOW}This demo will build/refresh the knowledge graph and may take a few minutes.${NC}"
echo -e "Press Enter to continue or Ctrl+C to cancel..."
read

# Run Demo 1: Code Review Assistant
./demo_code_review.sh

echo -e "\n${BLUE}Running Demo 2: PR Impact Analysis${NC}"
echo -e "${YELLOW}This demo will use the existing knowledge graph.${NC}"
echo -e "Press Enter to continue or Ctrl+C to cancel..."
read

# Run Demo 2: PR Impact Analysis
python pr_impact_analysis.py 71

echo -e "\n${BLUE}Running Demo 3: Blast Radius Visualization${NC}"
echo -e "${YELLOW}This demo will use the existing knowledge graph.${NC}"
echo -e "Press Enter to continue or Ctrl+C to cancel..."
read

# Run Demo 3: Blast Radius Visualization
python blast_radius_viz.py arc_memory/auto_refresh/core.py

echo -e "\n${GREEN}All demos completed successfully!${NC}"
