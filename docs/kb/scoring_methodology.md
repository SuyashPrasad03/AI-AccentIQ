# Scoring Methodology

## Overview
Your pronunciation score (0-100) is calculated using a transparent, explainable formula. There is no single opaque ML score — every word is individually assessed and the methodology is fully documented.

## Word-Level Score
Each word gets a score based on three components:
- **Confidence (60% weight)**: How clearly the speech recognition system heard you. Higher confidence means clearer pronunciation.
- **Timing (20% weight)**: Whether the word duration matches natural English speech pace (~150 words per minute). Too fast or too slow reduces this score.
- **Phoneme Accuracy (20% weight)**: How closely your pronunciation matches the expected phoneme sequence using IPA (International Phonetic Alphabet) comparison.

## Mistake Classification
Every word is classified into exactly one category:
- **Correct** (score ≥ 80): Well pronounced, no issues detected.
- **Mispronounced** (phoneme distance > 0.3): A specific sound substitution was detected (e.g., replacing TH /θ/ with T /t/).
- **Unclear** (confidence < 0.6): The word wasn't captured clearly — may be too quiet or too fast.
- **Mistimed** (timing deviation > 50%): The word's duration deviated significantly from expected.

## Overall Score
The overall score is a duration-weighted average of all word scores. Longer words contribute more to the total, which reflects their acoustic importance.

## Sub-Scores
- **Accuracy Score**: Average of the phoneme accuracy component across all words.
- **Fluency Score**: Based on speech rate vs. expected (150 WPM) and the ratio of silence to speech time.

## Weak Phonemes
Phonemes that appear in 2 or more mispronounced words are flagged as "weak phonemes." These feed directly into your personalized practice sentences.

## Phoneme Distance
We compare your pronunciation against a reference using a phonetically-weighted distance function. For example:
- Replacing /θ/ (TH) with /t/ is a severity of 0.3 (common, mild error)
- Replacing /θ/ with /m/ is a severity of 0.6 (very different sound)

This means common L2 English errors are treated more leniently than truly wrong sounds.

## Limitations
This system uses ASR confidence as a proxy for acoustic quality rather than a dedicated phoneme classifier. This is approximately 80% accurate for identifying problem areas. A true acoustic phoneme model would improve precision (documented as a future upgrade).
