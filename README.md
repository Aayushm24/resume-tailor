# AI Resume Tailor

Upload your resume + paste a job description → get a professionally tailored resume in seconds.

Built for the SDA Bocconi Mumbai session on "Future of AI and GTM".

## Quick Start

```bash
git clone https://github.com/Aayushm24/resume-tailor.git
cd resume-tailor
./setup.sh
```

The setup script will:
1. Ask you to pick an AI provider (Claude, GPT, or Gemini)
2. Ask for your API key
3. Install dependencies
4. Launch the app at http://localhost:8501

## Get an API Key

You only need **one** of these:

| Provider | Get Key | Free Tier |
|----------|---------|-----------|
| Claude (Anthropic) | [console.anthropic.com](https://console.anthropic.com/) | $5 credit |
| GPT (OpenAI) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Pay-as-you-go |
| Gemini (Google) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Free |

**Using a proxy (LiteLLM, Azure, etc.)?** Pick option 4 during setup and enter your proxy URL + token.

## What It Does

1. **Extracts** your resume from a PDF upload
2. **Analyzes** the job description (paste or scrape from LinkedIn)
3. **Researches** the company via web search (culture, hiring patterns, role insights)
4. **Tailors** your resume with AI using the CAR framework (Challenge → Action → Result)
5. **Highlights** changes with green underlines (removed in the download)
6. **Downloads** a clean PDF that matches your original format

## Requirements

- Python 3.9+
- Google Chrome or Chromium (for PDF generation)

## Manual Setup

If you prefer not to use the setup script:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your provider and API key
streamlit run app.py
```
