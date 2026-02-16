"""
AI Resume Tailor
Upload your resume + paste a job description → get a tailored resume in seconds.
"""

import base64
import io
import json
import os
import re
import shutil
import html as html_lib
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import pdfplumber
import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
from jinja2 import Template

from ai_utils import (
    PROVIDER_CONFIG,
    TEMPERATURE,
    _get_provider,
    get_ai_client,
    _chat,
    _web_search,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TEMPLATE_PATH = Path(__file__).parent / "resume_template.html"

# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)

# ---------------------------------------------------------------------------
# Job description scraping (multi-tier)
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


def _extract_linkedin_job_id(url: str) -> str | None:
    m = re.search(r"jobs/view/(?:.*?[-/])?(\d{8,})", url)
    if m:
        return m.group(1)
    m = re.search(r"currentJobId=(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/(\d{8,})/?(?:\?|$)", url)
    if m:
        return m.group(1)
    return None


def _scrape_linkedin_guest_api(job_id: str) -> str | None:
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.ok and len(resp.text) > 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            parts = []
            title_el = soup.select_one("h2.top-card-layout__title")
            if title_el:
                parts.append(f"Job Title: {title_el.get_text(strip=True)}")
            company_el = soup.select_one("a.topcard__org-name-link, span.topcard__flavor")
            if company_el:
                parts.append(f"Company: {company_el.get_text(strip=True)}")
            loc_el = soup.select_one("span.topcard__flavor--bullet")
            if loc_el:
                parts.append(f"Location: {loc_el.get_text(strip=True)}")
            desc_el = soup.select_one(
                "div.show-more-less-html__markup, "
                "div.description__text, "
                "section.show-more-less-html"
            )
            if desc_el:
                parts.append(f"\n{desc_el.get_text(separator=chr(10), strip=True)}")
            text = "\n".join(parts)
            if len(text) > 100:
                return text
    except Exception:
        pass
    return None


def scrape_job_url(url: str) -> str | None:
    if not url or not url.startswith("http"):
        return None
    parsed = urlparse(url)

    if "linkedin.com" in parsed.netloc:
        job_id = _extract_linkedin_job_id(url)
        if job_id:
            result = _scrape_linkedin_guest_api(job_id)
            if result:
                return result

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0]
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    desc = data.get("description", "")
                    title = data.get("title", "")
                    org = data.get("hiringOrganization", {})
                    company = org.get("name", "") if isinstance(org, dict) else ""
                    text = f"Job Title: {title}\nCompany: {company}\n\n{desc}"
                    clean = BeautifulSoup(text, "html.parser").get_text(separator="\n")
                    if len(clean) > 100:
                        return clean.strip()
            except (json.JSONDecodeError, AttributeError):
                continue

        for selector in [
            "div.show-more-less-html__markup", "div.description__text",
            "div.job-description", "div.jobsearch-jobDescriptionText",
            "div[data-testid='jobDescription']", "article", "main",
        ]:
            el = soup.select_one(selector)
            if el and len(el.get_text(strip=True)) > 200:
                return el.get_text(separator="\n", strip=True)

        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            if len(text) > 200:
                return text
    except Exception:
        pass

    try:
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
        resp = requests.get(cache_url, headers=HEADERS, timeout=10)
        if resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")
            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return text
    except Exception:
        pass

    return None

# ---------------------------------------------------------------------------
# Claude API calls
# ---------------------------------------------------------------------------

def parse_json_response(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {}


def analyze_job_description(client: OpenAI, jd_text: str, model: str) -> dict:
    prompt = f"""Analyze this job description and extract structured information.

JOB DESCRIPTION:
{jd_text}

Return ONLY valid JSON with this exact structure:
{{
    "company": "Company name",
    "role": "Job title / role",
    "department": "Department if mentioned",
    "seniority": "Entry/Mid/Senior/Lead/Executive",
    "requirements": {{
        "must_have": ["requirement 1", "requirement 2"],
        "nice_to_have": ["requirement 1", "requirement 2"]
    }},
    "ats_keywords": ["keyword1", "keyword2", "keyword3"],
    "soft_skills": ["skill1", "skill2"],
    "key_responsibilities": ["resp1", "resp2"],
    "industry": "Industry/domain"
}}"""
    return parse_json_response(_chat(client, prompt, model))


def research_company(client: OpenAI, jd_analysis: dict, model: str) -> dict:
    company = jd_analysis.get("company", "Unknown")
    role = jd_analysis.get("role", "Unknown")
    industry = jd_analysis.get("industry", "")

    search_queries = [
        f"{company} company culture values working environment",
        f"{company} {role} hiring what they look for in candidates",
        f"{company} glassdoor reviews employee experience",
        f"{company} recent news funding products 2024 2025",
        f'"{company}" LinkedIn who gets hired backgrounds',
        f"{role} {industry} job requirements skills needed 2025",
        f"{company} {role} interview process tips",
        f"{role} resume tips keywords job boards {industry}",
    ]
    web_results = _web_search(search_queries, max_results_per_query=4)

    prompt = f"""You are a career research expert. Using the web research below AND your own knowledge, provide actionable insights to help a candidate tailor their resume for this specific role.

COMPANY: {company}
ROLE: {role}
INDUSTRY: {industry}

WEB RESEARCH RESULTS:
{web_results}

Based on ALL of the above, return ONLY valid JSON:
{{
    "company_overview": "2-3 sentences about what the company does, market position, recent news/funding",
    "company_culture": "Specific cultural values, work style, and traits they look for (cite specifics from research)",
    "hiring_profile": "What backgrounds/schools/companies they typically hire from, skills they value most",
    "role_insights": "What makes someone successful in this role at this company specifically, what the day-to-day looks like",
    "what_makes_you_relevant": "Key angles a candidate should emphasize to stand out for this role",
    "resume_tips": [
        "Specific actionable tip 1 for tailoring resume to this company",
        "Specific actionable tip 2 based on their culture/values",
        "Specific actionable tip 3 based on what they look for in candidates",
        "Specific actionable tip 4 about role-specific positioning"
    ],
    "keywords_to_emphasize": ["keyword1", "keyword2", "keyword3"],
    "tone_recommendation": "How the resume should read based on the company's culture",
    "sources_used": ["brief note on useful web sources"]
}}"""
    return parse_json_response(_chat(client, prompt, model, max_tokens=2500))


def tailor_resume(client: OpenAI, resume_text: str, jd_analysis: dict, company_research: dict, model: str) -> dict:
    prompt = f"""You are an expert resume writer. Tailor this resume for the target role.

CRITICAL FORMAT RULES:
- You MUST preserve the EXACT same resume structure, section order, and section names as the original.
- Keep every section that exists in the original (e.g., if it has "Professional Profile", "Work Experience", "Education", "Skills & Interests", "Volunteering Experience" — keep ALL of them with those exact names).
- If the original has sections like "Projects", "Certifications", "Publications", "Awards", "Languages" etc., keep those too.
- Keep the same company names, role titles, dates, and locations EXACTLY as they appear.
- Do NOT add, remove, reorder, merge, or split sections or subsections.
- ONLY rewrite the text content (bullets, profile, skills) to better target the job.

CHANGE TRACKING:
- Wrap any text you've CHANGED or REWORDED in double brackets like [[changed text here]].
- Text that is identical to the original should NOT have brackets.
- Example: "Drove [[end-to-end GTM strategy for AI product]], building a community of 50+ HR professionals"

ORIGINAL RESUME:
{resume_text}

TARGET JOB ANALYSIS:
{json.dumps(jd_analysis, indent=2)}

COMPANY & ROLE RESEARCH:
{json.dumps(company_research, indent=2)}

CONTENT RULES:
1. NEVER fabricate experiences, companies, or degrees. Only rewrite what exists.
2. Rewrite the professional profile / summary to target this specific role and company.
3. Reword experience bullets using the CAR framework (Challenge → Action → Result).
4. If specific metrics are missing, insert bold placeholders like **X%**, **Y users**, **$Z revenue**.
5. Weave ATS keywords naturally where truthful.
6. Match the tone recommendation from company research.

Return ONLY valid JSON with this DYNAMIC structure:
{{
    "name": "Full Name (unchanged)",
    "contact_line": "location | linkedin | phone | email (same format as original, pipe-separated)",
    "sections": [
        {{
            "title": "The exact section heading from the original resume",
            "type": "text",
            "content": "Paragraph text with [[changed parts]] marked"
        }},
        {{
            "title": "Work Experience",
            "type": "experience",
            "entries": [
                {{
                    "left_primary": "Company Name (unchanged)",
                    "right_primary": "Location (unchanged)",
                    "left_secondary": "Role Title (unchanged)",
                    "right_secondary": "Dates (unchanged)",
                    "subsections": [
                        {{
                            "title": "Subsection name if any (e.g. GTM)",
                            "bullets": ["Bullet with [[changed portions]] marked"]
                        }}
                    ],
                    "bullets": ["Bullet if no subsections, with [[changes]] marked"]
                }}
            ]
        }},
        {{
            "title": "Education",
            "type": "experience",
            "entries": [
                {{
                    "left_primary": "School Name",
                    "right_primary": "Location",
                    "left_secondary": "Degree, (Grade: X)",
                    "right_secondary": "Year - Year",
                    "subsections": [],
                    "bullets": []
                }}
            ]
        }},
        {{
            "title": "Skills & Interests",
            "type": "list",
            "lines": [
                "Skill Category 1 | Skill Category 2 | [[new skill]] | ...",
                "<b>Interests</b> - interest1, interest2, ..."
            ]
        }},
        {{
            "title": "Volunteering Experience",
            "type": "experience",
            "entries": [
                {{
                    "left_primary": "Organization",
                    "right_primary": "Location",
                    "left_secondary": "",
                    "right_secondary": "",
                    "subsections": [],
                    "bullets": ["Bullet text"]
                }}
            ]
        }}
    ],
    "match_notes": {{
        "keywords_used": ["keyword1", "keyword2"],
        "keywords_missing": ["keyword3"],
        "match_score": 85,
        "suggestions": ["Suggestion for improving match"]
    }}
}}

SECTION TYPE GUIDE:
- "text": For paragraph sections like Professional Profile, Summary, Objective
- "experience": For ANY section with items that have left/right columns (company/location, school/location, org/location) and optional bullets. Use for Work Experience, Education, Projects, Certifications, Volunteering, etc.
- "list": For sections with simple text lines (Skills, Languages, Interests, etc.). Lines can contain <b>bold</b> for labels.

IMPORTANT:
- For experience items WITH subsections (e.g., GTM, Product Marketing under one company), put bullets INSIDE subsections and leave top-level "bullets" as [].
- For items WITHOUT subsections, put bullets in top-level "bullets" and leave "subsections" as [].
- Include ALL sections from the original resume in the same order. Do not skip any.
- The "sections" array should have one entry per section heading in the original resume."""

    return parse_json_response(_chat(client, prompt, model, max_tokens=4096))

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_resume_html(data: dict, highlight_changes: bool = True) -> str:
    """Render resume data into HTML. If highlight_changes, convert [[...]] to underlines."""
    template_str = TEMPLATE_PATH.read_text()
    template = Template(template_str)
    html = template.render(
        name=data.get("name", ""),
        contact_line=data.get("contact_line", ""),
        sections=data.get("sections", []),
    )

    if highlight_changes:
        html = html.replace("[[", '<span class="changed">').replace("]]", "</span>")
    else:
        html = html.replace("[[", "").replace("]]", "")

    return html


def _find_chrome() -> str | None:
    """Find Chrome/Chromium binary across macOS and Linux."""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/snap/bin/chromium",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    return None


def generate_pdf(resume_data: dict) -> bytes:
    """Generate PDF by rendering the clean HTML template through headless Chrome."""
    chrome = _find_chrome()
    if not chrome:
        st.warning("Chrome/Chromium not found. Install Chrome for PDF downloads: https://www.google.com/chrome/")
        return b""

    clean_html = render_resume_html(resume_data, highlight_changes=False)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(clean_html)
        html_path = f.name

    pdf_path = html_path.replace(".html", ".pdf")

    try:
        subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                f"--print-to-pdf={pdf_path}",
                "--no-pdf-header-footer",
                html_path,
            ],
            capture_output=True,
            timeout=30,
        )
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            with open(pdf_path, "rb") as f:
                return f.read()
    except Exception as e:
        st.warning(f"PDF generation error: {e}")
    finally:
        for p in (html_path, pdf_path):
            try:
                os.unlink(p)
            except OSError:
                pass

    return b""

# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def _embed_pdf_iframe(pdf_bytes: bytes, height: int = 750) -> str:
    """Return an HTML iframe embedding a PDF via base64 data URI."""
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    return f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" style="border: 1px solid #ccc; border-radius: 4px;"></iframe>'


def main():
    st.set_page_config(
        page_title="AI Resume Tailor",
        page_icon="*",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown("""
    <style>
        .stApp { max-width: 1300px; margin: 0 auto; }
        .big-title { font-size: 2.2rem; font-weight: 700; margin-bottom: 0; }
        .subtitle { font-size: 1.1rem; color: #888; margin-top: 0; }
        div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 8px; }
        .match-score { font-size: 2rem; font-weight: bold; }
        .keyword-tag {
            display: inline-block; padding: 2px 10px; margin: 2px 4px;
            border-radius: 12px; font-size: 0.85rem;
        }
        .keyword-hit { background: #1a4d2e; color: #4ade80; border: 1px solid #4ade80; }
        .keyword-miss { background: #4d1a1a; color: #f87171; border: 1px solid #f87171; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="big-title">AI Resume Tailor</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Upload your resume, paste a job description, get a tailored resume in seconds.</p>',
        unsafe_allow_html=True,
    )

    # Model selector based on configured provider
    provider = _get_provider()
    pconfig = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["anthropic"])
    if provider == "proxy":
        selected_model = st.text_input(
            "Model name (type your proxy's model ID)",
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

    # ---- Input section ----
    col_resume, col_jd = st.columns(2, gap="large")

    with col_resume:
        st.subheader("Your Resume")
        upload_method = st.radio(
            "Input method", ["Upload PDF", "Paste text"],
            horizontal=True, label_visibility="collapsed",
        )
        resume_text = ""
        if upload_method == "Upload PDF":
            uploaded = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
            if uploaded:
                raw_bytes = uploaded.read()
                # Store original PDF for side-by-side comparison
                st.session_state["original_pdf_bytes"] = raw_bytes
                with st.spinner("Extracting text..."):
                    resume_text = extract_text_from_pdf(raw_bytes)
                if resume_text:
                    st.success(f"Extracted {len(resume_text.split())} words")
                    with st.expander("Preview extracted text"):
                        st.text(resume_text)
                else:
                    st.warning("Could not extract text. Try pasting manually.")
        else:
            resume_text = st.text_area(
                "Paste your resume text", height=300,
                placeholder="Paste your full resume text here...",
            )

    with col_jd:
        st.subheader("Job Description(s)")
        num_jobs = st.number_input("Number of jobs to tailor for", min_value=1, max_value=3, value=1)

        jd_inputs: list[dict] = []
        for i in range(num_jobs):
            label = f"Job {i+1}" if num_jobs > 1 else "Target Job"
            with st.expander(label, expanded=(i == 0)):
                jd_method = st.radio(
                    "Input method", ["Paste JD", "LinkedIn / URL (beta)"],
                    horizontal=True, key=f"jd_method_{i}", label_visibility="collapsed",
                )
                jd_text = ""
                if jd_method == "LinkedIn / URL (beta)":
                    url = st.text_input(
                        "Job posting URL", key=f"jd_url_{i}",
                        placeholder="https://www.linkedin.com/jobs/view/...",
                    )
                    if url:
                        with st.spinner("Fetching job description..."):
                            scraped = scrape_job_url(url)
                        if scraped:
                            jd_text = scraped
                            st.success(f"Fetched {len(scraped.split())} words")
                            with st.expander("Preview scraped text"):
                                st.text(scraped)
                        else:
                            st.warning("Could not scrape. Paste the JD manually below.")
                    fallback = st.text_area(
                        "Or paste the JD manually", key=f"jd_fallback_{i}",
                        height=200, placeholder="Paste job description here as fallback...",
                    )
                    if fallback:
                        jd_text = fallback
                else:
                    jd_text = st.text_area(
                        "Paste the job description", key=f"jd_text_{i}",
                        height=250, placeholder="Paste the full job description here...",
                    )
                if jd_text:
                    jd_inputs.append({"index": i, "text": jd_text})

    # ---- Tailor button ----
    st.divider()
    can_run = bool(resume_text and jd_inputs)
    if not can_run:
        st.info("Upload/paste your resume and at least one job description to get started.")

    if st.button("Tailor My Resume", type="primary", use_container_width=True, disabled=not can_run):
        client = get_ai_client()
        model = selected_model
        results: list[dict] = []
        progress = st.progress(0, text="Starting...")

        for idx, jd_input in enumerate(jd_inputs):
            job_num = jd_input["index"] + 1
            total_steps = len(jd_inputs) * 5
            base_step = idx * 5

            progress.progress((base_step + 1) / total_steps, text=f"Job {job_num}: Analyzing job requirements...")
            jd_analysis = analyze_job_description(client, jd_input["text"], model)
            if not jd_analysis:
                st.error(f"Job {job_num}: Failed to analyze job description.")
                continue

            progress.progress((base_step + 2) / total_steps, text=f"Job {job_num}: Researching {jd_analysis.get('company', 'company')}...")
            company_intel = research_company(client, jd_analysis, model)

            progress.progress((base_step + 3) / total_steps, text=f"Job {job_num}: Tailoring your resume with AI...")
            tailored = tailor_resume(client, resume_text, jd_analysis, company_intel, model)
            if not tailored:
                st.error(f"Job {job_num}: Failed to tailor resume.")
                continue

            progress.progress((base_step + 4) / total_steps, text=f"Job {job_num}: Rendering resume...")
            match_notes = tailored.pop("match_notes", {})
            html_with_highlights = render_resume_html(tailored, highlight_changes=True)
            html_clean = render_resume_html(tailored, highlight_changes=False)

            progress.progress((base_step + 5) / total_steps, text=f"Job {job_num}: Generating PDF...")
            pdf_bytes = generate_pdf(tailored)

            results.append({
                "job_num": job_num,
                "jd_analysis": jd_analysis,
                "company_intel": company_intel,
                "tailored": tailored,
                "match_notes": match_notes,
                "html_highlighted": html_with_highlights,
                "html_clean": html_clean,
                "pdf_bytes": pdf_bytes,
            })

        progress.progress(1.0, text="Done!")
        st.session_state["results"] = results
        st.session_state["original_resume"] = resume_text

    # ---- Display results ----
    if "results" in st.session_state and st.session_state["results"]:
        results = st.session_state["results"]
        st.divider()
        st.subheader("Tailored Resumes")

        if len(results) == 1:
            tab_labels = ["Tailored Resume"]
        else:
            tab_labels = [
                f"Job {r['job_num']}: {r['jd_analysis'].get('company', '')} — {r['jd_analysis'].get('role', '')}"
                for r in results
            ]

        tabs = st.tabs(tab_labels)

        for tab, result in zip(tabs, results):
            with tab:
                jd_a = result["jd_analysis"]
                match = result["match_notes"]
                intel = result.get("company_intel", {})

                # ---- Match info bar ----
                mcol1, mcol2, mcol3 = st.columns([1, 2, 2])
                with mcol1:
                    score = match.get("match_score", "—")
                    st.markdown(f'<div class="match-score">{score}%</div>', unsafe_allow_html=True)
                    st.caption("Match Score")
                with mcol2:
                    st.markdown("**Target Role**")
                    st.write(f"{jd_a.get('role', 'N/A')} at {jd_a.get('company', 'N/A')}")
                with mcol3:
                    st.markdown("**Seniority**")
                    st.write(jd_a.get("seniority", "N/A"))

                # ---- Keyword visualization ----
                kw_used = match.get("keywords_used", [])
                kw_missing = match.get("keywords_missing", [])
                if kw_used or kw_missing:
                    st.markdown("**ATS Keywords**")
                    kw_html = ""
                    for kw in kw_used:
                        kw_html += f'<span class="keyword-tag keyword-hit">{html_lib.escape(str(kw))}</span>'
                    for kw in kw_missing:
                        kw_html += f'<span class="keyword-tag keyword-miss">{html_lib.escape(str(kw))}</span>'
                    st.markdown(kw_html, unsafe_allow_html=True)
                    st.caption("Green = in resume | Red = missing (consider adding)")

                # ---- Company Research ----
                if intel:
                    with st.expander("Company & Role Research", expanded=False):
                        r1, r2 = st.columns(2)
                        with r1:
                            st.markdown("**Company Overview**")
                            st.write(intel.get("company_overview", "N/A"))
                            st.markdown("**Culture & Values**")
                            st.write(intel.get("company_culture", "N/A"))
                            st.markdown("**Hiring Profile**")
                            st.write(intel.get("hiring_profile", "N/A"))
                        with r2:
                            st.markdown("**Role Insights**")
                            st.write(intel.get("role_insights", "N/A"))
                            st.markdown("**What Makes You Relevant**")
                            st.write(intel.get("what_makes_you_relevant", "N/A"))
                            st.markdown("**Tone Recommendation**")
                            st.write(intel.get("tone_recommendation", "N/A"))
                            tips = intel.get("resume_tips", [])
                            if tips:
                                st.markdown("**Resume Tips**")
                                for t in tips:
                                    st.write(f"- {t}")

                # ---- Suggestions ----
                suggestions = match.get("suggestions", [])
                if suggestions:
                    with st.expander("AI Suggestions"):
                        for s in suggestions:
                            st.write(f"- {s}")

                st.divider()

                # ---- View toggle ----
                view_mode = st.radio(
                    "View",
                    ["Tailored Resume", "Before vs After (Side by Side)"],
                    horizontal=True,
                    key=f"view_{result['job_num']}",
                )

                if view_mode == "Tailored Resume":
                    st.caption("Green underlines show what was changed from the original.")
                    st.components.v1.html(result["html_highlighted"], height=900, scrolling=True)

                else:  # Side by side
                    st.caption("**Left**: Original resume  |  **Right**: Tailored (green underlines = changes)")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Original Resume**")
                        orig_pdf = st.session_state.get("original_pdf_bytes")
                        if orig_pdf:
                            st.markdown(_embed_pdf_iframe(orig_pdf, height=800), unsafe_allow_html=True)
                        else:
                            st.info("Upload a PDF to see original here.")
                            st.text(st.session_state.get("original_resume", ""))
                    with c2:
                        st.markdown("**Tailored Resume**")
                        st.components.v1.html(result["html_highlighted"], height=800, scrolling=True)

                # ---- Download (clean PDF, no underlines) ----
                if result["pdf_bytes"]:
                    company = jd_a.get("company", "company").replace(" ", "_")
                    role = jd_a.get("role", "role").replace(" ", "_")
                    filename = f"Resume_{company}_{role}.pdf"
                    st.download_button(
                        label="Download PDF (clean, no underlines)",
                        data=result["pdf_bytes"],
                        file_name=filename,
                        mime="application/pdf",
                        key=f"dl_{result['job_num']}",
                        use_container_width=True,
                    )
                else:
                    st.warning("PDF generation failed. You can copy the HTML preview above.")

    # Footer
    st.divider()
    st.caption("Built with Claude AI + Streamlit | Demo for SDA Bocconi Mumbai — Future of AI and GTM")


if __name__ == "__main__":
    main()
