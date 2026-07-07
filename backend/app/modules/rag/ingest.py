"""
Knowledge base ingestion — reads docs/kb/*.md, chunks by heading,
embeds, and stores in MongoDB kb_chunks collection.

Run once at build/deploy time, or on startup if collection is empty.
Idempotent: clears and rebuilds the collection on each run.
"""

import re
from pathlib import Path

from app.core.logging import get_logger
from app.db.mongo.client import get_mongo_db
from app.modules.rag.embedder import embed_batch

logger = get_logger(__name__)

COLLECTION = "kb_chunks"
KB_DIR = Path(__file__).resolve().parents[4] / "docs" / "kb"

# Target chunk size in characters (~200-400 tokens ≈ 800-1600 chars)
MIN_CHUNK_CHARS = 100
MAX_CHUNK_CHARS = 1600


def _read_kb_files() -> list[dict]:
    """Read all .md files from the KB directory."""
    files = []
    if not KB_DIR.exists():
        logger.warning("kb_dir_not_found", path=str(KB_DIR))
        return files

    for md_file in sorted(KB_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        source_doc = md_file.stem  # e.g. "faq", "privacy_policy"
        files.append({"source_doc": source_doc, "content": content})

    logger.info("kb_files_read", count=len(files))
    return files


def _chunk_by_heading(content: str, source_doc: str) -> list[dict]:
    """
    Split markdown content into chunks by heading (## or ###).
    Each chunk includes the heading as context.
    """
    # Split on ## or ### headings
    sections = re.split(r'\n(?=#{2,3}\s)', content)
    chunks = []

    for i, section in enumerate(sections):
        text = section.strip()
        if not text or len(text) < MIN_CHUNK_CHARS:
            # Merge very short sections with the next one if possible
            if chunks and len(chunks[-1]["text"]) < MAX_CHUNK_CHARS:
                chunks[-1]["text"] += "\n\n" + text
                continue

        # Split further if section is too long
        if len(text) > MAX_CHUNK_CHARS:
            paragraphs = text.split("\n\n")
            current = ""
            for para in paragraphs:
                if len(current) + len(para) > MAX_CHUNK_CHARS and current:
                    chunks.append({
                        "source_doc": source_doc,
                        "text": current.strip(),
                        "chunk_index": len(chunks),
                    })
                    current = para
                else:
                    current += "\n\n" + para if current else para
            if current.strip():
                chunks.append({
                    "source_doc": source_doc,
                    "text": current.strip(),
                    "chunk_index": len(chunks),
                })
        else:
            chunks.append({
                "source_doc": source_doc,
                "text": text,
                "chunk_index": len(chunks),
            })

    return chunks


async def ingest_knowledge_base() -> int:
    """
    Full ingestion pipeline:
      1. Read all KB markdown files
      2. Chunk by heading
      3. Embed all chunks
      4. Clear and rebuild the Mongo collection

    Returns the number of chunks ingested.
    Idempotent: safe to re-run (drops and rebuilds).
    """
    files = _read_kb_files()
    if not files:
        logger.warning("kb_no_files_to_ingest")
        return 0

    # Chunk all files
    all_chunks = []
    for f in files:
        chunks = _chunk_by_heading(f["content"], f["source_doc"])
        all_chunks.extend(chunks)

    if not all_chunks:
        return 0

    # Embed all chunks
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_batch(texts)

    # Build Mongo documents
    docs = []
    for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
        docs.append({
            "_id": f"{chunk['source_doc']}_{chunk['chunk_index']}",
            "source_doc": chunk["source_doc"],
            "text": chunk["text"],
            "embedding": embedding,
            "chunk_index": chunk["chunk_index"],
        })

    # Clear and rebuild (idempotent)
    db = get_mongo_db()
    await db[COLLECTION].drop()
    if docs:
        await db[COLLECTION].insert_many(docs)

    logger.info("kb_ingestion_complete", chunks=len(docs))
    return len(docs)


async def ensure_kb_indexed() -> None:
    """Check if KB is indexed; if empty, run ingestion."""
    db = get_mongo_db()
    count = await db[COLLECTION].count_documents({})
    if count == 0:
        logger.info("kb_empty_triggering_ingestion")
        await ingest_knowledge_base()
