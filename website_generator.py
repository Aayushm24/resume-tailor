"""
AI Website Generator
Describe your product → get a complete landing page in seconds.
"""

import streamlit as st

from ai_utils import (
    PROVIDER_CONFIG,
    _get_provider,
    get_ai_client,
    _chat,
)


def main():
    st.set_page_config(
        page_title="AI Website Generator",
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

    st.markdown('<p class="big-title">AI Website Generator</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Describe your product and get a complete landing page in seconds.</p>',
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

    # Inputs
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("Product / Company Name *", placeholder="e.g. Atlan")
    with col2:
        product_tone = st.selectbox(
            "Tone",
            ["Professional & Modern", "Bold & Edgy", "Friendly & Approachable", "Minimal & Clean", "Enterprise & Trust"],
            index=0,
        )

    product_desc = st.text_area(
        "Product Description *",
        height=80,
        placeholder="e.g. The active metadata platform that helps data teams find, understand, and trust their data",
    )

    col3, col4 = st.columns(2)
    with col3:
        target_audience = st.text_input(
            "Target Audience",
            placeholder="e.g. Data engineers, analytics leads at mid-market SaaS companies",
        )
    with col4:
        color_accent = st.selectbox(
            "Accent Color",
            ["Blue/Purple (default)", "Green/Teal", "Orange/Amber", "Pink/Rose", "Cyan/Blue"],
            index=0,
        )

    key_features = st.text_area(
        "Key Features (optional — AI will generate if empty)",
        height=80,
        placeholder="e.g.\n- Real-time data lineage\n- Automated PII detection\n- Slack + Jira integrations\n- SOC 2 & GDPR compliant",
    )

    cta_text = st.text_input(
        "Primary CTA Text",
        placeholder="e.g. Start Free Trial, Book a Demo, Get Early Access",
    )

    can_run = bool(product_name and product_desc)
    if not can_run:
        st.info("Enter a product name and description to generate a landing page.")

    if st.button("Generate Landing Page", type="primary", use_container_width=True, disabled=not can_run):
        client = get_ai_client()

        # Build accent color mapping
        accent_map = {
            "Blue/Purple (default)": ("#667eea", "#764ba2"),
            "Green/Teal": ("#00b894", "#00cec9"),
            "Orange/Amber": ("#f39c12", "#e74c3c"),
            "Pink/Rose": ("#fd79a8", "#e84393"),
            "Cyan/Blue": ("#0984e3", "#6c5ce7"),
        }
        accent_from, accent_to = accent_map.get(color_accent, ("#667eea", "#764ba2"))

        with st.spinner("Generating landing page..."):
            system_prompt = f"""You are a world-class frontend engineer and visual designer who has built landing pages for Linear, Vercel, Stripe, and Raycast. You write production-quality HTML and CSS that wins design awards.

You generate a SINGLE self-contained HTML file with all CSS in a <style> block. The only allowed external resource is Google Fonts (Inter). No JavaScript frameworks, no external CSS, no CDN links besides Google Fonts.

═══════════════════════════════════════
CRITICAL: TEXT CONTRAST & READABILITY
═══════════════════════════════════════
THIS IS THE #1 PRIORITY. Every single piece of text MUST be readable against its background.

MANDATORY text color rules:
- ALL headings (h1, h2, h3): color #FFFFFF (pure white). NO EXCEPTIONS.
- Body/paragraph text: color rgba(255,255,255,0.85) — this is BRIGHT white, not gray
- Secondary/muted text: color rgba(255,255,255,0.6) — still clearly readable
- The MINIMUM allowed text opacity on dark backgrounds is 0.6. NEVER use 0.3 or 0.35 for readable text.
- Feature card titles: #FFFFFF
- Feature card descriptions: rgba(255,255,255,0.8)
- Navigation links: rgba(255,255,255,0.85)
- Pricing text, testimonial text, footer links: minimum rgba(255,255,255,0.7)
- Gradient text (hero headline) must use BRIGHT colors — the gradient endpoints should both be above #88 in brightness

DO NOT use these colors for text (they are invisible on dark):
- rgba(255,255,255,0.3) — BANNED for any readable text
- rgba(255,255,255,0.35) — BANNED for any readable text
- rgba(255,255,255,0.4) — BANNED for body text (only OK for decorative divider labels)
- #666, #777, #888 — BANNED
- Any gray below #999 — BANNED

═══════════════════════════════════════
LOGO BAR RULES
═══════════════════════════════════════
Do NOT generate a logo/partner bar section. Skip it entirely. It looks fake and cheapens the page. If you want social proof, use a single line like "Trusted by 500+ teams" with small colored dots, NOT company name text logos.

═══════════════════════════════════════
DESIGN SYSTEM
═══════════════════════════════════════

TYPOGRAPHY:
- Google Fonts Inter: weights 400;500;600;700;800;900
- Font stack: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif
- h1: 4rem/800, h2: 2.5rem/700, h3: 1.25rem/600
- Body: 1.05rem/400, line-height 1.7
- Letter-spacing: -0.03em on headings

COLOR PALETTE:
- Background: #09090b (near-black)
- Surface/cards: rgba(255,255,255,0.05) with 1px border rgba(255,255,255,0.1)
- Primary accent gradient: linear-gradient(135deg, {accent_from}, {accent_to})
- Text: see CRITICAL section above

LAYOUT:
- Container max-width: 1200px, centered
- Section padding: 120px 24px
- CSS Grid for features (auto-fit, minmax(320px, 1fr))
- Spacing scale: 8, 16, 24, 32, 48, 64, 96, 120px

SECTIONS TO INCLUDE:
1. HERO: min-height 90vh, centered. Pill badge, massive gradient headline, bright subtitle, two CTA buttons (primary filled + secondary outline). Animated gradient background.
2. FEATURES GRID: 3-column grid of glass cards. SVG icons, white titles, bright descriptions. Hover: translateY(-4px).
3. HOW IT WORKS: 3 numbered steps with accent gradient numbers.
4. TESTIMONIALS: 3 cards with quotes. Names bold white, roles bright muted.
5. PRICING: 3 tiers (Free, Pro highlighted, Enterprise). Checkmark bullets. Pro has accent border.
6. FINAL CTA: Bold headline, single button, subtle gradient bg.
7. FOOTER: 4 columns (Product, Company, Resources, Legal). Copyright row.

CSS ANIMATIONS:
- fadeInUp on hero content (staggered delays)
- Hover states on ALL cards and buttons
- Smooth transitions: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)
- Gradient shift animation on hero background

RESPONSIVE:
- @media (max-width: 768px): single column, smaller headings, full-width buttons

OUTPUT RULES:
- Return ONLY raw HTML starting with <!DOCTYPE html>
- No markdown fences. No explanation.
- ALL CSS in a single <style> block
- Generate realistic copy for the product. Not lorem ipsum.
- Quality comparable to linear.app, vercel.com, stripe.com"""

            # Build user prompt with all context
            context_parts = [f"PRODUCT NAME: {product_name}", f"PRODUCT DESCRIPTION: {product_desc}"]
            if target_audience:
                context_parts.append(f"TARGET AUDIENCE: {target_audience}")
            if key_features and key_features.strip():
                context_parts.append(f"KEY FEATURES:\n{key_features}")
            if cta_text:
                context_parts.append(f"PRIMARY CTA TEXT: {cta_text}")
            context_parts.append(f"TONE: {product_tone}")

            user_prompt = f"""Generate a stunning, production-quality landing page for:

{chr(10).join(context_parts)}

Write compelling marketing copy. Every headline should feel like it was written by a top SaaS copywriter. Feature names and descriptions should be specific to this product.

For testimonials, create realistic quotes from fictional people with generic titles (e.g. "Head of Engineering at a Series B startup").

For pricing, create 3 tiers that make sense for this product.

REMINDER: Every single line of text must be clearly readable. White headings (#FFFFFF). Bright body text (rgba 255,255,255,0.85). No invisible gray text. Test every color in your head against #09090b background before using it."""

            html_content = _chat(client, f"{system_prompt}\n\n{user_prompt}", selected_model, max_tokens=12000)

            # Clean markdown fences if the model wraps them
            html_content = html_content.strip()
            if html_content.startswith("```"):
                lines = html_content.split("\n")
                # Remove first line (```html) and last line (```)
                if lines[-1].strip() == "```":
                    lines = lines[1:-1]
                else:
                    lines = lines[1:]
                html_content = "\n".join(lines)

        st.session_state["generated_html"] = html_content
        st.session_state["product_name"] = product_name

    # Display results
    if "generated_html" in st.session_state:
        html = st.session_state["generated_html"]
        name = st.session_state.get("product_name", "website")

        st.divider()
        st.subheader("Generated Landing Page")

        # Live preview
        st.components.v1.html(html, height=800, scrolling=True)

        # Download button
        st.download_button(
            label="Download HTML",
            data=html,
            file_name=f"{name.lower().replace(' ', '_')}_landing_page.html",
            mime="text/html",
            use_container_width=True,
        )

    # Footer
    st.divider()
    st.caption("Built with AI + Streamlit | Demo for SDA Bocconi Mumbai — Future of AI and GTM")


if __name__ == "__main__":
    main()
