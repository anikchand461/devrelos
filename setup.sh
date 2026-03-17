#!/usr/bin/env bash
# ============================================================
#  DevRelOS – One-command setup & launch
#  Usage: bash setup.sh
# ============================================================
set -e

PYTHON=${PYTHON:-python3}

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   DevRelOS  –  AI DevRel-in-a-Box Setup  ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Python check ────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
  echo "[ERROR] Python 3.9+ required. Install from https://python.org"
  exit 1
fi

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[✓] Python $PY_VERSION found"

# ── 2. Virtual environment ─────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "[*] Creating virtual environment…"
  $PYTHON -m venv .venv
fi

# Activate
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  source .venv/Scripts/activate
fi

echo "[✓] Virtual environment ready"

# ── 3. Install dependencies ────────────────────────────────
echo "[*] Installing dependencies (this may take a minute)…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "[✓] Dependencies installed"

# ── 4. .env check ─────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "[!] No .env found, copying from .env.example…"
  cp .env .env
fi
echo "[✓] .env ready"

# ── 5. Launch ─────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  Starting DevRelOS on http://localhost:8000  ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  → Chat UI:    http://localhost:8000"
echo "  → Analytics:  http://localhost:8000/analytics"
echo "  → API Docs:   http://localhost:8000/docs-ui"
echo "  → Swagger:    http://localhost:8000/swagger"
echo ""
python main.py
