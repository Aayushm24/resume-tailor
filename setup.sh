#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo ""
echo "========================================="
echo "   AI Resume Tailor — Setup"
echo "========================================="
echo ""

# ---- .env setup ----
if [ -f .env ]; then
    echo "Found existing .env file."
    read -rp "Reconfigure? (y/N): " reconfig
    if [[ ! "$reconfig" =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env"
    else
        rm .env
    fi
fi

if [ ! -f .env ]; then
    echo "Choose your AI provider:"
    echo ""
    echo "  1) Claude (Anthropic)  — recommended"
    echo "  2) GPT (OpenAI)"
    echo "  3) Gemini (Google)     — free tier available"
    echo ""
    read -rp "Enter choice [1]: " choice
    choice=${choice:-1}

    case $choice in
        1)
            provider="anthropic"
            key_name="ANTHROPIC_API_KEY"
            echo ""
            echo "Get your key at: https://console.anthropic.com/"
            ;;
        2)
            provider="openai"
            key_name="OPENAI_API_KEY"
            echo ""
            echo "Get your key at: https://platform.openai.com/api-keys"
            ;;
        3)
            provider="google"
            key_name="GOOGLE_API_KEY"
            echo ""
            echo "Get your key at: https://aistudio.google.com/apikey"
            ;;
        *)
            echo "Invalid choice. Defaulting to Claude."
            provider="anthropic"
            key_name="ANTHROPIC_API_KEY"
            ;;
    esac

    read -rp "Paste your API key: " api_key

    if [ -z "$api_key" ]; then
        echo "Error: API key cannot be empty."
        exit 1
    fi

    cat > .env <<EOF
AI_PROVIDER=$provider
$key_name=$api_key
EOF

    echo ""
    echo "Saved .env (provider=$provider)"
fi

# ---- Python venv ----
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Installing dependencies..."
source .venv/bin/activate
pip install -q -r requirements.txt

# ---- Chrome check ----
chrome_found=false
for p in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/usr/bin/google-chrome" \
    "/usr/bin/google-chrome-stable" \
    "/usr/bin/chromium-browser" \
    "/usr/bin/chromium" \
    "/snap/bin/chromium"; do
    if [ -x "$p" ] 2>/dev/null; then
        chrome_found=true
        break
    fi
done

if ! $chrome_found && ! command -v google-chrome &>/dev/null && ! command -v chromium &>/dev/null; then
    echo ""
    echo "WARNING: Google Chrome or Chromium not found."
    echo "PDF download will not work without it."
    echo "Install Chrome: https://www.google.com/chrome/"
    echo ""
fi

# ---- Launch ----
echo ""
echo "========================================="
echo "   Starting AI Resume Tailor..."
echo "   Opening http://localhost:8501"
echo "========================================="
echo ""

streamlit run app.py
