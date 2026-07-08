# Architecture Document — AI Pronunciation Coach

## Components & Connections

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│   MySQL      │
│ React + Vite │◀────│   FastAPI    │────▶│   MongoDB    │
│   (Vercel)   │     │   (Render)   │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                           │
                     ┌─────┴──────┐
                     │  WhisperX  │ (ASR + Forced Alignment)
                     │  FFmpeg    │ (Audio Preprocessing)
                     │ Phonemizer │ (IPA Reference)
                     │ OpenRouter │ (Gemini for Feedback)
                     └────────────┘
```

**Frontend → Backend**: REST API over HTTPS. JWT access tokens (15min) + httpOnly refresh cookies (7d). CORS locked to deployed frontend origin.

**Backend → MySQL**: User accounts, auth, quotas, scores (queryable summaries), recordings metadata. Async via aiomysql + SQLAlchemy 2.0.

**Backend → MongoDB**: Transcripts, phoneme analysis, practice sets, explanation cache, RAG knowledge base chunks. Async via Motor.

**Backend → WhisperX**: CPU inference for ASR + forced alignment. Background job (FastAPI BackgroundTasks). Model: `small` on CPU.

**Backend → OpenRouter/Gemini**: Text-only API calls for feedback generation, practice sentences, RAG synthesis. Never receives audio.

## Models & APIs — Why These Over Alternatives

| Choice | Why | Alternative Considered |
|---|---|---|
| **WhisperX** over plain Whisper | Forced alignment gives word-level timestamps — the feature that enables per-word mistake highlighting | Plain Whisper only gives segment timestamps |
| **Phonemizer (espeak-ng)** over a proprietary phoneme model | Free, fast, deterministic IPA output. No API dependency for reference phonemes | Proprietary pronunciation APIs (cost, latency) |
| **Gemini via OpenRouter** over direct Gemini API | Single API key for multiple models, JSON mode, easy model switching | Direct Google AI API (vendor lock-in) |
| **MySQL + MongoDB** dual-database | MySQL for structured/relational (users, scores, quotas), MongoDB for large nested documents (transcripts, phoneme arrays). Genuinely different data shapes. | Single Postgres with JSONB (viable but loses Mongo's schema flexibility) |
| **FastAPI** over Django/Express | Async-first (matches Motor + WhisperX pipeline), native Pydantic validation, auto-generated docs | Django (sync overhead), Express (weaker validation) |
| **Local disk + adapter pattern** over direct S3 | Assessment scope. `StorageBackend` ABC lets swap to S3 without touching service logic | Direct S3 (requires paid infra for demo) |

## Scoring Methodology

**Formula**: `word_score = 60% × confidence + 20% × timing + 20% × phoneme_accuracy`

- **Confidence**: ASR confidence (0-1) from WhisperX per word
- **Timing**: Deviation from expected ~150 WPM pace
- **Phoneme Accuracy**: Weighted Levenshtein distance over IPA sequences (phonetic-feature-weighted: θ→t costs 0.3, θ→m costs 0.6)

**Classification**: correct (≥80) | mispronounced (phoneme dist >0.3) | unclear (confidence <0.6) | mistimed (timing >50% off)

**Overall**: Duration-weighted average of word scores. Sub-scores: Accuracy (phoneme mean), Fluency (rate + pause penalty).

## DPDP Compliance

- **Consent before processing**: Required checkbox records `consent_events` with policy version + timestamp before any audio is accepted
- **Audio retention**: Auto-purged after 30 days via scheduled job. Derived data (scores) retained for progress
- **Right to erasure**: `DELETE /me` cascades across MySQL + MongoDB + file storage. Logged in `data_deletion_requests`
- **No audio to third parties**: Gemini/OpenRouter only receives text/phoneme metadata, never raw audio
- **Data residency**: Documented gap — Render/Vercel free tiers may not offer India region. Architecture doc is honest about this.

## Trade-offs Made

| Trade-off | Why | Upgrade Path |
|---|---|---|
| **Confidence-proxy scoring** vs. true acoustic phoneme classifier | A wav2vec2-based phoneme model would give ~95% accuracy vs ~80% with confidence-proxy. But requires GPU + specialized model loading. | wav2vec2-lv-60-espeak-cv-ft on GPU worker |
| **In-process BackgroundTasks** vs. Celery+Redis | Fine at assessment scale (<100 concurrent users). Not horizontally scalable. | Celery + Redis + dedicated worker fleet |
| **Brute-force vector search** vs. managed vector DB | KB is 55 chunks. Brute-force cosine is <10ms. | Qdrant/Pinecone/Atlas Vector Search at scale |
| **BoW fallback embeddings** vs. sentence-transformers | torchcodec FFmpeg library conflict on macOS. BoW works with stemming but less semantic. | Fix torch environment or use API-based embeddings |
| **CPU WhisperX** vs. GPU | ~30s per 30s clip on CPU. Fine for demo. | GPU-backed Render instance or RunPod |
| **In-memory OTP rate limiter** vs. Redis | Single-process. Resets on restart. | Redis sorted-set sliding window |

## What I'd Build Next (Another Week)

1. **Dedicated acoustic phoneme classifier** (wav2vec2-lv-60-espeak-cv-ft) for true phoneme-level detection instead of confidence-proxy
2. **GPU-backed WhisperX** for <5s processing latency
3. **Celery + Redis** for horizontal job scaling
4. **Real sentence-transformers embeddings** for the RAG assistant (fix torchcodec conflict)
5. **Per-phoneme accent adaptation** — detect L1 background and weight common L1→English error patterns
6. **Managed vector DB** (Qdrant) + real-time KB ingestion
7. **Websocket** for live processing updates instead of polling
