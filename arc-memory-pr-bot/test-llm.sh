#!/bin/bash

# Build the TypeScript code
echo "Building TypeScript code..."
npm run build

# Run the test script
echo "Running LLM integration test..."
node test-llm-integration.js
