"""
Refract - Citation Context Summarizer
Uses LLM API to explain why a reference was cited in context.
Supports OpenAI and Anthropic APIs.
"""

import os
import requests


def _call_openai(prompt: str, api_key: str) -> str:
    """Call OpenAI ChatCompletion API."""
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.3,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_anthropic(prompt: str, api_key: str) -> str:
    """Call Anthropic Messages API."""
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"].strip()


def summarize_citation_context(
    ref_title: str,
    ref_abstract: str | None,
    citation_contexts: list[str],
    provider: str = "anthropic",
) -> str:
    """
    Generate a concise explanation of why this reference was cited.

    Args:
        ref_title: Title of the cited paper
        ref_abstract: Abstract of the cited paper (if available)
        citation_contexts: Surrounding text snippets where this ref appears
        provider: "openai" or "anthropic"

    Returns:
        1-3 sentence explanation in Korean.
    """
    if not citation_contexts:
        return "본문에서 인용된 위치를 찾을 수 없습니다."

    # Build prompt
    contexts_str = "\n---\n".join(citation_contexts[:3])  # max 3 contexts
    abstract_str = ref_abstract or "(Abstract not available)"

    prompt = f"""You are a research assistant. A researcher is reading a paper and wants to understand why a specific reference was cited.

## Cited Paper
Title: {ref_title}
Abstract: {abstract_str}

## Citation Contexts (where this reference appears in the main paper)
{contexts_str}

## Task
In 1-3 concise sentences IN KOREAN, explain:
1. What concept or finding from the cited paper is being referenced
2. Why the authors of the main paper cited it (to support their argument, as background, as comparison, etc.)

Be specific and informative. Do not be generic."""

    api_key_openai = os.environ.get("OPENAI_API_KEY", "")
    api_key_anthropic = os.environ.get("ANTHROPIC_API_KEY", "")

    try:
        if provider == "anthropic" and api_key_anthropic:
            return _call_anthropic(prompt, api_key_anthropic)
        elif provider == "openai" and api_key_openai:
            return _call_openai(prompt, api_key_openai)
        else:
            return _fallback_summary(citation_contexts)
    except Exception as e:
        return f"(요약 생성 실패: {e})"


def _fallback_summary(citation_contexts: list[str]) -> str:
    """Simple extractive fallback when no LLM API is available."""
    if not citation_contexts:
        return "인용 컨텍스트를 찾을 수 없습니다."

    # Just return the first context, trimmed
    ctx = citation_contexts[0]
    if len(ctx) > 200:
        ctx = ctx[:200] + "..."
    return f"📍 인용 맥락: \"{ctx}\""
