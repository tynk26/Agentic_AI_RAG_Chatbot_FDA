from __future__ import annotations

from typing import Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def build_search_text(chunk: dict) -> str:
    """
    검색 품질을 조금 높이기 위해
    문서 제목 + 섹션 제목 + 청크 본문을 함께 검색 텍스트로 사용한다.
    """
    document_title = chunk.get("document_title", "")
    section_title = chunk.get("section_title", "")
    chunk_text = chunk.get("chunk_text", "")

    return f"{document_title}\n{section_title}\n{chunk_text}".strip()


def build_tfidf_index(chunk_records: list[dict]) -> dict[str, Any]:
    """
    청크 목록을 받아 TF-IDF 벡터 인덱스를 생성한다.
    """
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


def search_tfidf(
    *,
    query: str,
    index_bundle: dict[str, Any],
    top_k: int = 5,
) -> list[dict]:
    """
    TF-IDF 유사도 검색.
    결과는 점수 내림차순으로 반환.
    """
    query = query.strip()
    if not query:
        return []

    vectorizer = index_bundle["vectorizer"]
    matrix = index_bundle["matrix"]
    chunk_records = index_bundle["chunk_records"]

    query_vector = vectorizer.transform([query])
    similarities = linear_kernel(query_vector, matrix).flatten()

    ranked_indices = similarities.argsort()[::-1]

    results: list[dict] = []
    for idx in ranked_indices[:top_k]:
        score = float(similarities[idx])
        chunk = chunk_records[idx]

        results.append(
            {
                "rank": len(results) + 1,
                "score": round(score, 6),
                "document_title": chunk["document_title"],
                "section_title": chunk["section_title"],
                "chunk_index": chunk["chunk_index"],
                "chunk_length": chunk["chunk_length"],
                "inner_zip_name": chunk["inner_zip_name"],
                "xml_name": chunk["xml_name"],
                "chunk_text": chunk["chunk_text"],
            }
        )

    return results