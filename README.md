# Refract 🔬

**See through every reference.**

When reading a research paper, citation markers like `[1]` or `(Author, Year)` tell you almost nothing about the referenced work — what it's about, why it was cited, or how it connects to the current argument. Refract automatically extracts every reference from a PDF, enriches it with metadata from Semantic Scholar, and uses LLMs to explain the citation context.

---

## Features

- **Multi-style Citation Parsing** — Automatically detects and parses both numbered `[n]` and author-year `(Author, Year)` citation formats
- **Semantic Scholar Integration** — Retrieves title, authors, abstract, citation count, fields of study, and TL;DR for each reference
- **Citation Context Extraction** — Locates where each reference is cited in the body text and extracts surrounding context
- **AI-powered Citation Analysis** — Uses Claude or GPT to explain *why* a reference was cited in a given context
- **Glass-morphism UI** — Clean, translucent-overlay-inspired interface built with Streamlit
- **JSON Export** — Download the full enriched reference dataset for further analysis

---

## Quick Start

```bash
# Clone
git clone https://github.com/LDY5388/refract.git
cd refract

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

---

## Usage

1. Upload a research paper (PDF)
2. Refract parses references and fetches metadata from Semantic Scholar
3. Browse each reference card to see:
   - Title, authors, year, and citation count
   - TL;DR and abstract preview
   - In-text citation context
   - AI-generated explanation of why the paper was cited (requires API key)

---

## Configuration

### LLM API (Optional)

Select an API provider in the sidebar and enter your key to enable AI citation analysis.

| Provider | Model | Purpose |
|----------|-------|---------|
| Anthropic | claude-sonnet-4-20250514 | Citation context summarization |
| OpenAI | gpt-4o-mini | Citation context summarization |
| none | — | Metadata only (no LLM) |

All core features (reference parsing + Semantic Scholar enrichment) work without an API key.

---

## Supported Citation Styles

| Style | Example | Status |
|-------|---------|--------|
| Numbered | `[1]`, `[2,3]`, `[1-5]` | ✅ Supported |
| Author-Year (parenthetical) | `(Zhou et al., 2013)` | ✅ Supported |
| Author-Year (inline) | `Zhou et al. (2013)` | ✅ Supported |
| Author-Year (multi-author) | `Hastie & Tibshirani (1990)` | ✅ Supported |

---

## Project Structure

```
refract/
├── app.py             # Streamlit main application
├── parser.py          # PDF text extraction & multi-style reference parsing
├── scholar.py         # Semantic Scholar API client
├── summarizer.py      # LLM-based citation context summarizer
├── requirements.txt
└── README.md
```

---

## Roadmap

- [x] Phase 1: Streamlit MVP
- [ ] Phase 2: Chrome Extension (targeting arXiv HTML)
- [ ] Phase 3: PDF viewer overlay with broad site support

---

## Limitations

- Semantic Scholar API rate limit: ~100 requests per 5 minutes (free tier)
- Reference section detection accuracy may vary depending on PDF structure
- Footnote-style citations are not yet supported

---

## License

MIT

---

<p align="center">
  <strong>Refract</strong> — See through every reference.
</p>
