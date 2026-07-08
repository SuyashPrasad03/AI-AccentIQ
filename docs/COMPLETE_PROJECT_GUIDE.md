# AI AccentIQ — Complete Project Guide

> This document explains **every functionality** of the application: what it does, how it works internally, and why each design decision was made.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack & Why Each Choice](#2-tech-stack--why-each-choice)
3. [Authentication & Identity System](#3-authentication--identity-system)
4. [Audio Upload & Preprocessing](#4-audio-upload--preprocessing)
5. [Speech Recognition (Deepgram)](#5-speech-recognition-deepgram)
6. [Pronunciation Scoring Engine](#6-pronunciation-scoring-engine)
7. [AI Feedback — "Explain My Mistake"](#7-ai-feedback--explain-my-mistake)
8. [Personalized Practice Generator](#8-personalized-practice-generator)
9. [Progress Comparison & Analytics](#9-progress-comparison--analytics)
10. [RAG-Powered In-App Assistant](#10-rag-powered-in-app-assistant)
11. [DPDP Compliance & Data Lifecycle](#11-dpdp-compliance--data-lifecycle)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Database Design](#13-database-design)
14. [API Endpoints Reference](#14-api-endpoints-reference)
15. [How to Run Locally](#15-how-to-run-locally)

---

## 1. Project Overview

### What is this?
An AI-powered web application that evaluates English pronunciation. A user uploads or records audio, the system analyzes it using speech recognition and phoneme comparison, and returns:
- A pronunciation score (0-100)
- Word-by-word analysis with color-coded highlights
- AI-generated coaching explanations
- Personalized practice sentences
- Progress tracking over time

### Who is it for?
Non-native English speakers who want to improve their pronunciation with objective, data-driven feedback rather than subjective human assessment.

### Core User Journey
```
Record/Upload Audio → AI Processes → See Score → Click Word → Get AI Coaching → Practice → Track Progress
```

---

## 2. Tech Stack & Why Each Choice

### Backend: FastAPI (Python 3.11)
**What**: The web framework handling all API requests.
**Why FastAPI specifically**:
- **Async-first**: MongoDB (Motor), Deepgram, and HTTP calls to OpenRouter all benefit from async/await. Django is sync by default.
- **Pydantic native**: Every request/response is validated automatically via type hints. No separate serializer layer needed.
- **Auto-generated docs**: Swagger UI at `/docs` — evaluators can explore the API immediately.
- **Performance**: One of the fastest Python frameworks (comparable to Node.js for I/O workloads).

### Frontend: React + Vite
**What**: Single-page application with client-side routing.
**Why**:
- **React**: Component-based, huge ecosystem, everyone knows it.
- **Vite**: 10x faster dev server than Create React App. Hot module replacement in <100ms.
- **Plain JS** (not TypeScript): Faster to build for an assessment. Types add safety but also ceremony.
- **Redux Toolkit**: Predictable global state for auth + quota + complex flows.

### Relational DB: MySQL
**What**: Stores users, auth tokens, recordings metadata, scores, quotas, consent events.
**Why MySQL over Postgres**:
- The PRD specified MySQL. Both would work equally well here.
- Used with SQLAlchemy 2.0 (async via aiomysql) + Alembic for migrations.

### Document DB: MongoDB
**What**: Stores transcripts, phoneme analysis, practice sets, explanation cache, RAG knowledge base.
**Why a second database**:
- Transcripts and phoneme analysis are large, deeply nested JSON documents (arrays of word objects with sub-arrays of phonemes). Storing these in MySQL would require either a blob column (losing queryability) or a painful normalized schema.
- MongoDB's schema flexibility lets us evolve the document shape as the scoring algorithm improves without migration pain.
- Accessed via Motor (async driver matching FastAPI's async model).

### Speech Recognition: Deepgram
**What**: Converts audio to text with word-level timestamps.
**Why Deepgram over plain Whisper**:
- **Forced alignment**: Deepgram adds wav2vec2-based alignment giving precise start/end times for EACH WORD. Plain Whisper only gives approximate segment timestamps.
- This is critical because the scoring engine needs to know exactly where each word starts/ends to assess timing, identify pauses, and map mistakes to specific positions.
- Model: `small` (good accuracy/speed tradeoff on CPU, ~30s processing for 30s audio).

### Audio Preprocessing: FFmpeg
**What**: Normalizes uploaded audio to a consistent format before Deepgram processes it.
**How**: Converts any input (MP3, M4A, WebM, etc.) → 16kHz mono WAV (PCM s16le).
**Why**: Deepgram expects 16kHz mono input. Without normalization, accuracy drops significantly on stereo/high-sample-rate/compressed inputs.

### Phoneme Reference: Phonemizer (espeak-ng)
**What**: Converts English text to IPA (International Phonetic Alphabet) phonemes.
**Example**: "think" → /θɪŋk/
**Why**: We need to know what a word SHOULD sound like (reference phonemes) to compare against what was actually said. Phonemizer with espeak-ng is free, fast, deterministic, and produces standard IPA output.

### LLM: Gemini via OpenRouter
**What**: Generates human-friendly coaching explanations and practice sentences.
**Why OpenRouter** (not direct Gemini API):
- Single API key for multiple models. Can switch to GPT-4, Claude, etc. without code changes.
- JSON mode for structured output (feedback endpoint).
- Model: `gemini-2.5-flash-lite` — fast, cheap (~$0.001 per call), good enough for coaching text.

### Storage: Local Disk (with adapter pattern)
**What**: Audio files stored on the local filesystem in development.
**Why an adapter pattern**: A `StorageBackend` abstract class with `LocalDiskBackend` implementation. `S3Backend` can be swapped in by changing one config value — zero code changes in the service layer. This is explicitly for the assessment; production would use S3.

---

## 3. Authentication & Identity System

### How it works

The app supports two types of users:

#### Anonymous Users
- Get a **signed httpOnly cookie** (`anon_session_id`) on first visit
- Server maintains a MySQL row tracking their usage count
- Limited to 3 free analyses
- Cookie is HMAC-signed so it can't be trivially forged
- Secondary signal: SHA-256(IP + UserAgent) stored alongside — raises the bar for quota bypass without invasive fingerprinting

#### Registered Users
1. **Register**: Enter email → receive 6-digit OTP via email (10-minute expiry)
2. **Verify OTP + Set Password**: OTP is hashed (argon2) and single-use
3. **Login**: Email + password → JWT access token (15min) + httpOnly refresh token (7 days)
4. **Silent Refresh**: On page load, if refresh cookie exists, automatically get a new access token without re-login

### Why OTP over magic link?
- Better on mobile (no app-switching to click an email link)
- Easier to demo/test
- Rate-limited: 5 OTP requests per email per hour

### Security details
- Passwords: Argon2 hashed (memory-hard, resistant to GPU cracking)
- Access tokens: Short-lived (15min) JWT with HS256 signing
- Refresh tokens: Opaque 64-byte hex, SHA-256 hashed before storage, rotation on use
- All tokens have `httpOnly` cookies where applicable (XSS protection)

### The `get_current_identity()` dependency
This is the single most important FastAPI dependency in the whole app. Every endpoint that needs to know "who is asking" uses it. It resolves either:
- An authenticated User (from JWT in Authorization header), OR
- An anonymous session ID (from the signed cookie)

This uniform identity object is then passed to quota checking, consent checking, and recording ownership.

---

## 4. Audio Upload & Preprocessing

### Upload Pipeline (executed in order)

```
Gate 1: Consent Check → Does this user have audio_processing consent? (403 if not)
Gate 2: Quota Check   → Has the anon user exceeded 3 free analyses? (402 if yes)
Step 3: MIME Sniff     → python-magic reads file bytes, rejects non-audio (422)
Step 4: Size Check     → Reject > 50MB (422)
Step 5: Duration Check → ffprobe reads actual duration, reject > 45s (422)
Step 6: Normalize      → FFmpeg converts to 16kHz mono WAV
Step 7: Store          → Save via StorageBackend with UUID filename
Step 8: DB Record      → Insert recordings row (status: "uploaded")
Step 9: Increment Quota → Bump anonymous usage counter
Step 10: Trigger Job   → Fire background transcription task
```

### Why validate duration server-side?
Client-side checks are UX niceties (instant feedback), but a modified client could send anything. The server is the only security boundary. We use `ffprobe` because it reads the actual audio container metadata, not trusting the Content-Length header.

### Why UUID filenames?
- Prevents path traversal attacks (user can't name a file `../../etc/passwd`)
- Maps cleanly to DPDP "deletable by ID" requirement
- No PII in the filename

---

## 5. Speech Recognition (Deepgram)

### What happens in the transcription job

```python
# 1. Load Deepgram model (cached after first call)
model = deepgram.load_model("small", device="cpu")

# 2. Transcribe
audio = deepgram.load_audio(audio_path)
result = model.transcribe(audio)
# Result: segments with approximate timestamps

# 3. Forced alignment
align_model = deepgram.load_align_model(language_code="en")
aligned = deepgram.align(result["segments"], align_model, audio)
# Result: WORD-LEVEL timestamps and confidence scores
```

### Output stored in MongoDB `transcripts` collection:
```json
{
  "_id": "uuid",
  "recording_id": "mysql-recording-id",
  "raw_text": "hello what up",
  "words": [
    {"word": "hello", "start": 0.42, "end": 0.71, "confidence": 0.91},
    {"word": "what", "start": 0.85, "end": 1.12, "confidence": 0.55},
    {"word": "up", "start": 1.20, "end": 1.45, "confidence": 0.94}
  ],
  "language": "en",
  "model_version": "deepgram-small-en"
}
```

### Why background job, not synchronous?
Deepgram on CPU takes 15-30 seconds. Blocking the HTTP response that long is terrible UX. Instead:
- Upload returns immediately (201) with a recording ID
- Frontend polls `GET /recordings/{id}/status` every 2.5 seconds
- Backend flips status: `uploaded → processing → transcribed → scored`
- Frontend shows staged progress UI

### Mock fallback
When Deepgram isn't installed (CI, lightweight dev), a mock returns plausible fake transcripts with varied confidence. This lets the full pipeline work end-to-end without the ~3GB ML dependency.

---

## 6. Pronunciation Scoring Engine

### The Scoring Formula (fully transparent, documented)

```
word_score = 60% × confidence_component + 20% × timing_component + 20% × phoneme_component
```

#### Component 1: Confidence (60% weight)
- Source: Deepgram's per-word confidence (0.0 to 1.0)
- Logic: `confidence × 100` → maps to 0-100
- Why 60%: ASR confidence is the strongest single signal for whether a word was pronounced clearly

#### Component 2: Timing (20% weight)
- Expected word duration: ~0.4 seconds (based on 150 WPM natural English)
- Penalty: deviation from expected duration (max 50 points penalty)
- Logic: `100 - min(deviation_ratio × 50, 50)`
- Why: Words spoken too fast or held too long indicate rhythm issues

#### Component 3: Phoneme Accuracy (20% weight)
- Reference: Phonemizer generates expected IPA for the word
- Comparison: Weighted Levenshtein distance over IPA sequences
- Key insight: Not all substitutions are equal. θ→t (0.3 severity — very common L2 error) vs θ→m (0.6 severity — completely wrong sound)
- Logic: `(1 - phoneme_distance) × 100`

### Mistake Classification (mutually exclusive per word)
| Classification | Trigger | Color |
|---|---|---|
| **correct** | word_score ≥ 80 | Green |
| **mispronounced** | phoneme_distance > 0.3 | Red |
| **unclear** | confidence < 0.6 | Orange/Amber |
| **mistimed** | timing deviation > 50% | Blue/Purple |

### Overall Score
Duration-weighted average of all word scores. Longer words contribute more (they carry more acoustic information).

### Sub-scores
- **Accuracy**: Mean of phoneme_component across all words
- **Fluency**: 100 - (rate_penalty + pause_penalty)
  - rate_penalty: deviation from 150 WPM
  - pause_penalty: ratio of silence to total duration

### Weak Phonemes
Any IPA phoneme that appears in 2+ mispronounced words → added to `weak_phonemes[]`. This directly feeds the Practice Generator.

### Where results are stored
- **MySQL `scores` table**: Overall/accuracy/fluency (queryable for progress charts)
- **MySQL `phoneme_scores` table**: Per-phoneme accuracy per recording (for comparisons)
- **MongoDB `phoneme_analysis`**: Full word-by-word breakdown (large, nested)

### Trade-off documented
This uses confidence as a PROXY for acoustic quality. A real acoustic phoneme classifier (wav2vec2-lv-60-espeak-cv-ft) would be ~95% accurate vs ~80% with the confidence proxy. Flagged as the "next week" upgrade.

---

## 7. AI Feedback — "Explain My Mistake"

### How it works

When a user clicks a highlighted (non-green) word in the transcript:

```
1. Frontend: GET /recordings/{id}/words/{index}/explain
2. Backend builds a cache key: "think|mispronounced|t,ɪ,ŋ,k"
3. Check MongoDB cache → if hit, return instantly (~5ms)
4. If miss: call Gemini with a structured prompt containing ONLY:
   - The word
   - The mistake type
   - Expected phonemes
   - Detected phonemes
   (NEVER audio, NEVER user email — only linguistic metadata)
5. Gemini returns JSON: {explanation, mouth_position_tip, practice_words}
6. Cache write-through to MongoDB
7. Return to frontend
```

### Why on-demand (not pre-generated)?
- Most users won't click every mistake
- Saves ~90% of LLM costs
- Keeps the initial results screen fast (no waiting for 15 LLM calls)

### Why cache by pattern?
The SAME mistake pattern ("TH replaced by T in any word") recurs across thousands of users. One LLM call serves everyone who makes that error. Cache key: `word|issue|substitution_pattern`.

### Fallback
If OpenRouter is down/rate-limited, a static template provides generic but useful advice per issue type. The user NEVER sees a raw error — they always get coaching content.

---

## 8. Personalized Practice Generator

### How it works

```
1. GET /practice/today
2. Aggregate weak phonemes from user's last 5 recordings (frequency-weighted)
   - Anonymous: single-recording only (natural signup incentive)
3. Check if today's practice set is cached (MongoDB, keyed by user+date)
4. If not cached: call Gemini to generate sentences targeting those phonemes
5. Validation pass: re-run Phonemizer on generated sentences to confirm
   they actually CONTAIN the target sounds (prevents irrelevant sentences)
6. If validation fails: retry up to 2 times, then use static fallback
7. Cache result for the day (stable across page reloads)
```

### Why validate LLM output?
LLMs sometimes generate sentences that sound relevant but don't actually contain the target phoneme. "Practice TH sound" → generates "The cat sat on a mat" (only has /ð/, not /θ/). Phonemic validation catches this.

### Why cache by day?
- Gives a sense of structured curriculum ("Today's Practice")
- Prevents random noise on every refresh
- User can explicitly click "Regenerate" for new sentences

---

## 9. Progress Comparison & Analytics

### How it works

- **Comparison**: Every new recording is compared against the IMMEDIATELY PRIOR one (N vs N-1)
- **Deltas shown**: Overall (+8), Accuracy (+10), Fluency (-3), per-phoneme (θ: 61→88)
- **Only common phonemes**: If a phoneme wasn't in both recordings, it's excluded (no fabricated 0→X)
- **First recording**: Gracefully shows "Upload another to see progress" (not an error)

### Why N vs N-1 (not vs. average)?
The spec explicitly shows "before → after" — most legible for a learner. "Today vs. last time" is more motivating than "today vs. your historical average."

### Data source
- `scores` table (MySQL) for overall/fluency/accuracy
- `phoneme_scores` table (MySQL) for per-phoneme accuracy
- Populated at scoring time — no real-time recalculation needed

---

## 10. RAG-Powered In-App Assistant

### How it works

```
User asks: "How is my score calculated?"
       ↓
1. Embed the question (BoW hash fallback or sentence-transformers)
2. Search MongoDB kb_chunks for top-15 similar chunks
3. Pass context to Gemini with grounding prompt:
   "Answer ONLY from context. If not covered, refuse."
4. Gemini synthesizes a natural answer
5. Check for refusal indicators in the response
6. Return {answer, sources, refused}
```

### Knowledge Base
6 versioned Markdown files in `docs/kb/`:
- `faq.md` — Usage questions
- `privacy_policy.md` — DPDP compliance details
- `scoring_methodology.md` — Formula, weights, thresholds
- `user_guide.md` — How to use features
- `troubleshooting.md` — Common issues + fixes
- `api_docs.md` — All endpoints documented

### Ingestion
On app startup (if collection is empty):
1. Read all .md files
2. Split by heading (semantic chunks, 200-400 tokens each)
3. Embed each chunk
4. Store in MongoDB `kb_chunks` collection

### Refusal Logic (the key requirement)
- **Hard backstop**: Similarity threshold (with real embeddings)
- **LLM grounding**: System prompt instructs "refuse if context doesn't cover it"
- **Result**: "What's the capital of France?" → refused. "How is scoring done?" → answered.

### Why NOT LangChain?
Hand-rolled pipeline gives full control over refusal logic. LangChain adds framework overhead and makes the refusal boundary harder to reason about for a small, scoped implementation.

---

## 11. DPDP Compliance & Data Lifecycle

### What is DPDP?
India's Digital Personal Data Protection Act 2023. Requires:
- Explicit consent before processing personal data
- Right to access what's stored
- Right to erasure
- Data minimization

### How we implement it

| Requirement | Implementation |
|---|---|
| **Consent before processing** | Required checkbox + `consent_events` table (type, policy_version, timestamp). Upload endpoint has a dependency guard that returns 403 without consent. |
| **Right to access** | `GET /me/data-summary` — recordings count, consent events, retention dates |
| **Right to erasure** | `DELETE /me` — cascading deletion across MySQL + MongoDB + file storage + token revocation. Logged in `data_deletion_requests` for audit. |
| **Data retention** | Audio auto-deleted after 30 days via scheduled job. Derived data (scores) retained for progress. |
| **Audio handling minimization** | Raw audio is NEVER sent to any LLM. Only text/phoneme metadata goes to Gemini. Hard architectural boundary. |
| **Audit trail** | `consent_events` records what was agreed to, when, under which policy version |

### The retention job
```python
# Runs periodically (APScheduler or cron)
# Finds recordings where created_at < (now - 30 days)
# Deletes ONLY the audio file (derived data kept for history)
# Marks storage_path = "[purged]"
# Logs every purge action
```

---

## 12. Frontend Architecture

### Routing
| Route | Page | Access |
|---|---|---|
| `/` | Landing Page (marketing) | Public |
| `/app` | Dashboard (upload, record, results, history) | Public (anon + auth) |

### State Management (Redux Toolkit)
- `authSlice`: user, accessToken, isLoading, error
- `quotaSlice`: used, limit, remaining, requires_auth

### Key Components
| Component | Purpose |
|---|---|
| `Navbar` | Logo, auth buttons, quota pill, navigation |
| `PageLoader` | 1.2s branded loading animation |
| `AudioUploader` | Drag-drop + mic recording + progress + results + history |
| `ProcessingStatus` | Staged step list driven by real backend progress |
| `ScoreCard` | Animated SVG ring with count-up |
| `MetricCards` | Accuracy/Fluency/Words/Weak sounds |
| `HighlightedTranscript` | Color-coded words with hover tooltips |
| `Charts` | Radar, Bar, Pie (Recharts) |
| `ExplainMistakeModal` | AI coaching explanation per word |
| `RecordingHistory` | Past recordings with score badges, rename, delete |
| `AssistantWidget` | Floating chat widget (RAG) |
| `ConsentBanner` | DPDP consent capture |
| `StatsStrip` | Average/Best/Count stats |

### API Client (`src/api/client.js`)
- Attaches JWT from Redux store
- On 401 for non-auth endpoints: attempts silent refresh
- Surfaces real error messages (never "Failed to fetch")
- `credentials: "include"` for cookies

---

## 13. Database Design

### MySQL Tables

| Table | Purpose |
|---|---|
| `users` | id, email, password_hash, verified_at, created_at, deleted_at |
| `otp_codes` | email, code_hash, purpose, expires_at, consumed_at, attempts |
| `refresh_tokens` | user_id, token_hash, expires_at, revoked_at |
| `anonymous_usage` | anon_session_id, ip_hash, analyses_used |
| `consent_events` | user_id/anon_id, consent_type, policy_version, granted_at |
| `recordings` | user_id/anon_id, storage_path, duration, status, title, created_at |
| `scores` | recording_id, overall_score, fluency_score, accuracy_score |
| `phoneme_scores` | recording_id, phoneme, accuracy_score |
| `data_deletion_requests` | user_id, requested_at, completed_at, summary |

### MongoDB Collections

| Collection | Purpose |
|---|---|
| `transcripts` | Word-level timestamped transcripts from Deepgram |
| `phoneme_analysis` | Full per-word scoring breakdown with expected/detected phonemes |
| `practice_sets` | Daily practice sentences per user (cached) |
| `mistake_explanations` | Cached AI explanations keyed by mistake pattern |
| `kb_chunks` | RAG knowledge base chunks with embeddings |

---

## 14. API Endpoints Reference

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Send OTP to email |
| POST | `/auth/verify-otp` | Verify OTP + set password → tokens |
| POST | `/auth/login` | Email + password → tokens |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/me` | Current user info |

### Quota & Consent
| Method | Path | Description |
|---|---|---|
| GET | `/quota/status` | Current usage |
| POST | `/consent` | Record consent event |
| GET | `/consent/status` | Check existing consents |

### Recordings
| Method | Path | Description |
|---|---|---|
| POST | `/recordings/upload` | Upload audio file |
| GET | `/recordings/{id}` | Get recording metadata |
| GET | `/recordings/{id}/status` | Poll processing status + stage |
| GET | `/recordings/{id}/transcript` | Get word-level transcript |
| GET | `/recordings/{id}/score` | Get full scoring results |
| GET | `/recordings/{id}/words/{idx}/explain` | AI explanation for a word |
| GET | `/recordings/{id}/comparison` | Compare with previous recording |
| PATCH | `/recordings/{id}` | Rename recording |
| DELETE | `/recordings/{id}` | Soft-delete recording |

### Practice & Progress
| Method | Path | Description |
|---|---|---|
| GET | `/practice/today` | Get/generate today's practice set |
| POST | `/practice/regenerate` | Force new sentences |
| GET | `/progress/history` | Full score timeline (paginated) |

### Assistant & Compliance
| Method | Path | Description |
|---|---|---|
| POST | `/assistant/ask` | RAG-grounded Q&A |
| GET | `/me/data-summary` | What data we hold |
| DELETE | `/me` | Full account deletion |
| POST | `/me/consent/withdraw` | Withdraw consent |

### Health
| Method | Path | Description |
|---|---|---|
| GET | `/health` | MySQL + MongoDB connectivity check |

---

## 15. How to Run Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- MongoDB 7.0+
- FFmpeg (`brew install ffmpeg`)
- espeak-ng (`brew install espeak-ng`)

### Setup
```bash
# Clone
git clone <repo>
cd accentiq

# Backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install deepgram torch torchaudio phonemizer sentence-transformers

# Create DB
mysql -u root -p -e "CREATE DATABASE accentiq CHARACTER SET utf8mb4;"

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Frontend (new terminal)
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8080 npm run dev
```

### Environment Variables (key ones)
| Variable | Purpose |
|---|---|
| `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` | MySQL connection |
| `MONGO_URI` | MongoDB connection |
| `JWT_SECRET` | Token signing (min 32 chars) |
| `OPENROUTER_API_KEY` | LLM for feedback + practice |
| `OPENROUTER_MODEL` | Which model (e.g. `google/gemini-2.5-flash-lite`) |
| `SMTP_HOST/PORT/USER/PASSWORD` | Email for OTP |
| `AUDIO_MIN_DURATION_SECONDS` | Min recording length (1s) |
| `AUDIO_MAX_DURATION_SECONDS` | Max recording length (45s) |

### URLs
- Frontend: http://localhost:5173
- Backend API: http://localhost:8080
- Swagger Docs: http://localhost:8080/docs

### Test User (seeded)
```
Email: test@pronunciation.coach
Password: Test1234!
```

---

## Summary

This application demonstrates:
1. **Full-stack engineering** — React frontend + FastAPI backend + dual-database architecture
2. **Real AI/ML pipeline** — Deepgram ASR → Phonemizer → scoring engine → Gemini feedback
3. **Production patterns** — auth, rate limiting, background jobs, structured errors, storage adapters
4. **Data compliance** — DPDP consent, retention, deletion (not bolted on, structural)
5. **Honest trade-offs** — every shortcut documented with an explicit upgrade path
6. **Working end-to-end** — upload audio → get real score → click for AI coaching → practice → track progress
