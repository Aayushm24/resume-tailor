#!/bin/bash
# Launch all 3 AI GTM demos on separate ports

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "Starting AI GTM Toolkit..."
echo ""
echo "  Demo 1: Resume Tailor        → http://localhost:8501"
echo "  Demo 2: Landing Page Builder  → http://localhost:8502"
echo "  Demo 3: Competitor Intel      → http://localhost:8503"
echo ""

streamlit run app.py --server.port 8501 &
streamlit run website_generator.py --server.port 8502 &
streamlit run competitor_intel.py --server.port 8503 &

echo "All 3 demos running. Press Ctrl+C to stop all."
trap "kill 0" EXIT
wait
