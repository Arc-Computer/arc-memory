#!/bin/bash

# Colors for better terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Arc Memory: Code Time Machine Demo ===${NC}\n"

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}Warning: OPENAI_API_KEY environment variable is not set.${NC}"
    echo -e "${YELLOW}Some features may not work correctly.${NC}"
    echo -e "${YELLOW}Set your OpenAI API key with: export OPENAI_API_KEY=your-api-key${NC}\n"
fi

# Check if the knowledge graph exists
if [ ! -f ~/.arc/graph.db ]; then
    echo -e "${YELLOW}Knowledge graph not found. Building a new graph...${NC}"
    arc build --github
else
    echo -e "${GREEN}Using existing knowledge graph.${NC}"
fi

# Get the repository path
REPO_PATH="$(pwd)"

# Default file to analyze
DEFAULT_FILE="arc_memory/sdk/core.py"

# Get the file to analyze from command line argument or use default
FILE_PATH=${1:-$DEFAULT_FILE}

echo -e "${BLUE}Running Code Time Machine on file: ${FILE_PATH}${NC}\n"

# Check if reasoning should be enabled
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}Reasoning engine will be disabled due to missing API key.${NC}"
    REASONING_FLAG="--no-reasoning"
else
    echo -e "${GREEN}Reasoning engine will be enabled with model: o4-mini${NC}"
    REASONING_FLAG="--reasoning"
fi

# Run the Code Time Machine demo
python -m demo.code_time_machine.main --repo "$REPO_PATH" --file "$FILE_PATH" $REASONING_FLAG

# Check if the demo was successful
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Demo completed successfully!${NC}"
else
    echo -e "\n${YELLOW}Demo encountered some issues. Please check the error messages above.${NC}"
fi
