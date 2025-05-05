#!/bin/bash

# Compile TypeScript files, ignoring errors
echo "Compiling TypeScript files..."
npx tsc --skipLibCheck --noEmitOnError=true

# Run the bot on port 3001
echo "Starting the PR Bot..."
PORT=3001 npx probot run ./dist/src/index.js
