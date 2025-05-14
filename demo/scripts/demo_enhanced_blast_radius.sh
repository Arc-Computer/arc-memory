#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Arc Memory: Enhanced Blast Radius Visualization Demo ===${NC}\n"

echo -e "${BLUE}Running Enhanced Blast Radius Visualization on a key file${NC}"
echo -e "This will analyze the potential impact of changes to a core file..."
echo -e "${YELLOW}Command: python docs/examples/agents/enhanced_blast_radius.py arc_memory/sdk/core.py${NC}\n"

# Run the enhanced blast radius visualization
python docs/examples/agents/enhanced_blast_radius.py arc_memory/sdk/core.py

echo -e "\n${GREEN}=== Demo Complete ===${NC}"
echo -e "Arc Memory gives you and your agents the context needed to understand code,"
echo -e "predict impact, and make safer changes. This is just the beginning!"
