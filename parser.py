"""
Refract - Reference Parser v2
Supports multiple citation styles:
  1. Numbered: [1], [2], [3]
  2. Author-Year: (Zhou et al., 2013), (Hastie & Tibshirani, 1990)
  3. Inline Author-Year: Zhou et al. (2013), Hastie and Tibshirani (1990)
"""

import re
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
from dataclasses import dataclass, field
from enum import Enum


class CitationStyle(Enum):
    NUMBERED = "numbered"
    AUTHOR_YEAR = "author_year"
    UNKNOWN = "unknown"


@dataclass
class ParsedReference:
    """A single parsed reference from the bibliography."""
    key: str
    raw_text: str
    authors: list[str] = field(default_factory=list)
    year: str | None = None
    extracted_title: str | None = None
    citation_contexts: list[str] = field(default_factory=list)
    search_query: str | None = None


@dataclass
class ParseResult:
    """Result of parsing a PDF."""
    style: CitationStyle
    references: dict[str, ParsedReference]
    body_text: str
    full_text: str
    total_refs: int
    error: str | None = None


# ─── Text Extraction ─────────────────────────────────────────

def extract_text(pdf_path: str) -> str:
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) is required for PDF extraction. Install with: pip install PyMuPDF")
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


# ─── Citation Style Detection ────────────────────────────────

def detect_citation_style(text: str) -> CitationStyle:
    sample = text[:15000]

    numbered_pattern = r"\[(\d+(?:\s*[,\-–]\s*\d+)*)\]"
    numbered_hits = len(re.findall(numbered_pattern, sample))

    author_year_pattern = (
        r"[A-Z][a-z]+"
        r"(?:\s+(?:et\s+al\.|&\s+[A-Z][a-z]+|and\s+[A-Z][a-z]+))?"
        r"\s*[\(,]\s*\d{4}[a-z]?\s*\)?"
    )
    author_year_hits = len(re.findall(author_year_pattern, sample))

    if author_year_hits > numbered_hits * 1.5 and author_year_hits > 10:
        return CitationStyle.AUTHOR_YEAR
    elif numbered_hits > 5:
        return CitationStyle.NUMBERED
    elif author_year_hits > 3:
        return CitationStyle.AUTHOR_YEAR
    return CitationStyle.UNKNOWN


# ─── Reference Section Detection ─────────────────────────────

def find_reference_section(text: str) -> tuple[str | None, int]:
    patterns = [
        r"\n\s*(References|Bibliography|Works Cited|Literature Cited|REFERENCES)\s*\n",
    ]
    best_match = None
    for pat in patterns:
        for match in re.finditer(pat, text):
            best_match = match

    if best_match:
        return text[best_match.start():], best_match.start()
    return None, -1


# ─── Numbered Reference Parsing ──────────────────────────────

def parse_numbered_references(ref_section: str) -> dict[str, ParsedReference]:
    entries = re.split(r"\n\s*\[(\d+)\]\s*", ref_section)
    refs = {}
    i = 1
    while i < len(entries) - 1:
        num = entries[i]
        content = re.sub(r"\s+", " ", entries[i + 1].strip())
        key = f"[{num}]"
        ref = ParsedReference(key=key, raw_text=content)
        ref.extracted_title = _extract_title_from_entry(content)
        ref.year = _extract_year(content)
        ref.authors = _extract_authors_from_entry(content)
        ref.search_query = _build_search_query(ref)
        refs[key] = ref
        i += 2
    return refs


# ─── Author-Year Reference Parsing ───────────────────────────

def parse_author_year_references(ref_section: str) -> dict[str, ParsedReference]:
    refs = {}
    entries = _split_bibliography_entries(ref_section)

    for entry_text in entries:
        entry_text = re.sub(r"\s+", " ", entry_text).strip()
        if len(entry_text) < 20:
            continue

        year = _extract_year(entry_text)
        authors = _extract_authors_from_entry(entry_text)
        title = _extract_title_from_entry(entry_text)

        if not year and not authors:
            continue

        key = _make_author_year_key(authors, year)
        base_key = key
        suffix = 1
        while key in refs:
            key = f"{base_key}_{suffix}"
            suffix += 1

        ref = ParsedReference(
            key=key,
            raw_text=entry_text,
            authors=authors,
            year=year,
            extracted_title=title,
        )
        ref.search_query = _build_search_query(ref)
        refs[key] = ref

    return refs


def _split_bibliography_entries(ref_section: str) -> list[str]:
    lines = ref_section.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"^\s*(References|Bibliography|REFERENCES)", line.strip()):
            start = i + 1
            break

    text = "\n".join(lines[start:])

    # Strategy 1: blank-line separated
    chunks = re.split(r"\n\s*\n", text)
    if len(chunks) > 3:
        return [c.strip() for c in chunks if c.strip()]

    # Strategy 2: each entry starts with Author surname
    entry_pattern = r"\n(?=[A-Z][a-zà-ü]+(?:\s+[A-Z]\.|\s*,))"
    chunks = re.split(entry_pattern, text)
    if len(chunks) > 3:
        return [c.strip() for c in chunks if c.strip()]

    # Strategy 3: split on period + newline + capital letter
    chunks = re.split(r"(?<=\.)\s*\n\s*(?=[A-Z])", text)
    return [c.strip() for c in chunks if c.strip()]


# ─── Citation Context Extraction ─────────────────────────────

def find_citation_contexts_numbered(body_text: str, ref_key: str, window: int = 300) -> list[str]:
    num = ref_key.strip("[]")
    pattern = re.compile(
        rf"\[(?:\d+\s*[,\-–]\s*)*{re.escape(num)}(?:\s*[,\-–]\s*\d+)*\]"
    )
    return _extract_contexts(body_text, pattern, window)


def find_citation_contexts_author_year(
    body_text: str, authors: list[str], year: str | None, window: int = 300
) -> list[str]:
    if not authors or not year:
        return []

    first_author = _get_surname(authors[0])
    if not first_author or len(first_author) < 2:
        return []

    fa = re.escape(first_author)
    yr = re.escape(year)

    patterns = [
        rf"{fa}\s+et\s+al\.?\s*[\(,]\s*{yr}",
        rf"\(\s*{fa}\s+et\s+al\.?,?\s*{yr}\s*\)",
        rf"{fa}\s+(?:and|&)\s+[A-Z][a-z]+\s*[\(,]\s*{yr}",
        rf"\(\s*{fa}\s+(?:and|&)\s+[A-Z][a-z]+,?\s*{yr}\s*\)",
        rf"{fa}\s*\(\s*{yr}\s*\)",
        rf"\(\s*{fa},?\s*{yr}\s*\)",
        rf"{fa}(?:\s+et\s+al\.?)?,?\s*{yr}",
    ]

    all_contexts = []
    seen_positions = set()

    for pat_str in patterns:
        pattern = re.compile(pat_str, re.IGNORECASE)
        for match in pattern.finditer(body_text):
            pos = match.start()
            if any(abs(pos - sp) < 100 for sp in seen_positions):
                continue
            seen_positions.add(pos)
            start = max(0, pos - window)
            end = min(len(body_text), match.end() + window)
            snippet = re.sub(r"\s+", " ", body_text[start:end].strip())
            all_contexts.append(snippet)

    return all_contexts[:5]


def _extract_contexts(text: str, pattern: re.Pattern, window: int) -> list[str]:
    contexts = []
    for match in pattern.finditer(text):
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        snippet = re.sub(r"\s+", " ", text[start:end].strip())
        contexts.append(snippet)
    return contexts[:5]


# ─── Helper Functions ────────────────────────────────────────

def _get_surname(author_str: str) -> str:
    """Extract surname from an author string like 'Zhou H.' or 'Durham T. J.'."""
    author_str = author_str.strip().rstrip(".,")
    if not author_str:
        return ""

    # If comma present: "Zhou, H." → surname before comma
    if "," in author_str:
        return author_str.split(",")[0].strip()

    parts = author_str.split()
    if not parts:
        return author_str

    # Walk from the end, skip initials (single letter with optional period)
    for i in range(len(parts) - 1, -1, -1):
        p = parts[i].rstrip(".")
        if len(p) == 1 and p.isupper():
            continue  # This is an initial, skip
        return parts[i]

    # All parts are initials — return the first one
    return parts[0]


def _extract_year(text: str) -> str | None:
    match = re.search(r"\(?\b((?:19|20)\d{2})[a-z]?\b\)?", text)
    return match.group(1) if match else None


def _extract_authors_from_entry(text: str) -> list[str]:
    year_match = re.search(r"\(?\b(?:19|20)\d{2}[a-z]?\b\)?", text)
    if not year_match:
        return []

    author_part = text[:year_match.start()].strip().rstrip(".(,")

    # Step 1: split on major separators: " & ", " and ", "; "
    # But also ", & " and ", and "
    chunks = re.split(r"\s*(?:,\s*&\s*|\s+&\s+|,\s*and\s+|\s+and\s+|;\s*)", author_part)

    # Step 2: within each chunk, further split authors separated by commas
    # Pattern: "Zhou H., Li L." → two authors separated by ", " before a capital
    # We split on ", " followed by a capital letter (start of new surname)
    authors = []
    for chunk in chunks:
        # Split: ", " followed by uppercase letter (new author)
        # But NOT ", " followed by an initial like "A." (which is part of same author)
        sub_authors = re.split(r",\s+(?=[A-Z][a-z])", chunk)
        for a in sub_authors:
            a = a.strip().strip(".,")
            if a and len(a) > 1 and not a.isdigit():
                authors.append(a)

    return authors


def _extract_title_from_entry(text: str) -> str | None:
    quoted = re.search(r'["\u201c](.+?)["\u201d]', text)
    if quoted:
        return quoted.group(1).strip()

    year_match = re.search(r"\(?\b(?:19|20)\d{2}[a-z]?\b\)?\.?\s*", text)
    if not year_match:
        return None

    after_year = text[year_match.end():].strip()
    after_year = re.sub(r"^[.,;:\s]+", "", after_year)

    title_match = re.match(
        r"(.+?)\.\s+(?:[A-Z]|In\s|Proceedings|Journal|The\s|IEEE|SIAM|Biometri|Nature|Chapman|CRC|Cambridge|Springer|John\s+Wiley|North-Holland|PMLR|ACM|Curran)",
        after_year,
    )
    if title_match:
        title = title_match.group(1).strip()
        if 10 < len(title) < 300:
            return title

    dot_pos = after_year.find(".")
    if dot_pos > 10:
        return after_year[:dot_pos].strip()

    return None


def _make_author_year_key(authors: list[str], year: str | None) -> str:
    if not authors:
        first = "Unknown"
    else:
        first = _get_surname(authors[0])
        first = re.sub(r"[^a-zA-Z]", "", first)
        if not first:
            first = "Unknown"
    yr = year or "XXXX"
    return f"{first}{yr}"


def _build_search_query(ref: ParsedReference) -> str:
    if ref.extracted_title:
        return ref.extracted_title[:200]
    query_parts = []
    if ref.authors:
        query_parts.append(_get_surname(ref.authors[0]))
    if ref.year:
        query_parts.append(ref.year)
    query_parts.append(ref.raw_text[:80].strip())
    return " ".join(query_parts)[:200]


# ─── Main Pipeline ───────────────────────────────────────────

def process_pdf(pdf_path: str) -> ParseResult:
    full_text = extract_text(pdf_path)
    style = detect_citation_style(full_text)
    ref_section, ref_start = find_reference_section(full_text)

    if not ref_section:
        return ParseResult(
            style=style, references={}, body_text=full_text,
            full_text=full_text, total_refs=0,
            error="Could not locate reference section",
        )

    body_text = full_text[:ref_start] if ref_start > 0 else full_text

    if style == CitationStyle.NUMBERED:
        refs = parse_numbered_references(ref_section)
        for key, ref in refs.items():
            ref.citation_contexts = find_citation_contexts_numbered(body_text, key)
    else:
        refs = parse_author_year_references(ref_section)
        for key, ref in refs.items():
            ref.citation_contexts = find_citation_contexts_author_year(
                body_text, ref.authors, ref.year
            )

    # Fallback: if author-year found too few, try numbered
    if style != CitationStyle.NUMBERED and len(refs) < 3:
        numbered_refs = parse_numbered_references(ref_section)
        if len(numbered_refs) > len(refs):
            refs = numbered_refs
            style = CitationStyle.NUMBERED
            for key, ref in refs.items():
                ref.citation_contexts = find_citation_contexts_numbered(body_text, key)

    return ParseResult(
        style=style, references=refs, body_text=body_text,
        full_text=full_text, total_refs=len(refs),
    )
