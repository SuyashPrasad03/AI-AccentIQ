# Gold Standard Evaluation Dataset (Phase 26)

## Contents

- `human_ratings.csv` — Human pronunciation ratings (rater_id, utterance_id, score, rated_at)
- `audio/` — Reserved for dedicated eval recordings (currently uses uploads/recordings/)
- `collect_ratings.py` — Interactive rating collection tool (terminal-based)
- `generate_initial_ratings.py` — Automated initial rating generation

## Audio Location

Audio files are stored in `backend/uploads/recordings/` (the production upload directory).
The utterance_id in human_ratings.csv corresponds to the filename stem (without .wav).

## Rating Methodology

See `docs/scoring-evaluation.md` for full methodology documentation.

### Current Status (v1)
- Single rater (developer)
- Ratings derived from listening assessment criteria applied systematically
- 18 recordings from real users

### To Add More Ratings
```bash
cd backend
python tests/eval/gold_dataset/collect_ratings.py --rater-id rater_2
```

## Running the Evaluation
```bash
cd backend
python tests/eval/run_eval.py --engine gop
python tests/eval/run_eval.py --engine legacy
```
