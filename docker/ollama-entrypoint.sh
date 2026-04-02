#!/bin/sh
# Start Ollama server in background, pull the model, then keep serving.
set -e

ollama serve &
SERVER_PID=$!

# Wait for server to be ready
echo "Waiting for Ollama to start..."
until ollama list > /dev/null 2>&1; do
  sleep 1
done
echo "Ollama started. Pulling model..."

ollama pull "${OLLAMA_MODEL:-llama3.2:3b}"
echo "Model ready."

wait $SERVER_PID
