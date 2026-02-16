# AI GTM Toolkit

Three AI-powered demos built for the **SDA Bocconi Mumbai** session on **"AI and the Future of GTM"**.

Built by one person with AI to show what's possible.

## Demos

| # | Demo | Command | What It Does |
|---|------|---------|--------------|
| 1 | AI Resume Tailor | `streamlit run app.py` | Upload resume + JD → tailored resume in seconds |
| 2 | AI Landing Page Builder | `streamlit run website_generator.py` | Describe product → full landing page HTML |
| 3 | AI Competitor Intel | `streamlit run competitor_intel.py` | Paste two URLs → comparative battle card |

## Quick Start

```bash
git clone https://github.com/Aayushm24/resume-tailor.git
cd resume-tailor
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` with your API key (you only need **one**):

```bash
# Pick your provider
AI_PROVIDER=anthropic          # or: openai, google, proxy

# Add your API key (just the one matching your provider)
ANTHROPIC_API_KEY=sk-ant-...   # Get from https://console.anthropic.com
OPENAI_API_KEY=sk-...          # Get from https://platform.openai.com/api-keys
GOOGLE_API_KEY=AI...           # Get from https://aistudio.google.com/apikey
```

Run any demo:

```bash
streamlit run app.py                # Demo 1: Resume Tailor
streamlit run website_generator.py  # Demo 2: Landing Page Builder
streamlit run competitor_intel.py   # Demo 3: Competitor Intel
```

## Get an API Key

You only need **one** of these:

| Provider | Get Key | Free Tier |
|----------|---------|-----------|
| Claude (Anthropic) | [console.anthropic.com](https://console.anthropic.com/) | $5 credit |
| GPT (OpenAI) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Pay-as-you-go |
| Gemini (Google) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Free |

**Using a proxy (LiteLLM, Azure, etc.)?** Set `AI_PROVIDER=proxy` and add:
```bash
PROXY_BASE_URL=https://your-proxy.com
PROXY_API_KEY=your-token
```

## What Each Demo Does

### Demo 1: AI Resume Tailor (`app.py`)
1. **Extracts** your resume from a PDF upload
2. **Analyzes** the job description (paste or scrape from LinkedIn)
3. **Researches** the company via web search (culture, hiring patterns, role insights)
4. **Tailors** your resume with AI using the CAR framework (Challenge → Action → Result)
5. **Highlights** changes with green underlines (removed in the download)
6. **Downloads** a clean PDF

### Demo 2: AI Landing Page Builder (`website_generator.py`)
1. Enter a product name, description, target audience, tone, and accent color
2. Optionally add key features and CTA text for more control
3. AI generates a complete dark-mode landing page with hero, features, pricing, testimonials
4. Live preview in the browser
5. Download the HTML file — ready to deploy

### Demo 3: AI Competitor Intel (`competitor_intel.py`)
1. Enter a competitor URL (e.g. `notion.com`) and your company URL (e.g. `atlan.com`)
2. AI scrapes both websites + searches for news, pricing, reviews
3. Generates a comparative battle card — strengths, weaknesses, how to win
4. Download as markdown

## Requirements

- Python 3.9+
- Google Chrome or Chromium (for PDF generation in Demo 1)

## Manual Setup (with venv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your provider and API key
streamlit run app.py
```

## Or Use the Setup Script

```bash
./setup.sh
```

The setup script will:
1. Ask you to pick an AI provider (Claude, GPT, Gemini, or LiteLLM proxy)
2. Ask for your API key
3. Install dependencies
4. Launch the app
