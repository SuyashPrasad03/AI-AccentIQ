# AccentIQ Architecture v2 — Full Pipeline

## System Overview

AccentIQ is an AI pronunciation coaching platform that scores English pronunciation using acoustic phoneme analysis, classifies error types, and generates evidence-grounded feedback with L1-adaptive explanations.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React)                               │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ Upload/  │  │ Live Stream  │  │  Practice   │  │  Admin         │  │
│  │ Record   │  │ (WebSocket)  │  │  Plan View  │  │  Dashboard     │  │
│  └────┬─────┘  └──────┬───────┘  └──────┬──────┘  └───────┬────────┘  │
└───────┼────────────────┼─────────────────┼─────────────────┼───────────┘
        │                │                 │                  │
        ▼                ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                                  │
│                                                                          │
│  ┌─────────────────────── SCORING PIPELINE ──────────────────────────┐  │
│  │                                                                    │  │
│  │  Audio → WhisperX ASR → Word timestamps + confidence               │  │
│  │           │                                                        │  │
│  │           ▼                                                        │  │
│  │  Audio → wav2vec2-CTC → Frame-level log-posteriors                 │  │
│  │           │                                                        │  │
│  │           ▼                                                        │  │
│  │  GOP Engine: per-phoneme log P(expected | frames)                  │  │
│  │           │                                                        │  │
│  │           ▼                                                        │  │
│  │  Score Normalizer: raw GOP → 0-100 (calibrated bounds)             │  │
│  │           │                                                        │  │
│  │           ▼                                                        │  │
│  │  Error Classifier (LightGBM): substitution/deletion/distortion     │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─────────────────────── FEEDBACK PIPELINE ─────────────────────────┐  │
│  │                                                                    │  │
│  │  Evidence Builder → Structured acoustic evidence payload           │  │
│  │           │                                                        │  │
│  │           ▼                                                        │  │
│  │  L1 Transfer Patterns → Accent-aware context (5 languages)         │  │
│  │           │                                                        │  │
│  │           ▼                                                        │  │
│  │  LLM (Gemini via OpenRouter) → Evidence-grounded explanation       │  │
│  │           │                                                        │  │
│  │           ▼                                                        │  │
│  │  Feedback Verifier → Reject ungrounded claims (max 2 retries)      │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──── STREAMING ────┐  ┌──── PLANNER ────┐  ┌──── OBSERVABILITY ───┐  │
│  │ WebSocket endpoint │  │ Error History   │  │ Pipeline metrics     │  │
│  │ Rolling buffer     │  │ Aggregator      │  │ Per-stage latency    │  │
│  │ Incremental GOP    │  │ Practice Agent  │  │ Cost tracking        │  │
│  │ Word-by-word       │  │ 7-day plans     │  │ Quality drift        │  │
│  └────────────────────┘  └─────────────────┘  └──────────────────────┘  │
│                                                                          │
│  ┌──── RAG ASSISTANT ─┐                                                 │
│  │ Phonetics KB (10)  │                                                 │
│  │ Contextual trigger │                                                 │
│  │ Answer verifier    │                                                 │
│  └────────────────────┘                                                 │
└─────────────────────────────────────────────────────────────────────────┘
        │                │                 │
        ▼                ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  MySQL       │  │  MongoDB     │  │  File Store  │
│  Users       │  │  Analyses    │  │  Audio WAVs  │
│  Scores      │  │  Transcripts │  │              │
│  Phonemes    │  │  KB chunks   │  │              │
│  Plans       │  │  Metrics     │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Phoneme scoring | GOP via wav2vec2-CTC | Standard in speech assessment literature; measures acoustic quality, not just ASR confidence |
| Error classifier | LightGBM | Tabular features, trains in seconds, interpretable, defensible for interview |
| Feedback verification | Rule-based regex | Deterministic, fast, no extra LLM cost — checks phoneme references against measured data |
| Streaming | WebSocket + rolling buffer | Real-time UX without changing the batch pipeline's core logic |
| Practice planning | Custom state machine | Simpler than LangGraph for a single-purpose agent; reads error history, produces structured plan |
| Observability | MongoDB metrics + custom dashboard | Appropriate for portfolio project scope; documents the trade-off vs. Prometheus |
| L1 adaptation | Curated lookup table | Linguistics knowledge is finite and well-documented; no ML needed for 18 patterns |

## Data Flow: Recording → Score → Feedback

1. **Upload**: Audio file → FFmpeg normalization → local storage → MySQL recording record
2. **Transcription**: WhisperX/Deepgram → word-level timestamps + confidence → MongoDB transcript
3. **GOP Scoring**: wav2vec2-CTC frame posteriors → per-phoneme GOP → normalized 0-100 scores
4. **Error Classification**: Acoustic features → LightGBM → substitution/deletion/distortion labels
5. **Feedback**: Evidence builder → LLM prompt with acoustic data + L1 context → verifier → user

## Models in Use

| Model | Purpose | Loaded |
|-------|---------|--------|
| facebook/wav2vec2-lv-60-espeak-cv-ft | Phoneme-level acoustic posteriors | Once at startup (warm) |
| WhisperX (small) / Deepgram Nova-2 | Word-level ASR + timestamps | Per-request |
| LightGBM error_classifier_v1 | Error type classification | Once at first inference |
| sentence-transformers/all-MiniLM-L6-v2 | RAG embeddings | Once at startup |
| Google Gemini (via OpenRouter) | Feedback generation, practice sentences | Per-request (API call) |

## Feature Flags

| Flag | Values | Effect |
|------|--------|--------|
| `SCORING_ENGINE` | `gop` / `legacy` | Switches active scoring engine (both always log for comparison) |

---

*Architecture v2 — Phases 24–32 | Last updated: 2026-07-31*
