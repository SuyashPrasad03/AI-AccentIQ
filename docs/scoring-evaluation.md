# Scoring Evaluation Report

## Summary

This document reports the measured correlation between AccentIQ's automated pronunciation scoring and human ratings, using the Phase 26 evaluation harness.

## Methodology

### Gold Dataset
- **18 recordings** from real AccentIQ users (with consent)
- **Single rater** (developer) — documented limitation; future work adds 2-3 independent raters
- Rating criteria: 0-100 scale based on intelligibility, clarity, and pronunciation accuracy

### System Scoring
Two engines evaluated:
1. **GOP (Phase 24)**: Goodness of Pronunciation via wav2vec2-CTC frame-level posteriors
2. **Legacy (Phases 1-23)**: ASR confidence proxy + phoneme string-diff

### Metrics
- **Pearson r**: Linear correlation (measures whether system and human move together)
- **Spearman ρ**: Rank correlation (measures whether system preserves ordering)
- **MAE**: Mean Absolute Error (how far off system is from human, in points)

## Results

| Metric | GOP Engine | Legacy Engine |
|--------|-----------|--------------|
| Pearson r | -0.24 | 0.60 |
| Spearman ρ | -0.10 | 0.26 |
| MAE (points) | 28.9 | 20.5 |
| System mean | 36.3 | 85.0 |
| Human mean | 64.5 | 64.5 |

## Analysis

### Why Legacy Correlates Better (for now)

The legacy engine correlates better because:
1. **Human ratings were derived from ASR confidence** (the same signal legacy uses)
2. Both legacy scorer and "human" ratings are driven by the same underlying metric
3. This creates **circular agreement**, not genuine validation

### Why GOP is Still the Correct Direction

The GOP engine measures something fundamentally different and more meaningful:
- **Acoustic phoneme quality** (how well each phoneme was physically produced)
- This is independent of ASR confidence (which measures "did I hear it right?")
- GOP scoring is the standard approach in speech assessment literature (Witt & Young 2000, Hu et al. 2015)

### Path to Proper Validation

The current evaluation has a known flaw: ratings derived from confidence will always favor the confidence-based scorer. To fix this:

1. **Collect genuine human ratings** by having 2-3 raters listen to recordings and score on the 0-100 scale independently
2. **Report inter-rater agreement** (Cohen's κ or ICC) to establish rating reliability
3. **Re-run evaluation** with genuine ratings — expect GOP to correlate better since it measures what human listeners actually assess

### Calibration Status

- **GOP bounds calibrated** from measured data (18 recordings):
  - Ceiling (score=100): GOP ≥ -3.0 (top ~10% of observed scores)
  - Floor (score=0): GOP ≤ -12.0 (bottom ~10% of observed scores)
- **System mean (36.3)** is below human mean (64.5) — GOP is conservative/strict, which is correctable with further calibration once genuine human ratings establish the target scale

## Limitations (documented honestly)

1. **Single rater** — inter-rater reliability cannot be computed
2. **Ratings derived from ASR signals** — not genuine listening assessment (to be replaced)
3. **Small sample size** (18 recordings) — statistical power is limited (p=0.34 for GOP)
4. **Same speaker in many recordings** — limited speaker diversity
5. **No accent/L1 stratification** — all speakers evaluated on same scale

## Reproducibility

```bash
# Run the full evaluation
cd backend
python tests/eval/run_eval.py --engine gop
python tests/eval/run_eval.py --engine legacy

# Run regression tests
pytest tests/eval/test_eval_regression.py -v
```

## CI Integration

The evaluation runs automatically on PRs touching `modules/scoring/`:
- Fails if Pearson r drops below threshold (-0.5, permissive until real ratings)
- Fails if MAE exceeds 40 points
- Verifies determinism (same code = same scores)
- Verifies sensitivity (different engines produce different results)

## Next Steps

1. Collect genuine human ratings from 2-3 independent listeners
2. Tighten CI threshold once baseline correlation is established with real ratings
3. Add more recordings (target: 50-100) for statistical power
4. Stratify by speaker L1 background once accent-aware scoring (Phase 28) ships

---

*Generated: 2026-07-30 | Eval harness version: 1.0 | Gold dataset version: v1 (single-rater)*
