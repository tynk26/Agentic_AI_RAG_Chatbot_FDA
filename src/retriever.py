from __future__ import annotations

import re
from typing import Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


QUERY_EXPANSION_MAP = {
    "interactions": ["drug interactions", "interaction", "concomitant use"],
    "drug interaction": ["drug interactions", "interaction"],
    "side effects": ["adverse reactions", "adverse reaction"],
    "warning": ["warnings and precautions", "precautions"],
    "warnings": ["warnings and precautions", "precautions"],
    "dosage": ["dosage and administration", "dose"],
    "contraindication": ["contraindications"],
    "contraindications": ["contraindications"],
    "pregnancy": ["use in specific populations", "pregnancy"],
    "lactation": ["use in specific populations", "nursing mothers"],
    "overdose": ["overdosage"],
}


def normalize_query(query: str) -> str:
    query = query.strip().lower()
    query = re.sub(r"\s+", " ", query)
    return query


def expand_query(query: str) -> str:
    normalized = normalize_query(query)
    expanded_terms = [normalized]

    for key, values in QUERY_EXPANSION_MAP.items():
        if key in normalized:
            expanded_terms.extend(values)

    if "aspirin" in normalized:
        expanded_terms.extend(["aspirin hypersensitivity", "nsaid", "salicylate"])

    if "warfarin" in normalized:
        expanded_terms.extend(["anticoagulant", "bleeding", "drug interactions"])

    deduped = []
    seen = set()
    for term in expanded_terms:
        cleaned = term.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)

    return " ".join(deduped)


def tokenize_for_highlight(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9\-]+", text.lower())
    return [tok for tok in tokens if len(tok) >= 3]


def build_search_text(chunk: dict) -> str:
    """
    검색 품질 향상을 위해 section title을 반복해 boost를 준다.
    """
    document_title = chunk.get("document_title", "")
    section_title = chunk.get("section_title", "")
    chunk_text = chunk.get("chunk_text", "")

    boosted_text = "\n".join(
        [
            document_title,
            section_title,
            section_title,
            section_title,
            chunk_text,
        ]
    ).strip()

    return boosted_text


def build_tfidf_index(chunk_records: list[dict]) -> dict[str, Any]:
    if not chunk_records:
        raise ValueError("인덱싱할 청크가 없습니다.")

    corpus = [build_search_text(chunk) for chunk in chunk_records]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words=None,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )

    matrix = vectorizer.fit_transform(corpus)

    return {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "chunk_records": chunk_records,
        "corpus_size": len(corpus),
    }


def highlight_text(text: str, query: str) -> str:
    """
    질의 토큰을 <mark>로 감싼 HTML 문자열 반환
    """
    tokens = tokenize_for_highlight(expand_query(query))
    if not tokens:
        return text

    # 긴 토큰부터 치환
    tokens = sorted(set(tokens), key=len, reverse=True)
    highlighted = text

    for token in tokens:
        pattern = re.compile(rf"(?i)\b({re.escape(token)})\b")
        highlighted = pattern.sub(r"<mark>\1</mark>", highlighted)

    return highlighted


def search_tfidf(
    *,
    query: str,
    index_bundle: dict[str, Any],
    top_k: int = 5,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    expanded_query = expand_query(query)

    vectorizer = index_bundle["vectorizer"]
    matrix = index_bundle["matrix"]
    chunk_records = index_bundle["chunk_records"]

    query_vector = vectorizer.transform([expanded_query])
    similarities = linear_kernel(query_vector, matrix).flatten()

    ranked_indices = similarities.argsort()[::-1]
    top_scores = similarities[ranked_indices[:top_k]]

    max_score = float(top_scores[0]) if len(top_scores) > 0 else 0.0

    results: list[dict] = []
    for idx in ranked_indices[:top_k]:
        raw_score = float(similarities[idx])
        chunk = chunk_records[idx]

        relative_score = 0.0
        if max_score > 0:
            relative_score = (raw_score / max_score) * 100.0

        results.append(
            {
                "rank": len(results) + 1,
                "raw_score": round(raw_score, 6),
                "relative_score": round(relative_score, 2),
                "expanded_query": expanded_query,
                "document_title": chunk["document_title"],
                "section_title": chunk["section_title"],
                "chunk_index": chunk["chunk_index"],
                "chunk_length": chunk["chunk_length"],
                "inner_zip_name": chunk["inner_zip_name"],
                "xml_name": chunk["xml_name"],
                "chunk_text": chunk["chunk_text"],
                "highlighted_chunk_text": highlight_text(chunk["chunk_text"], query),
            }
        )

    return results