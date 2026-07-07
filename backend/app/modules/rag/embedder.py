"""
Embedding utility for RAG.

Uses sentence-transformers if available, falls back to a simple
TF-IDF-like bag-of-words cosine similarity for dev/CI environments
without the ML dependency.
"""

import hashlib
import math
from collections import Counter

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)

_model = None
_USE_TRANSFORMERS = False


def _load_model():
    """Lazy-load the embedding model."""
    global _model, _USE_TRANSFORMERS
    if _model is not None:
        return

    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model)
        _USE_TRANSFORMERS = True
        logger.info("embedder_loaded", model=settings.embedding_model)
    except ImportError:
        logger.warning(
            "sentence_transformers_not_installed",
            fallback="bag_of_words",
            info="Install sentence-transformers for production-quality embeddings.",
        )
        _model = "bow_fallback"
        _USE_TRANSFORMERS = False


def embed_text(text: str) -> list[float]:
    """
    Generate an embedding vector for the given text.
    Returns a list of floats (384-dim for MiniLM, variable for BoW fallback).
    """
    _load_model()

    if _USE_TRANSFORMERS:
        vector = _model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    # Fallback: deterministic 128-dim pseudo-embedding from BoW hash
    return _bow_embed(text)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts efficiently."""
    _load_model()

    if _USE_TRANSFORMERS:
        vectors = _model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [v.tolist() for v in vectors]

    return [_bow_embed(t) for t in texts]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        # Pad shorter vector with zeros
        max_len = max(len(a), len(b))
        a = a + [0.0] * (max_len - len(a))
        b = b + [0.0] * (max_len - len(b))

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _bow_embed(text: str, dim: int = 128) -> list[float]:
    """
    Fallback embedding: hash each word into a fixed-dim vector.
    Not semantically meaningful, but deterministic and allows
    the full pipeline to function without ML dependencies.
    """
    words = text.lower().split()
    vector = [0.0] * dim

    for word in words:
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % dim
        vector[idx] += 1.0

    # Normalize
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    return vector
