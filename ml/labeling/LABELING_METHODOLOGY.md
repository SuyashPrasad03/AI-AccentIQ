# Labeling Methodology — Pronunciation Error-Type Classifier

## Overview

This document describes how the training labels for the pronunciation error-type classifier were generated. This is a critical piece of documentation for reproducibility and interview defensibility.

## Label Schema

Each phoneme segment is assigned one of five error types:

| Error Type | Definition | Example |
|---|---|---|
| `correct` | Phoneme pronounced within acceptable acoustic range | /θ/ in "think" sounds like /θ/ |
| `substitution` | One phoneme consistently replaced by another | /θ/ → /t/ ("think" → "tink") |
| `deletion` | Phoneme omitted entirely or severely shortened | "months" → "mon_s" (th deleted) |
| `insertion` | Extra phoneme added that shouldn't be there | "film" → "filum" |
| `distortion` | Phoneme attempted but acoustically malformed | /r/ produced but sounds neither /r/ nor /l/ |

## Data Source

- **18 real user recordings** from AccentIQ production (users consented to data use)
- **3,541 phoneme segments** extracted via forced alignment (WhisperX timestamps)
- Each recording is 10–45 seconds of read English speech

## Labeling Approach: Hybrid Weak Supervision

We used a **rule-based weak supervision** approach (Ratner et al., "Data Programming: Creating Large Training Sets Quickly", NeurIPS 2016) to generate initial labels from acoustic measurements:

### Labeling Functions (Rules)

1. **Substitution** (GOP gap > 3.0 AND max_posterior ≠ expected):
   The wav2vec2-CTC model very confidently assigns a *different* phoneme than expected. Large gap = high confidence it's wrong.

2. **Deletion** (GOP gap > 1.5 AND duration_ratio < 0.3):
   Phoneme segment is less than 30% of expected duration AND acoustic model doesn't detect it well.

3. **Insertion** (GOP gap > 1.5 AND duration_ratio > 2.5):
   Segment is 2.5× longer than expected — likely contains extra articulatory material.

4. **Distortion** (1.5 < GOP gap ≤ 3.0 AND low energy OR moderate gap):
   Model detects something between expected and a clear substitution — the phoneme was attempted but produced poorly.

5. **Correct** (GOP gap < 1.0):
   Model confidently agrees the expected phoneme was produced.

### Why Weak Supervision (Not Manual Labeling of All 3,541 Samples)?

- **Scalability**: Manual phoneme-level labeling requires trained phoneticians and takes ~2-3 minutes per phoneme segment. 3,541 samples × 2 min = ~118 hours of expert time.
- **Consistency**: Rule-based labels are deterministic. Human labels have inter-annotator disagreement (typical κ = 0.6-0.8 for pronunciation assessment tasks).
- **Bootstrapping**: The model trained on rule-based labels generalizes beyond the exact rules by learning feature interactions the rules don't capture (demonstrated by the model learning from MFCCs, pitch, energy in addition to just GOP gap).

### Known Limitations

1. **Circular validation risk**: Since labels come from the same GOP features used for training, the held-out accuracy (100%) reflects rule-learning, not true pronunciation assessment accuracy. **Real validation requires Phase 26's human-rated gold set.**
2. **Insertion class is underrepresented** (4 samples / 0.1%) — the rule threshold is strict. May need to collect targeted insertion examples.
3. **Rules encode our assumptions about what constitutes each error type** — these assumptions should be validated against phonetics literature and human expert review.

## Retraining Path

The training script (`backend/app/modules/scoring/error_classifier/train.py`) is re-runnable:
1. Add more recordings to the `uploads/recordings/` directory
2. Re-run `ml/labeling/label_tool.py` to regenerate labels
3. Re-run the training script to produce a new versioned model artifact

As human-labeled data becomes available (Phase 26), mix rule-based and human labels with appropriate weighting.

## Dataset Statistics (v1)

| Metric | Value |
|---|---|
| Total samples | 3,541 |
| Recordings | 18 |
| correct | 660 (18.6%) |
| substitution | 2,496 (70.5%) |
| distortion | 381 (10.8%) |
| deletion | 4 (0.1%) |
| insertion | 0 (0.0%) |
| Label source | Rule-based v1 |
| Date generated | 2026-07-30 |
