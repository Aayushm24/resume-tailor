"""
AI Competitor Intel
Paste a company URL → get a competitive battle card in seconds.
"""

import requests
import streamlit as st
from bs4 import BeautifulSoup

from ai_utils import (
    PROVIDER_CONFIG,
    _get_provider,
    get_ai_client,
    _chat,
    _web_search,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _scrape_website(url: str) -> str:
    """Scrape visible text from a company website."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Truncate to ~6000 chars to stay within prompt limits
        return text[:6000]
    except Exception as e:
        return f"Could not scrape website: {e}"


def main():
    st.set_page_config(
        page_title="AI Competitor Intel",
        page_icon="*",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown("""
    <style>
        .stApp { max-width: 1300px; margin: 0 auto; }
        .big-title { font-size: 2.2rem; font-weight: 700; margin-bottom: 0; }
        .subtitle { font-size: 1.1rem; color: #888; margin-top: 0; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="big-title">AI Competitor Intel</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Enter both URLs to generate a head-to-head competitive battle card.</p>',
        unsafe_allow_html=True,
    )

    # Model selector
    provider = _get_provider()
    pconfig = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["anthropic"])
    if provider == "proxy":
        selected_model = st.text_input(
            "Model name",
            value=pconfig["default"],
            help="Enter the exact model name your LiteLLM / proxy supports.",
        )
    else:
        selected_model = st.selectbox(
            f"AI Model ({pconfig['label']})",
            pconfig["models"],
            index=0,
        )
    st.divider()

    # Input — both URLs required
    col1, col2 = st.columns(2)
    with col1:
        company_url = st.text_input(
            "Competitor URL *",
            placeholder="e.g. notion.com",
            value=st.session_state.get("competitor_url", ""),
            key="competitor_url_input",
        )
        # Quick-apply examples
        ex_col1, ex_col2, ex_col3 = st.columns(3)
        with ex_col1:
            if st.button("notion.com", key="ex_c1", use_container_width=True):
                st.session_state["competitor_url"] = "notion.com"
                st.rerun()
        with ex_col2:
            if st.button("hubspot.com", key="ex_c2", use_container_width=True):
                st.session_state["competitor_url"] = "hubspot.com"
                st.rerun()
        with ex_col3:
            if st.button("salesforce.com", key="ex_c3", use_container_width=True):
                st.session_state["competitor_url"] = "salesforce.com"
                st.rerun()

    with col2:
        your_company_url = st.text_input(
            "Your Company URL *",
            placeholder="e.g. atlan.com",
            value=st.session_state.get("your_url", ""),
            key="your_url_input",
        )
        # Quick-apply examples
        ey_col1, ey_col2, ey_col3 = st.columns(3)
        with ey_col1:
            if st.button("atlan.com", key="ex_y1", use_container_width=True):
                st.session_state["your_url"] = "atlan.com"
                st.rerun()
        with ey_col2:
            if st.button("alation.com", key="ex_y2", use_container_width=True):
                st.session_state["your_url"] = "alation.com"
                st.rerun()
        with ey_col3:
            if st.button("collibra.com", key="ex_y3", use_container_width=True):
                st.session_state["your_url"] = "collibra.com"
                st.rerun()

    can_run = bool(company_url and your_company_url)
    if not can_run:
        st.info("Enter both a competitor URL and your company URL to generate a comparative battle card.")

    if st.button("Generate Comparative Battle Card", type="primary", use_container_width=True, disabled=not can_run):
        client = get_ai_client()
        progress = st.progress(0, text="Starting research...")

        # Step 1: Scrape competitor website
        progress.progress(0.10, text="Scraping competitor website...")
        competitor_website_text = _scrape_website(company_url)

        competitor_domain = company_url.replace("https://", "").replace("http://", "").strip("/")
        competitor_name = competitor_domain.split(".")[0].capitalize()

        # Step 2: Scrape your company website
        progress.progress(0.20, text="Scraping your company website...")
        your_website_text = _scrape_website(your_company_url)
        your_domain = your_company_url.replace("https://", "").replace("http://", "").strip("/")
        your_name = your_domain.split(".")[0].capitalize()

        # Step 3: Web search for competitor
        progress.progress(0.30, text=f"Researching {competitor_name}...")
        competitor_search_results = _web_search([
            f"{competitor_name} product features pricing 2025",
            f"{competitor_name} vs competitors comparison",
            f"{competitor_name} reviews strengths weaknesses",
            f"{competitor_name} recent news funding 2024 2025",
            f"{competitor_name} target customers use cases",
        ], max_results_per_query=4)

        # Step 4: Web search for your company
        progress.progress(0.45, text=f"Researching {your_name}...")
        your_search_results = _web_search([
            f"{your_name} product features pricing 2025",
            f"{your_name} reviews strengths weaknesses",
            f"{your_name} target customers use cases",
            f"{your_name} recent news funding 2024 2025",
        ], max_results_per_query=4)

        # Step 5: Head-to-head comparison search
        progress.progress(0.55, text=f"Comparing {competitor_name} vs {your_name}...")
        comparison_search_results = _web_search([
            f"{competitor_name} vs {your_name} comparison",
            f"{competitor_name} {your_name} alternative",
            f"{your_name} vs {competitor_name} reviews",
        ], max_results_per_query=4)

        # Step 6: Generate battle card
        progress.progress(0.65, text="Generating battle card with AI...")

        prompt = f"""You are a competitive intelligence analyst specializing in head-to-head competitive analysis. Create a comprehensive COMPARATIVE battle card between a competitor and the user's own company, using only publicly available information.

COMPETITOR WEBSITE ({competitor_domain}):
{competitor_website_text}

YOUR COMPANY WEBSITE ({your_domain}):
{your_website_text}

WEB RESEARCH ON COMPETITOR ({competitor_name}):
{competitor_search_results}

WEB RESEARCH ON YOUR COMPANY ({your_name}):
{your_search_results}

HEAD-TO-HEAD COMPARISON RESEARCH:
{comparison_search_results}

Generate a detailed comparative battle card in well-structured markdown with the following sections:

# Competitive Battle Card: {competitor_name} vs {your_name}

## Executive Summary
3-4 sentence overview of both companies, their market positions, and how they compare at a high level. Frame this from the perspective of someone at {your_name} trying to win against {competitor_name}.

## Company Overview — Side by Side
| Attribute | {competitor_name} | {your_name} |
|-----------|---|---|
| One-liner | ... | ... |
| Founded | ... | ... |
| HQ | ... | ... |
| Employees (est.) | ... | ... |
| Funding / Valuation | ... | ... |
| Key Segments | ... | ... |
| Market Position | ... | ... |

## Feature Comparison
Create a detailed feature-by-feature comparison table. Identify the major capability areas relevant to both products and compare them.

| Capability | {competitor_name} | {your_name} | Edge |
|-----------|---|---|---|
| (list 8-12 key capabilities) | (rating/notes) | (rating/notes) | (who wins and why) |

## Pricing Comparison
Compare pricing tiers, models, and value for money. Include specific pricing if publicly available.

| Tier / Plan | {competitor_name} | {your_name} |
|-----------|---|---|
| Free / Entry | ... | ... |
| Mid-tier | ... | ... |
| Enterprise | ... | ... |
| Pricing Model | ... | ... |

## Target Audience & ICP
- **{competitor_name}'s sweet spot:** Who are they best for? What segments do they dominate?
- **{your_name}'s sweet spot:** Who are you best for? Where do you win most often?
- **Overlap zones:** Where do you compete directly for the same customers?
- **White space:** Segments one company serves that the other doesn't.

## {competitor_name}'s Strengths (What They Do Well)
- Bullet points of their genuine advantages — be honest and objective

## {competitor_name}'s Weaknesses (Where They Fall Short)
- Bullet points of their vulnerabilities and gaps

## {your_name}'s Strengths Against {competitor_name}
- Bullet points of your genuine advantages in this matchup

## {your_name}'s Weaknesses to Shore Up
- Bullet points of areas where you are weaker — be honest so the sales team can prepare

## Key Differentiators
What fundamentally separates these two products? What is each company's "unfair advantage"?

## Talk Tracks: What to Say When {competitor_name} Comes Up
Provide 3-4 specific talk tracks a salesperson can use when a prospect mentions {competitor_name}. Each should include:
- **Situation:** When a prospect says "..."
- **Response:** A natural, confident response that acknowledges the competitor and pivots to your strengths
- **Proof point:** A specific fact, stat, or capability to back it up

## Objection Handling
| Common Objection | Why They Say It | How to Respond |
|-----------|---|---|
| (list 5-6 common objections related to choosing between these two) | (root cause) | (specific response with proof points) |

## Win/Loss Patterns
Based on available information, describe:
- **When {your_name} wins:** What deal characteristics favor you?
- **When {competitor_name} wins:** What deal characteristics favor them?
- **Tipping points:** What factors most often determine who wins the deal?

## Competitive Landmines
3-4 questions your sales team can ask prospects that expose {competitor_name}'s weaknesses (without being negative — these should be genuinely useful questions that highlight areas where you excel).

## Quick Reference Card
A 5-bullet summary a sales rep can memorize before a competitive call:
1. ...
2. ...
3. ...
4. ...
5. ...

Be specific, actionable, and honest. Use real information from the research. Do not invent facts, but you may make reasonable inferences clearly marked as such. Frame everything to be useful for a {your_name} sales or GTM team member."""

        battle_card = _chat(client, prompt, selected_model, max_tokens=4000)
        progress.progress(1.0, text="Done!")

        st.session_state["battle_card"] = battle_card
        st.session_state["company_name"] = competitor_name
        st.session_state["your_company_name"] = your_name

    # Display results
    if "battle_card" in st.session_state:
        card = st.session_state["battle_card"]
        name = st.session_state.get("company_name", "competitor")
        your_co = st.session_state.get("your_company_name", "")

        st.divider()
        st.markdown(card)

        # Download as markdown
        filename = f"{name.lower()}_vs_{your_co.lower()}_battle_card.md" if your_co else f"{name.lower()}_battle_card.md"
        st.download_button(
            label="Download Battle Card (.md)",
            data=card,
            file_name=filename,
            mime="text/markdown",
            use_container_width=True,
        )

    # Footer
    st.divider()
    st.caption("Built with AI + Streamlit | Demo for SDA Bocconi Mumbai — Future of AI and GTM")


if __name__ == "__main__":
    main()
