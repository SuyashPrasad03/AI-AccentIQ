"""
Phase 25 — Error Classifier Inference Wrapper

Loads the trained LightGBM model artifact and provides prediction functions.
Handles missing/corrupt model files gracefully (falls back to GOP-only, no crash).

Usage:
    from app.modules.scoring.error_classifier.model import predict_error_types
    predictions = predict_error_types(feature_vectors)
"""

import threading
from pathlib import Path

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ERROR_TYPES = ["correct", "substitution", "deletion", "insertion", "distortion"]
ID_TO_ERROR_TYPE = {i: et for i, et in enumerate(ERROR_TYPES)}

# Module-level singleton
_model = None
_lock = threading.Lock()
_model_loaded = False
_model_failed = False  # Don't keep retrying if the model can't load


def _ensure_model_loaded() -> bool:
    """
    Lazy-load the trained model. Thread-safe.
    Returns True if model is available, False otherwise.
    """
    global _model, _model_loaded, _model_failed

    if _model_loaded:
        return True
    if _model_failed:
        return False

    with _lock:
        if _model_loaded:
            return True
        if _model_failed:
            return False

        try:
            import lightgbm as lgb

            # Find the model file
            model_path = _find_latest_model()
            if model_path is None:
                logger.warning(
                    "error_classifier_no_model",
                    msg="No trained model artifact found. Error classification disabled.",
                    artifacts_dir=str(ARTIFACTS_DIR),
                )
                _model_failed = True
                return False

            _model = lgb.Booster(model_file=str(model_path))
            _model_loaded = True

            logger.info(
                "error_classifier_loaded",
                model_path=model_path.name,
            )
            return True

        except Exception as exc:
            logger.error(
                "error_classifier_load_failed",
                error=str(exc),
                msg="Error classifier will be disabled. Falling back to GOP-only.",
            )
            _model_failed = True
            return False


def _find_latest_model() -> Path | None:
    """Find the latest model artifact file."""
    if not ARTIFACTS_DIR.exists():
        return None

    # Check for latest reference file
    latest_ref = ARTIFACTS_DIR / "latest_model.txt"
    if latest_ref.exists():
        model_name = latest_ref.read_text().strip()
        model_path = ARTIFACTS_DIR / model_name
        if model_path.exists():
            return model_path

    # Fallback: find any .txt model file (LightGBM saves as text)
    model_files = sorted(ARTIFACTS_DIR.glob("error_classifier_*.txt"))
    if model_files:
        return model_files[-1]  # Latest by name (timestamp in filename)

    return None


def predict_error_types(
    feature_vectors: list[np.ndarray],
) -> list[dict]:
    """
    Predict error types for a list of phoneme feature vectors.

    Args:
        feature_vectors: List of numpy arrays from feature_extraction.extract_phoneme_features()

    Returns:
        List of dicts: [{error_type: str, confidence: float}]
        Returns empty list if model is unavailable.
    """
    if not _ensure_model_loaded():
        return []

    if not feature_vectors:
        return []

    try:
        # Stack feature vectors into a matrix
        # The training used 9 features: gop_score, gop_gap, duration, duration_ratio,
        # energy_mean + 4 derived features
        # But feature_vectors from extract_phoneme_features has 48 features
        # We need to extract the subset the model was trained on
        X = _extract_model_features(feature_vectors)

        # Predict
        probabilities = _model.predict(X)  # shape: (n_samples, n_classes)

        results = []
        for probs in probabilities:
            predicted_class = int(np.argmax(probs))
            confidence = float(probs[predicted_class])
            error_type = ID_TO_ERROR_TYPE.get(predicted_class, "correct")
            results.append({
                "error_type": error_type,
                "error_type_confidence": round(confidence, 4),
            })

        return results

    except Exception as exc:
        logger.error(
            "error_classifier_predict_failed",
            error=str(exc),
            num_samples=len(feature_vectors),
        )
        return []


def _extract_model_features(feature_vectors: list[np.ndarray]) -> np.ndarray:
    """
    Extract the 9 features the model was trained on from the full 48-feature vectors.

    Training features (in order):
      0: gop_score (index 39 in full vector)
      1: gop_gap (index 40)
      2: duration (index 41)
      3: duration_ratio (index 42)
      4: energy_mean (index 45)  # first of the 3 energy features
      5: gop_score^2 (derived)
      6: gop_gap * duration_ratio (derived)
      7: energy_mean / duration_ratio (derived)
      8: log1p(gop_gap) (derived)
    """
    rows = []
    for fv in feature_vectors:
        if len(fv) >= 48:
            gop_score = fv[39]
            gop_gap = fv[40]
            duration = fv[41]
            duration_ratio = fv[42]
            energy_mean = fv[45]
        else:
            # If feature vector is shorter (shouldn't happen), use zeros
            gop_score = fv[0] if len(fv) > 0 else 0.0
            gop_gap = fv[1] if len(fv) > 1 else 0.0
            duration = fv[2] if len(fv) > 2 else 0.0
            duration_ratio = fv[3] if len(fv) > 3 else 1.0
            energy_mean = fv[4] if len(fv) > 4 else 0.0

        # Derived features (same as training)
        gop_sq = gop_score ** 2
        gap_dur = gop_gap * duration_ratio
        energy_dur = energy_mean / max(duration_ratio, 0.01)
        log_gap = float(np.log1p(max(gop_gap, 0)))

        rows.append([
            gop_score, gop_gap, duration, duration_ratio, energy_mean,
            gop_sq, gap_dur, energy_dur, log_gap,
        ])

    return np.array(rows, dtype=np.float32)


def predict_single(
    gop_score: float,
    gop_gap: float,
    duration: float,
    duration_ratio: float,
    energy_mean: float,
) -> dict:
    """
    Convenience function: predict error type from raw features directly.
    Used when full feature extraction isn't available.

    Returns: {error_type: str, error_type_confidence: float}
    """
    if not _ensure_model_loaded():
        return {"error_type": "correct", "error_type_confidence": 0.0}

    try:
        # Build the 9-feature vector
        gop_sq = gop_score ** 2
        gap_dur = gop_gap * duration_ratio
        energy_dur = energy_mean / max(duration_ratio, 0.01)
        log_gap = float(np.log1p(max(gop_gap, 0)))

        X = np.array([[
            gop_score, gop_gap, duration, duration_ratio, energy_mean,
            gop_sq, gap_dur, energy_dur, log_gap,
        ]], dtype=np.float32)

        probs = _model.predict(X)[0]
        predicted_class = int(np.argmax(probs))
        confidence = float(probs[predicted_class])

        return {
            "error_type": ID_TO_ERROR_TYPE.get(predicted_class, "correct"),
            "error_type_confidence": round(confidence, 4),
        }

    except Exception as exc:
        logger.error("error_classifier_single_predict_failed", error=str(exc))
        return {"error_type": "correct", "error_type_confidence": 0.0}


def is_model_available() -> bool:
    """Check if the error classifier model is loaded and ready."""
    return _model_loaded and _model is not None
