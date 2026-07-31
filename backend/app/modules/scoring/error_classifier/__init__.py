"""
Pronunciation Error Classifier (Phase 25)

Classifies the *type* of pronunciation error per phoneme segment:
  - correct: phoneme pronounced correctly
  - substitution: one phoneme replaced by another (e.g., /θ/ → /t/)
  - deletion: phoneme omitted entirely
  - insertion: extra phoneme added
  - distortion: phoneme produced but acoustically malformed

Uses a LightGBM classifier trained on acoustic features extracted per phoneme
segment (MFCCs, GOP score, duration, pitch, energy).
"""
