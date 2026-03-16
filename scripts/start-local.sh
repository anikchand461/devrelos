#!/usr/bin/env bash
# ─────────────────────────────────────────────
# DevRel-in-a-Box — Quick Start (no Docker)
# Runs backend + frontend locally for demo
# ─────────────────────────────────────────────
set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}▶ DevRel-in-a-Box — Local Quick Start${NC}"
echo "─────────────────────────────────────────"

# Check Python
python3 --version >/dev/null 2>&1 || { echo -e "${RED}✗ Python 3 not found${NC}"; exit 1; }
echo -e "${GREEN}✓ Python found${NC}"

# Check .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo -e "${CYAN}! Created .env from .env.example — add your OPENAI_API_KEY${NC}"
fi

# Install Python deps
echo -e "${CYAN}▶ Installing backend dependencies...${NC}"
cd backend
python3 -m pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Start backend (SQLite mode — no Docker needed)
echo -e "${CYAN}▶ Starting FastAPI backend on :8000...${NC}"
DATABASE_URL="sqlite+aiosqlite:///./devrel-demo.db" \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

cd ..

# Start frontend on simple HTTP server
echo -e "${CYAN}▶ Starting frontend on :3000...${NC}"
cd frontend
python3 -m http.server 3000 &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}✅ DevRel-in-a-Box is running!${NC}"
echo "─────────────────────────────────────────"
echo -e "  Widget demo:    ${CYAN}http://localhost:3000${NC}"
echo -e "  Dashboard:      ${CYAN}http://localhost:3000/dashboard/index.html${NC}"
echo -e "  API docs:       ${CYAN}http://localhost:8000/docs${NC}"
echo "─────────────────────────────────────────"
echo "Press Ctrl+C to stop"

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" SIGINT SIGTERM
wait $BACKEND_PID $FRONTEND_PID
