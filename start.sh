#!/bin/bash
# Start both nginx and the backend

# Start the FastAPI backend
cd /app/backend
uvicorn main:app --host 127.0.0.1 --port 8000 &

# Start nginx in the foreground
nginx -g 'daemon off;'
