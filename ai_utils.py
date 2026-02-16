"""
Shared AI utilities for all demo apps.
Supports Anthropic, OpenAI, Google Gemini, and LiteLLM/proxy providers.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from ddgs import DDGS

load_dotenv()

TEMPERATURE = 0.3

PROVIDER_CONFIG = {
    "anthropic": {
        "models": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
        "default": "claude-sonnet-4-20250514",
        "label": "Claude (Anthropic)",
    },
    "openai": {
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        "default": "gpt-4o",
        "label": "GPT (OpenAI)",
    },
    "google": {
        "models": ["gemini-2.0-flash", "gemini-2.5-pro"],
        "default": "gemini-2.0-flash",
        "label": "Gemini (Google)",
    },
    "proxy": {
        "models": [],
        "default": "claude-sonnet-4",
        "label": "LiteLLM / Proxy",
    },
}


def _get_provider() -> str:
    return os.environ.get("AI_PROVIDER", "anthropic").lower()


def get_ai_client() -> tuple:
    """Return (provider_type, client) tuple. provider_type is 'anthropic' or 'openai'."""
    import streamlit as st

    provider = _get_provider()

    if provider == "proxy":
        api_key = (
            os.environ.get("PROXY_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        )
        base_url = (
            os.environ.get("PROXY_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("ANTHROPIC_BASE_URL")
        )
        if not base_url:
            st.error("Set PROXY_BASE_URL in your .env file (e.g. https://your-litellm-proxy.com).")
            st.stop()
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        return ("openai", OpenAI(api_key=api_key, base_url=base_url))

    elif provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            st.error("Set ANTHROPIC_API_KEY in your .env file. Run `./setup.sh` to configure.")
            st.stop()
        import anthropic
        return ("anthropic", anthropic.Anthropic(api_key=api_key))

    elif provider == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            st.error("Set GOOGLE_API_KEY in your .env file. Run `./setup.sh` to configure.")
            st.stop()
        return ("openai", OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        ))

    else:  # openai
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            st.error("Set OPENAI_API_KEY in your .env file. Run `./setup.sh` to configure.")
            st.stop()
        base_url = os.environ.get("OPENAI_BASE_URL")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return ("openai", OpenAI(**kwargs))


def _chat(client_tuple: tuple, prompt: str, model: str, max_tokens: int = 2000) -> str:
    provider_type, client = client_tuple
    if provider_type == "anthropic":
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    else:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""


def _web_search(queries: list[str], max_results_per_query: int = 5) -> str:
    all_results: list[str] = []
    try:
        ddgs = DDGS()
        for query in queries:
            try:
                results = ddgs.text(query, max_results=max_results_per_query)
                for r in results:
                    title = r.get("title", "")
                    body = r.get("body", "")
                    href = r.get("href", "")
                    all_results.append(f"[{title}]({href})\n{body}")
            except Exception:
                continue
    except Exception:
        pass
    return "\n\n---\n\n".join(all_results) if all_results else "No web results found."
