from __future__ import annotations

from typing import Any
import faiss
import numpy as np


def build_faiss_index(embeddings: np.ndarray, chunk_records: list[dict]) -> dict[str, Any]:
    if embeddings.ndim != 2:
        raise ValueError("embeddings는 2차원 배열이어야 합니다.")

    if len(embeddings) != len(chunk_records):
        raise ValueError("임베딩 개수와 chunk_records 개수가 일치해야 합니다.")

    if len(chunk_records) == 0:
        raise ValueError("인덱싱할 청크가 없습니다.")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    return {
        "index": index,
        "embeddings": embeddings,
        "chunk_records": chunk_records,
        "dimension": dim,
        "corpus_size": len(chunk_records),
    }


def search_faiss(
    *,
    query_vector: np.ndarray,
    index_bundle: dict[str, Any],
    top_k: int = 5,
) -> list[dict]:
    if query_vector.ndim != 2:
        raise ValueError("query_vector는 shape=(1, dim) 형태여야 합니다.")

    index = index_bundle["index"]
    chunk_records = index_bundle["chunk_records"]

    scores, indices = index.search(query_vector, top_k)

    results: list[dict] = []
    top_scores = scores[0]
    top_indices = indices[0]

    max_score = float(top_scores[0]) if len(top_scores) > 0 else 0.0

    for rank, (score, idx) in enumerate(zip(top_scores, top_indices), start=1):
        if idx < 0:
            continue

        chunk = chunk_records[int(idx)]

        relative_score = 0.0
        if max_score > 0:
            relative_score = (float(score) / max_score) * 100.0

        results.append(
            {
                "rank": rank,
                "raw_score": round(float(score), 6),
                "relative_score": round(relative_score, 2),
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