#!/bin/bash

# Demo script for the Self-Healing Code Generation Loop
# This script demonstrates how to use the self-healing code generation loop
# to automatically improve code quality.

# Set colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Self-Healing Code Generation Loop Demo ===${NC}"
echo -e "${BLUE}This demo will run the self-healing loop on a sample code file${NC}"
echo -e "${BLUE}and show how it can automatically improve code quality.${NC}"
echo

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY environment variable is not set.${NC}"
    echo -e "${YELLOW}Please set your OpenAI API key:${NC}"
    echo -e "${YELLOW}export OPENAI_API_KEY=your-api-key${NC}"
    exit 1
fi

# Check if the knowledge graph exists
if [ ! -f ~/.arc/graph.db ]; then
    echo -e "${YELLOW}Knowledge graph not found. Building a new graph...${NC}"
    arc build --github
else
    echo -e "${GREEN}Using existing knowledge graph.${NC}"
fi

# Run the self-healing loop demo
echo -e "${BLUE}Running self-healing loop on sample code...${NC}"
python demo/scripts/run_self_healing_demo.py --repo . --file demo/test_files/sample_code.py --output demo/test_files/improved_code.py --iterations 2

# Check if the demo was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Demo completed successfully!${NC}"
    echo -e "${BLUE}You can find the improved code at:${NC} demo/test_files/improved_code.py"
    
    # Show a diff of the changes
    echo -e "${YELLOW}Showing diff between original and improved code:${NC}"
    diff -u demo/test_files/sample_code.py demo/test_files/improved_code.py || true
    
    echo
    echo -e "${GREEN}=== Demo Complete ===${NC}"
else
    echo -e "${RED}Demo failed. Please check the error messages above.${NC}"
fi
