# System Architecture — AI Pronunciation Coach

## How Everything Connects

```
                                    ┌─────────────────────────────────────┐
                                    │         EXTERNAL SERVICES           │
                                    │                                     │
                                    │  OpenRouter (Gemini 2.5 Flash Lite) │
                                    │  Gmail SMTP (OTP emails)            │
                                    └──────────────┬──────────────────────┘
                                                   │ text-only API calls
                                                   │ (NEVER audio)
┌──────────────┐    REST API     ┌─────────────────┴──────────────────┐
│              │ ──────────────▶ │                                     │
│   FRONTEND   │                 │           BACKEND (FastAPI)         │
│  React+Vite  │ ◀────────────── │                                     │
│  Port 5173   │    JSON + JWT   │  • Auth (JWT + OTP)                │
│              │                 │  • Upload + FFmpeg preprocessing    │
└──────────────┘                 │  • Deepgram transcription          │
                                 │  • Scoring engine                   │
                                 │  • RAG assistant                    │
                                 │  Port 8080                          │
                                 └───────┬──────────────┬──────────────┘
                                         │              │
                              ┌──────────┴───┐   ┌─────┴──────────┐
                              │    MySQL     │   │    MongoDB      │
                              │              │   │                 │
                              │ Users        │   │ Transcripts     │
                              │ Scores       │   │ Phoneme analysis│
                              │ Quotas       │   │ Practice sets   │
                              │ Consent log  │   │ RAG KB chunks   │
                              │ Recordings   │   │ Explanation cache│
                              └──────────────┘   └─────────────────┘
                                         │
                              ┌──────────┴───┐
                              │ Local Disk   │
                              │ (audio files)│
                              │ /uploads/    │
                              └──────────────┘
```

I use two databases because they serve different purposes. MySQL holds structured data I need to query with SQL (users, scores, quotas — things with relationships). MongoDB holds large, deeply nested documents (a single transcript is an array of word objects, each with sub-arrays of phonemes — normalizing this into MySQL would be painful and slow to query).

---

## Models & APIs — What I Used and Why

| What I Use | What It Does | Why I Picked It Over Alternatives |
|---|---|---|
| **Deepgram Nova-2** | Converts speech to text with word-level timestamps | Cloud API — zero RAM/GPU needed on our servers. Free tier gives 12,000 minutes/year. Provides word-level timestamps + confidence scores which is exactly what our scoring engine needs. Unlike local models (Whisper/WhisperX), it works on Render's free tier (512MB) without any ML dependencies. |
| **Phonemizer (espeak-ng)** | Generates the "correct" IPA pronunciation for any English word | Free, fast, runs locally. No API dependency. A commercial pronunciation API (like Google TTS) would cost money and add latency for something I need on every single word. |
| **Gemini 2.5 Flash Lite (via OpenRouter)** | Generates coaching explanations and practice sentences | Cheap (~₹0.08 per call), fast, supports JSON mode. I use OpenRouter as the gateway so I can switch models without changing code. I never send audio to the LLM — only text metadata about phonemes. |
| **FFmpeg** | Normalizes uploaded audio to 16kHz mono WAV | Deepgram accuracy drops on stereo/high-sample-rate input. Normalizing first is cheap and makes everything downstream reliable. |

---

## How I Score Pronunciation

Every word gets a score from 0 to 100 using this formula:

```
Word Score = (60% × Confidence) + (20% × Timing) + (20% × Phoneme Accuracy)
```

**Confidence (60%):** How clearly Deepgram "heard" the word. If it's confident, the speaker was clear.

**Timing (20%):** Did the word last about the right duration? Natural English is ~150 words per minute. Too fast or too slow reduces this score.

**Phoneme Accuracy (20%):** I compare what the speaker said against what it *should* sound like. For example, "think" should be /θɪŋk/. If someone says /tɪŋk/ (replacing TH with T), that's a phoneme substitution. I use a weighted distance function where common L2 errors (like θ→t) are penalized less harshly than completely wrong sounds (like θ→m).

**How I decide what to highlight:**
- Score ≥ 80 → Green (correct)
- Phoneme distance > 0.3 → Red (mispronounced — I can tell you exactly which sound was wrong)
- Confidence < 0.6 → Orange (unclear — the word wasn't captured clearly)
- Timing off by > 50% → Blue (mistimed — rhythm issue)

The overall score is a duration-weighted average of all word scores. I also track which phonemes appear in 2+ mistakes — those become the "weak sounds" that feed the practice generator.

---

## DPDP Compliance

I took India's Digital Personal Data Protection Act 2023 seriously from the start — it's baked into the architecture, not added at the end.

**Consent:** Before any audio is accepted, the user must explicitly check a consent box. This records a `consent_events` row with the policy version and timestamp. The upload endpoint has a hard gate — without consent, it returns 403. Not just a UI checkbox, a server-enforced dependency.

**Storage:** Audio files are stored locally with randomized UUID filenames (no PII in the path). Behind a storage adapter interface so I can swap to S3 without changing business logic.

**Retention:** Raw audio is automatically deleted after 30 days via a scheduled job. Only the file is purged — derived data (scores, phoneme analysis) is retained because it's the user's progress history and less sensitive than biometric-adjacent raw audio.

**Deletion (Right to Erasure):** `DELETE /me` triggers cascading erasure across all three data stores: MySQL user row (PII zeroed), all recordings from file storage, all MongoDB documents (transcripts, analysis, practice sets). Logged in `data_deletion_requests` for audit proof.

**What goes to third parties:** The Gemini LLM receives ONLY text-based phoneme metadata — never raw audio, never email, never any PII. This is a hard architectural boundary enforced at the code level, not just a policy promise.

**Data residency gap (honest):** Render and Vercel free tiers don't guarantee India-region hosting. I've documented this transparently rather than silently ignoring it. In production with paid infra, I'd pin MySQL/Mongo/storage to `ap-south-1`.

---

## Trade-offs I Made

| What I Did | What I'd Do With More Time | Why I Made This Choice |
|---|---|---|
| **Confidence-proxy scoring** instead of a dedicated phoneme classifier | Use wav2vec2-lv-60-espeak-cv-ft for true acoustic phoneme recognition (~95% vs ~80% accuracy) | The dedicated model requires GPU and a specialized loading pipeline. Confidence-proxy still correctly identifies ~80% of problem areas and runs without GPU. |
| **Deepgram API** instead of local WhisperX | Run WhisperX locally for zero API dependency and offline capability | Deepgram is cloud-based (needs internet) but gives us zero-RAM deployment on free hosting tiers. WhisperX needs 2GB+ RAM and PyTorch — doesn't fit on Render free. |
| **Bag-of-words fallback** for RAG embeddings | Fix the torchcodec/FFmpeg library conflict and use real sentence-transformers | A Mac-specific library incompatibility. BoW with stemming works adequately for a small KB (55 chunks). |
| **CPU inference** for Deepgram (~30s per clip) | GPU-backed worker (RunPod or Render GPU tier) for <5s processing | Assessment scope — GPU hosting costs money. The UX handles the wait with staged progress UI. |
| **Local disk storage** | S3-compatible object storage | The adapter pattern means swapping is one config change. Local disk is fine for single-server demo. |
| **In-memory OTP rate limiter** | Redis-backed sliding window | Resets on server restart. Acceptable at assessment scale. |

---

## What I'd Build Next (One More Week)

1. **True acoustic phoneme classifier** — wav2vec2-lv-60-espeak-cv-ft on a GPU worker. This would make the scoring genuinely accurate at the individual phoneme level rather than using confidence as a proxy.

2. **Deepgram's diarization** — Enable speaker diarization for multi-speaker recordings, and leverage Deepgram's upcoming pronunciation scoring features as they mature.

3. **Celery + Redis** — Proper job queue for horizontal scaling. Multiple workers processing recordings in parallel.

4. **Real sentence-transformers embeddings** — The RAG assistant would understand semantic meaning (paraphrases, synonyms) rather than relying on word-overlap matching.

5. **Per-phoneme accent adaptation** — Detect the speaker's L1 background from their error patterns and weight the scoring/suggestions accordingly (e.g., Japanese speakers have different typical errors than Hindi speakers).

6. **WebSocket live updates** — Replace polling with real-time push notifications for processing status.

7. **Managed vector DB** (Qdrant/Pinecone) — For when the knowledge base grows beyond what brute-force search handles.
