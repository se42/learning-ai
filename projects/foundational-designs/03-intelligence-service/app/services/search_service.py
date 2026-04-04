"""
Document Search Service

A deliberately simple search implementation over a local JSON corpus.
In production, this would be backed by a vector store (pgvector, Pinecone, etc.),
but the API contract stays the same — that's the value of the service boundary.

This demo uses TF-IDF keyword matching. The upgrade path:
  1. Keyword search (this demo) — no dependencies, good enough for small corpora
  2. Embedding search — use the LLM's embeddings API for semantic similarity
  3. Vector store — pgvector, Pinecone, Weaviate for production-scale RAG
"""

import json
import math
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Load the document corpus at module import time.
# In production this would be a database query or vector store call.
# ---------------------------------------------------------------------------

_DOCS_PATH = Path(__file__).resolve().parent.parent.parent / "sample_data" / "docs.json"

_documents: list[dict] = []

try:
    with open(_DOCS_PATH) as f:
        _documents = json.load(f)
except FileNotFoundError:
    print(f"Warning: {_DOCS_PATH} not found. Search will return no results.")
except json.JSONDecodeError:
    print(f"Warning: {_DOCS_PATH} is not valid JSON. Search will return no results.")


# ---------------------------------------------------------------------------
# Simple tokenizer — split on non-alphanumeric characters, lowercase, and
# drop very short tokens. This is intentionally naive; a real implementation
# would use NLTK or spaCy.
# ---------------------------------------------------------------------------

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "it", "as", "be", "this", "that", "are",
    "was", "were", "been", "have", "has", "had", "do", "does", "did",
    "will", "would", "can", "could", "should", "may", "might", "from",
    "not", "no", "so", "if", "then", "than", "when", "what", "which",
    "who", "how", "all", "each", "every", "both", "few", "more", "most",
    "your", "you", "our", "we", "they", "their", "its", "any", "some",
}


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, removing stop words."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOP_WORDS]


# ---------------------------------------------------------------------------
# Pre-compute document token frequencies and IDF values.
# This is a simplified TF-IDF: we compute term frequency per document and
# inverse document frequency across the corpus.
# ---------------------------------------------------------------------------

def _compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency for a list of tokens."""
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    total = len(tokens) if tokens else 1
    return {token: count / total for token, count in counts.items()}


# Tokenize all documents and compute TF for each
_doc_tokens: list[dict[str, float]] = []
_doc_freq: dict[str, int] = {}  # how many docs contain each term

for doc in _documents:
    # Combine title and content for search (title terms get extra weight)
    text = f"{doc.get('title', '')} {doc.get('title', '')} {doc.get('content', '')}"
    tokens = _tokenize(text)
    tf = _compute_tf(tokens)
    _doc_tokens.append(tf)

    # Track document frequency for IDF calculation
    for term in tf:
        _doc_freq[term] = _doc_freq.get(term, 0) + 1

# Compute IDF: log(total_docs / docs_containing_term)
_num_docs = len(_documents) if _documents else 1
_idf: dict[str, float] = {
    term: math.log(_num_docs / freq)
    for term, freq in _doc_freq.items()
}


def search_documents(query: str, max_results: int = 5) -> list[dict]:
    """Search the document corpus using TF-IDF keyword matching.

    Tokenizes the query, computes TF-IDF similarity against each document,
    and returns the top results sorted by score.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.

    Returns:
        A list of dicts, each containing:
          - title: document title
          - content: truncated document content (first 300 chars)
          - score: relevance score (higher is better)
          - article_id: the document's ID
    """
    if not _documents:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # Score each document by summing TF-IDF for matching query terms.
    # This is a simplified cosine-like similarity — good enough for a demo.
    scored: list[tuple[float, int]] = []

    for idx, doc_tf in enumerate(_doc_tokens):
        score = 0.0
        for token in query_tokens:
            if token in doc_tf:
                # TF from document * IDF from corpus
                score += doc_tf[token] * _idf.get(token, 0.0)
        if score > 0:
            scored.append((score, idx))

    # Sort by score descending, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max_results]

    # Build result dicts
    results = []
    for score, idx in top:
        doc = _documents[idx]
        content = doc.get("content", "")
        results.append({
            "title": doc.get("title", ""),
            "content": content[:300] + ("..." if len(content) > 300 else ""),
            "score": round(score, 4),
            "article_id": doc.get("id", ""),
        })

    return results
