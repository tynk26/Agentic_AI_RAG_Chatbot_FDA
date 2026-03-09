from __future__ import annotations

from typing import Sequence
import numpy as np
from sentence_transformers import SentenceTransformer


_MODEL = None


def get_embedding_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _MODEL


def embed_texts(texts: Sequence[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 384), dtype="float32")

    model = get_embedding_model()
    embeddings = model.encode(
        list(texts),
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.astype("float32")


def embed_query(query: str) -> np.ndarray:
    model = get_embedding_model()
    vector = model.encode(
        [query],
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return vector.astype("float32")