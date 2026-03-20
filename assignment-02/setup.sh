#!/bin/bash
# ── Blind Drop Module B — Quick Setup ──────────────────────────────────────
set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Blind Drop — Module B Setup        ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── PostgreSQL ───────────────────────────────────────────────────────────────
echo "▶ Setting up PostgreSQL database..."
DB_NAME="blinddrop"
DB_USER="postgres"

psql -U $DB_USER -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
  psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;"

echo "  Running SQL scripts..."
psql -U $DB_USER -d $DB_NAME -f sql/02_project_tables.sql -q
psql -U $DB_USER -d $DB_NAME -f sql/01_core_tables.sql -q
psql -U $DB_USER -d $DB_NAME -f sql/04_seed_data.sql -q
psql -U $DB_USER -d $DB_NAME -f sql/03_indexes.sql -q
echo "  ✓ Database ready"

# ── Backend ──────────────────────────────────────────────────────────────────
echo ""
echo "▶ Installing backend dependencies..."
cd backend
pip install -r requirements.txt -q
echo "  ✓ Backend deps installed"

# ── Frontend ─────────────────────────────────────────────────────────────────
echo ""
echo "▶ Installing frontend dependencies..."
cd ../frontend
yarn install --silent
echo "  ✓ Frontend deps installed"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Setup complete!                    ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "To start the app:"
echo ""
echo "  Terminal 1:  cd backend && python app.py"
echo "  Terminal 2:  cd frontend && yarn dev"
echo ""
echo "  Frontend → http://localhost:5173"
echo "  Backend  → http://localhost:5000"
echo ""
echo "  Login: admin / password123"
echo ""
