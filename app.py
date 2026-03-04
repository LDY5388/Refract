"""
Refract — See through every reference.
Phase 1: Streamlit MVP v2
Supports numbered [n] and author-year citation styles.
"""

import os
import json
import streamlit as st

from parser import process_pdf, CitationStyle
from scholar import enrich_references, format_authors
from summarizer import summarize_citation_context

# ─── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Refract",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

.stApp { font-family: 'DM Sans', sans-serif; }

.refract-hero {
    text-align: center;
    padding: 2rem 0 1rem 0;
}
.refract-hero h1 {
    font-family: 'DM Sans', sans-serif;
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
}
.refract-hero p {
    color: #8892a4;
    font-size: 1.1rem;
}

.glass-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}
.glass-card:hover {
    border-color: rgba(102, 126, 234, 0.4);
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.1);
}

.ref-header {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
}
.ref-number {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 500;
    padding: 0.25rem 0.6rem;
    border-radius: 8px;
    flex-shrink: 0;
    max-width: 160px;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ref-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2e8f0;
    line-height: 1.4;
}
.ref-meta {
    font-size: 0.85rem;
    color: #8892a4;
    margin-top: 0.25rem;
}
.ref-abstract {
    font-size: 0.9rem;
    color: #a0aec0;
    line-height: 1.6;
    margin-top: 0.75rem;
    padding: 0.75rem;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    border-left: 3px solid rgba(102, 126, 234, 0.5);
}
.ref-context-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #667eea;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 1rem;
    margin-bottom: 0.4rem;
}
.ref-context {
    font-size: 0.85rem;
    color: #94a3b8;
    line-height: 1.5;
    padding: 0.6rem;
    background: rgba(102, 126, 234, 0.05);
    border-radius: 8px;
    font-style: italic;
}
.ref-tldr {
    font-size: 0.9rem;
    color: #c4b5fd;
    margin-top: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: rgba(118, 75, 162, 0.1);
    border-radius: 8px;
}
.ref-stats {
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;
    flex-wrap: wrap;
}
.stat-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #8892a4;
    background: rgba(255,255,255,0.05);
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
}
.not-found { opacity: 0.5; }

.status-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: rgba(102, 126, 234, 0.08);
    border-radius: 10px;
    margin: 1rem 0;
    font-size: 0.9rem;
    color: #a0aec0;
}

.style-badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    background: rgba(102, 126, 234, 0.15);
    color: #667eea;
    margin-left: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ─── Header ────────────────────────────────────────────────────
st.markdown("""
<div class="refract-hero">
    <h1>Refract</h1>
    <p>See through every reference.</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    llm_provider = st.selectbox(
        "LLM Provider",
        ["anthropic", "openai", "none"],
        help="API used for citation context summarization",
    )

    if llm_provider == "anthropic":
        api_key = st.text_input("Anthropic API Key", type="password")
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
    elif llm_provider == "openai":
        api_key = st.text_input("OpenAI API Key", type="password")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

    st.divider()
    st.markdown("### 📊 Stats")

    if "enriched" in st.session_state:
        enriched = st.session_state["enriched"]
        total = len(enriched)
        found = sum(1 for v in enriched.values() if v["match_status"] == "found")
        st.metric("Total References", total)
        st.metric("Matched", f"{found}/{total}")
        st.metric("Match Rate", f"{found/total*100:.0f}%" if total > 0 else "—")

    if "citation_style" in st.session_state:
        style = st.session_state["citation_style"]
        style_label = {
            CitationStyle.NUMBERED: "Numbered [1]",
            CitationStyle.AUTHOR_YEAR: "Author-Year",
            CitationStyle.UNKNOWN: "Auto-detected",
        }.get(style, "Unknown")
        st.metric("Citation Style", style_label)

    st.divider()
    st.markdown(
        "<small style='color:#64748b'>Powered by Semantic Scholar API</small>",
        unsafe_allow_html=True,
    )


# ─── File Upload ───────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload a research paper (PDF)",
    type=["pdf"],
    help="Supports both [1]-style and (Author, Year)-style citations.",
)

if uploaded:
    tmp_path = f"/tmp/{uploaded.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded.read())

    # ─── Step 1: Parse ─────────────────────────────────────────
    with st.spinner("📄 Extracting text and parsing references..."):
        parsed = process_pdf(tmp_path)

    if parsed.error:
        st.error(f"⚠️ {parsed.error}")
        st.info(
            "이 PDF에서 References 섹션을 자동으로 찾지 못했습니다. "
            "References, Bibliography 등의 섹션 헤더가 있는 논문에서 가장 잘 동작합니다."
        )
        st.stop()

    st.session_state["citation_style"] = parsed.style

    style_name = {
        CitationStyle.NUMBERED: "Numbered [n]",
        CitationStyle.AUTHOR_YEAR: "Author-Year (Author, Year)",
        CitationStyle.UNKNOWN: "Auto",
    }.get(parsed.style, "Unknown")

    st.markdown(
        f'<div class="status-bar">'
        f'✅ <strong>{parsed.total_refs}개</strong>의 레퍼런스를 파싱했습니다.'
        f'<span class="style-badge">{style_name}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ─── Step 2: Enrich ───────────────────────────────────────
    if "enriched" not in st.session_state or st.session_state.get("_last_file") != uploaded.name:
        with st.spinner("🔍 Semantic Scholar에서 메타데이터를 가져오는 중..."):
            enriched = enrich_references(parsed.references, delay=0.4)
            st.session_state["enriched"] = enriched
            st.session_state["_last_file"] = uploaded.name
            st.rerun()
    else:
        enriched = st.session_state["enriched"]

    # ─── Step 3: Display ──────────────────────────────────────
    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        show_only_found = st.toggle("매칭된 레퍼런스만 보기", value=False)
    with col2:
        sort_by = st.selectbox("정렬", ["키 순", "인용수 높은순", "최신순"])

    items = list(enriched.items())
    if sort_by == "인용수 높은순":
        items.sort(
            key=lambda x: (x[1].get("scholar_data") or {}).get("citation_count") or 0,
            reverse=True,
        )
    elif sort_by == "최신순":
        items.sort(
            key=lambda x: (x[1].get("scholar_data") or {}).get("year") or 0,
            reverse=True,
        )

    for ref_key, ref in items:
        if show_only_found and ref["match_status"] != "found":
            continue

        sd = ref.get("scholar_data")

        with st.container():
            if sd:
                title = sd["title"] or ref["raw"][:80]
                authors_str = format_authors(sd.get("authors", []))
                year = sd.get("year", "")
                citations = sd.get("citation_count", 0)
                fields = ", ".join(sd.get("fields") or [])
                abstract = sd.get("abstract", "")
                tldr = sd.get("tldr", "")
                url = sd.get("url", "")

                # Truncate long keys for display badge
                display_key = ref_key if len(ref_key) < 20 else ref_key[:17] + "…"

                card_html = f"""
                <div class="glass-card">
                    <div class="ref-header">
                        <span class="ref-number" title="{ref_key}">{display_key}</span>
                        <div>
                            <div class="ref-title">{title}</div>
                            <div class="ref-meta">{authors_str} · {year}</div>
                        </div>
                    </div>
                    <div class="ref-stats">
                        <span class="stat-badge">📊 cited {citations:,} times</span>
                        {'<span class="stat-badge">🏷️ ' + fields + '</span>' if fields else ''}
                        {'<a href="' + url + '" target="_blank" style="font-size:0.75rem;color:#667eea;">🔗 Semantic Scholar</a>' if url else ''}
                    </div>
                """

                if tldr:
                    card_html += f'<div class="ref-tldr">💡 TL;DR: {tldr}</div>'

                if abstract:
                    short_abs = abstract[:300] + "..." if len(abstract) > 300 else abstract
                    card_html += f'<div class="ref-abstract">{short_abs}</div>'

                contexts = ref.get("citation_contexts", [])
                if contexts:
                    card_html += '<div class="ref-context-label">📍 Citation Context</div>'
                    ctx = contexts[0][:250] + "..." if len(contexts[0]) > 250 else contexts[0]
                    card_html += f'<div class="ref-context">{ctx}</div>'

                card_html += "</div>"
                st.markdown(card_html, unsafe_allow_html=True)

                if contexts and llm_provider != "none":
                    with st.expander(f"🤖 AI 인용 맥락 분석 — {display_key}"):
                        summary_key = f"summary_{ref_key}"
                        if summary_key not in st.session_state:
                            with st.spinner("분석 중..."):
                                summary = summarize_citation_context(
                                    ref_title=title,
                                    ref_abstract=abstract,
                                    citation_contexts=contexts,
                                    provider=llm_provider,
                                )
                                st.session_state[summary_key] = summary
                        st.markdown(st.session_state[summary_key])
            else:
                raw_preview = ref["raw"][:120] + "..." if len(ref["raw"]) > 120 else ref["raw"]
                display_key = ref_key if len(ref_key) < 20 else ref_key[:17] + "…"
                card_html = f"""
                <div class="glass-card not-found">
                    <div class="ref-header">
                        <span class="ref-number">{display_key}</span>
                        <div>
                            <div class="ref-title" style="color:#64748b">{raw_preview}</div>
                            <div class="ref-meta">⚠️ Semantic Scholar에서 매칭되지 않음</div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

    # ─── Export ────────────────────────────────────────────────
    st.markdown("---")
    if st.button("📥 결과를 JSON으로 내보내기"):
        export_data = {}
        for ref_key, ref in enriched.items():
            export_data[ref_key] = {
                "raw_reference": ref["raw"],
                "extracted_title": ref.get("extracted_title"),
                "match_status": ref["match_status"],
                "scholar_data": ref.get("scholar_data"),
                "citation_contexts": ref.get("citation_contexts", []),
            }
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="💾 Download JSON",
            data=json_str,
            file_name=f"refract_{uploaded.name.replace('.pdf','')}.json",
            mime="application/json",
        )

else:
    st.markdown("""
    <div style="text-align:center; padding:4rem 2rem; color:#64748b">
        <div style="font-size:3rem; margin-bottom:1rem">📄</div>
        <div style="font-size:1.1rem; margin-bottom:0.5rem">PDF 논문을 업로드하세요</div>
        <div style="font-size:0.9rem; color:#8892a4">
            <strong>[1]</strong> 형식과 <strong>(Author, Year)</strong> 형식 모두 지원합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)
