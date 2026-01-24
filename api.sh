#!/bin/bash
SESSION_ID="550e8400-e29b-41d4-a716-446655440001"

echo "Question 1..."
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What are data subject rights?\", \"session_id\": \"$SESSION_ID\"}" | jq .response

echo -e "\nQuestion 2..."
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Explain that simpler\", \"session_id\": \"$SESSION_ID\"}" | jq .response

echo -e "\nGetting history..."
curl -s http://localhost:8000/chat/history/$SESSION_ID | jq '.messages[] | {role, content: (.user_message // .response)}'