"""
Vector search over kb_chunks in MongoDB.

Retrieves top-k chunks by cosine similarity against the query embedding.
Uses brute-force search over Mongo-stored embeddings (fine for small KB).
Production upgrade: MongoDB Atlas Vector Search or FAISS.
"""

from app.core.logging import get_logger
from app.core.settings import settings
from app.db.mongo.client import get_mongo_db
from app.modules.rag.embedder import cosine_similarity, embed_text

logger = get_logger(__name__)

COLLECTION = "kb_chunks"


async def search_similar(query: str, top_k: int | None = None) -> list[dict]:
    """
    Search for the top-k most similar chunks to the query.

    Returns list of {text, source_doc, score} sorted by similarity (descending).
    """
    if top_k is None:
        top_k = settings.rag_top_k

    # Embed the query
    query_embedding = embed_text(query)

    # Fetch all chunks (small KB — brute force is fine)
    db = get_mongo_db()
    cursor = db[COLLECTION].find({}, {"text": 1, "source_doc": 1, "embedding": 1})

    results = []
    async for doc in cursor:
        score = cosine_similarity(query_embedding, doc.get("embedding", []))
        results.append({
            "text": doc["text"],
            "source_doc": doc["source_doc"],
            "score": score,
        })

    # Sort by score descending, take top-k
    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:top_k]

    logger.info(
        "vector_search",
        query_preview=query[:50],
        top_score=top_results[0]["score"] if top_results else 0.0,
        results_count=len(top_results),
    )
    return top_results
