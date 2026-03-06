# ─── Backend ───────────────────────────
FROM python:3.12-slim AS backend

WORKDIR /app/backend

# Install git (needed for cloning repos)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# ─── Frontend ──────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build


# ─── Production ────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

# Install git + nginx
RUN apt-get update && apt-get install -y git nginx && rm -rf /var/lib/apt/lists/*

# Backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/

# Frontend static files
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Nginx config
COPY nginx.conf /etc/nginx/sites-available/default

# Startup script
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 80
CMD ["./start.sh"]
