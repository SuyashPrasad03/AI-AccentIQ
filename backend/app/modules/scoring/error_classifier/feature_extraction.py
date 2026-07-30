"""
Acoustic feature extraction for the pronunciation error classifier.

Extracts per-phoneme-segment features from audio:
  - MFCCs (13 coefficients + deltas = 39 features)
  - GOP score (from Phase 24's engine)
  - GOP gap (expected vs max posterior)
  - Duration (seconds)
  - Duration ratio (actual / expected for that phoneme)
  - Pitch statistics (mean, std, range via librosa pyin)
  - Energy statistics (mean, std, max RMS)

These features feed into the LightGBM classifier to predict error type.
"""

import numpy as np
import librosa

from app.core.logging import get_logger

logger = get_logger(__name__)

# Expected phoneme durations (approximate, in seconds)
# Based on English phonetics literature averages
_EXPECTED_DURATIONS = {
    # Vowels (longer)
    "iː": 0.12, "uː": 0.12, "ɑː": 0.13, "ɔː": 0.12, "ɜː": 0.11,
    "ɪ": 0.08, "ʊ": 0.08, "ɛ": 0.08, "æ": 0.09, "ʌ": 0.07,
    "ɒ": 0.08, "ə": 0.06,
    # Diphthongs (longer)
    "eɪ": 0.14, "aɪ": 0.15, "ɔɪ": 0.15, "aʊ": 0.15, "əʊ": 0.14,
    "ɪə": 0.13, "eə": 0.13, "ʊə": 0.13,
    # Plosives (short)
    "p": 0.06, "b": 0.05, "t": 0.06, "d": 0.05, "k": 0.07, "ɡ": 0.05,
    # Fricatives (medium)
    "f": 0.09, "v": 0.07, "θ": 0.09, "ð": 0.06, "s": 0.10, "z": 0.08,
    "ʃ": 0.10, "ʒ": 0.08, "h": 0.06,
    # Affricates
    "tʃ": 0.11, "dʒ": 0.09,
    # Nasals
    "m": 0.07, "n": 0.06, "ŋ": 0.07,
    # Liquids/Glides
    "l": 0.06, "r": 0.06, "w": 0.05, "j": 0.05,
}
DEFAULT_EXPECTED_DURATION = 0.08  # fallback


def extract_phoneme_features(
    audio: np.ndarray,
    sample_rate: int,
    start_time: float,
    end_time: float,
    phoneme: str,
    gop_score: float,
    gop_gap: float,
) -> np.ndarray:
    """
    Extract the full feature vector for a single phoneme segment.

    Args:
        audio: Full audio array (mono, float32)
        sample_rate: Audio sample rate (expected 16000)
        start_time: Phoneme start time in seconds
        end_time: Phoneme end time in seconds
        phoneme: The expected IPA phoneme symbol
        gop_score: GOP score for this phoneme (from Phase 24)
        gop_gap: GOP gap (max_posterior - expected_posterior)

    Returns:
        Feature vector (numpy array, ~48 features)
    """
    # Extract the audio segment for this phoneme
    start_sample = int(start_time * sample_rate)
    end_sample = int(end_time * sample_rate)

    # Ensure valid bounds
    start_sample = max(0, min(start_sample, len(audio) - 1))
    end_sample = max(start_sample + 1, min(end_sample, len(audio)))

    segment = audio[start_sample:end_sample]

    # Pad very short segments to minimum length for feature extraction
    min_samples = int(0.025 * sample_rate)  # 25ms minimum
    if len(segment) < min_samples:
        segment = np.pad(segment, (0, min_samples - len(segment)))

    features = []

    # 1. MFCCs (13 coefficients)
    mfcc_features = _extract_mfccs(segment, sample_rate)
    features.extend(mfcc_features)  # 39 features (13 + 13 delta + 13 delta-delta)

    # 2. GOP features
    features.append(gop_score)
    features.append(gop_gap)

    # 3. Duration features
    duration = end_time - start_time
    expected_dur = _EXPECTED_DURATIONS.get(phoneme, DEFAULT_EXPECTED_DURATION)
    duration_ratio = duration / expected_dur if expected_dur > 0 else 1.0
    features.append(duration)
    features.append(duration_ratio)

    # 4. Pitch features (mean, std, range)
    pitch_features = _extract_pitch(segment, sample_rate)
    features.extend(pitch_features)  # 3 features

    # 5. Energy features (mean, std, max)
    energy_features = _extract_energy(segment, sample_rate)
    features.extend(energy_features)  # 3 features

    return np.array(features, dtype=np.float32)


def extract_features_for_word(
    audio: np.ndarray,
    sample_rate: int,
    word_start: float,
    word_end: float,
    phonemes: list[str],
    gop_scores: list[float],
    gop_gaps: list[float],
) -> list[np.ndarray]:
    """
    Extract feature vectors for all phonemes in a word.

    Distributes the word's time span across phonemes proportionally
    based on expected durations.

    Returns:
        List of feature vectors, one per phoneme.
    """
    if not phonemes:
        return []

    word_duration = word_end - word_start
    if word_duration <= 0:
        word_duration = 0.01

    # Distribute time across phonemes based on expected durations
    expected_durs = [
        _EXPECTED_DURATIONS.get(ph, DEFAULT_EXPECTED_DURATION) for ph in phonemes
    ]
    total_expected = sum(expected_durs)
    if total_expected <= 0:
        total_expected = len(phonemes) * DEFAULT_EXPECTED_DURATION

    feature_vectors = []
    current_time = word_start

    for i, (phoneme, gop_score, gop_gap) in enumerate(
        zip(phonemes, gop_scores, gop_gaps)
    ):
        # Proportional time allocation
        proportion = expected_durs[i] / total_expected
        ph_duration = word_duration * proportion
        ph_start = current_time
        ph_end = current_time + ph_duration
        current_time = ph_end

        features = extract_phoneme_features(
            audio=audio,
            sample_rate=sample_rate,
            start_time=ph_start,
            end_time=ph_end,
            phoneme=phoneme,
            gop_score=gop_score,
            gop_gap=gop_gap,
        )
        feature_vectors.append(features)

    return feature_vectors


def get_feature_names() -> list[str]:
    """Return the names of all features in order (for model interpretability)."""
    names = []

    # MFCCs
    for i in range(13):
        names.append(f"mfcc_{i}")
    for i in range(13):
        names.append(f"mfcc_delta_{i}")
    for i in range(13):
        names.append(f"mfcc_delta2_{i}")

    # GOP
    names.append("gop_score")
    names.append("gop_gap")

    # Duration
    names.append("duration_sec")
    names.append("duration_ratio")

    # Pitch
    names.append("pitch_mean")
    names.append("pitch_std")
    names.append("pitch_range")

    # Energy
    names.append("energy_mean")
    names.append("energy_std")
    names.append("energy_max")

    return names


FEATURE_COUNT = 48  # 39 MFCC + 2 GOP + 2 duration + 3 pitch + 3 energy


def _extract_mfccs(segment: np.ndarray, sr: int) -> list[float]:
    """Extract 13 MFCCs + 13 deltas + 13 delta-deltas = 39 features."""
    try:
        # Compute MFCCs
        mfccs = librosa.feature.mfcc(y=segment, sr=sr, n_mfcc=13, n_fft=512, hop_length=160)

        # Compute deltas
        mfcc_delta = librosa.feature.delta(mfccs)
        mfcc_delta2 = librosa.feature.delta(mfccs, order=2)

        # Take mean across time frames
        mfcc_mean = np.mean(mfccs, axis=1).tolist()  # 13
        delta_mean = np.mean(mfcc_delta, axis=1).tolist()  # 13
        delta2_mean = np.mean(mfcc_delta2, axis=1).tolist()  # 13

        return mfcc_mean + delta_mean + delta2_mean

    except Exception:
        return [0.0] * 39


def _extract_pitch(segment: np.ndarray, sr: int) -> list[float]:
    """Extract pitch statistics: mean, std, range."""
    try:
        # Use pyin for pitch estimation
        f0, voiced_flag, voiced_probs = librosa.pyin(
            segment,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sr,
        )
        # Filter to voiced frames only
        voiced_f0 = f0[~np.isnan(f0)]

        if len(voiced_f0) > 0:
            return [
                float(np.mean(voiced_f0)),
                float(np.std(voiced_f0)),
                float(np.max(voiced_f0) - np.min(voiced_f0)),
            ]
    except Exception:
        pass

    return [0.0, 0.0, 0.0]


def _extract_energy(segment: np.ndarray, sr: int) -> list[float]:
    """Extract energy statistics: mean RMS, std RMS, max RMS."""
    try:
        rms = librosa.feature.rms(y=segment, frame_length=512, hop_length=160)
        rms = rms.flatten()

        if len(rms) > 0:
            return [
                float(np.mean(rms)),
                float(np.std(rms)),
                float(np.max(rms)),
            ]
    except Exception:
        pass

    return [0.0, 0.0, 0.0]
