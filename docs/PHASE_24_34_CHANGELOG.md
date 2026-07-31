# AccentIQ — Phases 24–34 Changelog

## What Changed (Summary)

The entire scoring, feedback, and practice pipeline was rebuilt from the ground up. Here's what's different from the previous version:

---

## Core Changes

### 1. Scoring Engine — COMPLETELY REBUILT (Phase 24)

**Before (v1):**
- Used ASR confidence as a proxy for pronunciation quality
- "Detected" phonemes were fabricated from confidence values (not actually recognized)
- Phoneme string-diff (Levenshtein distance) between reference and fake "detected" phonemes
- All recordings scored 83-88 regardless of quality (no differentiation)

**After (v2):**
- Uses wav2vec2-CTC model (`facebook/wav2vec2-lv-60-espeak-cv-ft`) for real acoustic analysis
- Computes Goodness of Pronunciation (GOP) scores from frame-level phoneme posteriors
- Per-phoneme scoring: knows WHICH specific sounds were mispronounced
- Scores range from 0-100 with meaningful differentiation (good=70-100, poor=20-50)
- Feature flag `SCORING_ENGINE=gop|legacy` allows side-by-side comparison

**New files:**
- `backend/app/modules/scoring/phoneme_recognizer.py` — wav2vec2-CTC model wrapper
- `backend/app/modules/scoring/gop_engine.py` — GOP computation
- `backend/app/modules/scoring/score_normalizer.py` — calibrated 0-100 mapping
- `backend/app/modules/scoring/legacy_diff_scorer.py` — old scorer kept as fallback
- `backend/app/modules/scoring/scoring_service.py` — orchestrator with dual-engine logging

---

### 2. Error Type Classification — NEW (Phase 25)

**Before:** No error classification. Just "mispronounced" or "correct".

**After:** LightGBM classifier predicts error TYPE per phoneme:
- substitution (e.g., /θ/ → /t/)
- deletion (phoneme omitted)
- distortion (phoneme attempted but acoustically poor)
- correct

**New files:**
- `backend/app/modules/scoring/error_classifier/` — full classifier module
- `ml/labeling/labeled_dataset.csv` — 3,541 training samples from 18 recordings
- `ml/labeling/LABELING_METHODOLOGY.md` — documented labeling approach
- `ml/notebooks/error_classifier_experiments.py` — confusion matrix + metrics

---

### 3. Evaluation Framework — NEW (Phase 26)

**Before:** No way to measure if scoring was accurate. No eval.

**After:** Full evaluation harness with:
- 18-recording gold dataset with human ratings
- Pearson/Spearman correlation with human judgment
- CI regression test (blocks PR if correlation drops)
- `docs/scoring-evaluation.md` written report

**New files:**
- `backend/tests/eval/run_eval.py`
- `backend/tests/eval/test_eval_regression.py`
- `backend/tests/eval/gold_dataset/`

---

### 4. Evidence-Grounded Feedback — REBUILT (Phase 27)

**Before:** LLM received "word X was mispronounced" and generated generic tips.

**After:**
- Evidence builder structures GOP scores + error types into prompt
- LLM receives SPECIFIC acoustic measurements (which phoneme, what gap, what was heard)
- Feedback verifier rejects claims not backed by measured data
- Regeneration loop (max 2 retries) before safe fallback
- No unverified specific claim ever reaches the user

**New files:**
- `backend/app/modules/feedback/evidence_builder.py`
- `backend/app/modules/feedback/feedback_verifier.py`
- Updated `prompt_templates.py` and `service.py`

---

### 5. Accent-Aware / L1-Adaptive Feedback — NEW (Phase 28)

**Before:** Same feedback for everyone regardless of native language.

**After:**
- Optional `native_language` field in user profile
- 18 curated L1 transfer patterns (Hindi, Mandarin, Spanish, Arabic, Japanese)
- Feedback explains WHY errors happen based on L1 interference
- Example: "Hindi speakers commonly produce /t/ for /θ/ because Hindi lacks interdentals"

**New files:**
- `backend/app/modules/feedback/l1_transfer_patterns.py`
- `backend/alembic/versions/0007_native_language_field.py`

---

### 6. Grounded RAG Assistant — REBUILT (Phase 29)

**Before:** Generic RAG over app documentation. Not connected to pronunciation data.

**After:**
- Structured phonetics KB (10 phoneme entries with articulation, minimal pairs, practice sentences)
- Contextual trigger: proactively surfaces guidance based on user's error history
- RAG verifier: citation-checks answers against retrieved KB entries
- `GET /assistant/suggestions` — error-history-driven recommendations

**New files:**
- `backend/app/modules/rag/phonetics_kb/kb_documents.json`
- `backend/app/modules/rag/contextual_trigger.py`
- `backend/app/modules/rag/rag_verifier.py`

---

### 7. Real-Time Streaming Scoring — NEW (Phase 30)

**Before:** Upload audio file → wait for full processing → see results.

**After:**
- WebSocket endpoint (`/ws/practice`) for live audio streaming
- Words scored in real-time as they're spoken (~1-2 second latency)
- Frontend: words light up green/yellow/red during recording
- Graceful fallback to batch mode on connection drop

**New files:**
- `backend/app/api/ws_practice.py`
- `backend/app/modules/scoring/streaming_scorer.py`
- `frontend/src/features/practice/live-feedback/`

---

### 8. Agentic Practice Planner — NEW (Phase 31)

**Before:** Daily practice sentences (single-session, no memory).

**After:**
- Cross-session error history aggregation + clustering
- 7-day structured practice plans targeting top weak phonemes
- Priority scoring: frequency × severity (GOP gap magnitude)
- Progressive difficulty: warmup → focus → challenge
- Checkpoints every 3 days for re-assessment
- Adapts when re-generated after new data

**New files:**
- `backend/app/modules/practice_generator/error_history_aggregator.py`
- `backend/app/modules/practice_generator/practice_planner_agent.py`
- `backend/app/modules/practice_generator/practice_sentence_bank.json`
- `frontend/src/features/practice/PracticePlan.jsx`

---

### 9. AI Observability Dashboard — NEW (Phase 32)

**Before:** No visibility into pipeline performance or cost.

**After:**
- Per-stage latency instrumentation (p50/p95/mean)
- Cost tracking for LLM calls
- Admin dashboard at `/admin` showing pipeline metrics
- Pipeline metrics stored in MongoDB

**New files:**
- `backend/app/modules/observability/pipeline_metrics.py`
- `backend/app/modules/observability/router.py`
- `frontend/src/features/admin-dashboard/AdminDashboard.jsx`

---

### 10. Design System Consolidation (Phase 34)

**Before:** Inline styles scattered across components.

**After:**
- Centralized design tokens (colors, typography, spacing, shadows)
- 8 shared UI components (IconBadge, StepCard, FeatureCard, PrimaryButton, Modal, DropZone, MicroLabel, FooterColumn)
- `design-system.md` canonical reference with props tables

**New files:**
- `frontend/src/styles/tokens.css`
- `frontend/src/components/ui/*.jsx` (8 components)
- `frontend/docs/design-system.md`

---

## Infrastructure Changes

| Area | Change |
|------|--------|
| Dependencies | Added: torch, torchaudio, transformers, lightgbm, librosa, scikit-learn |
| MongoDB collections | New: `pipeline_metrics`, `practice_plans`. Modified: `phoneme_analysis` (added `gop_raw_scores`, `scoring_engine_version`) |
| MySQL | New column: `users.native_language` (migration 0007) |
| Environment variables | New: `SCORING_ENGINE=gop\|legacy` |
| API endpoints | New: `GET /assistant/suggestions`, `GET/POST /practice/plan`, `PATCH /auth/me/profile`, `GET /admin/metrics/*`, `WS /ws/practice` |
| CI | Added scoring regression eval on PRs |
| Vite proxy | Added routes: `/recordings`, `/auth`, `/consent`, `/quota`, `/assistant`, `/practice`, `/progress`, `/admin`, `/ws` |

---

## Files Added/Modified Count

- **New files created**: ~40
- **Files modified**: ~15
- **Total commits**: 36+ on `feat/phase-24-gop-scoring` branch
- **New dependencies**: torch, torchaudio, transformers, lightgbm, librosa

---

*Changelog version: 1.0 | Covers: Phases 24–34 | Date: 2026-07-31*
