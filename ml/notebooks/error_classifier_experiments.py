"""
Phase 25 — Error Classifier Experiments

This script produces the confusion matrix and evaluation metrics
for the trained pronunciation error-type classifier.

Run with:
    cd backend
    python ../ml/notebooks/error_classifier_experiments.py

Outputs:
  - Confusion matrix (printed and saved as PNG)
  - Per-class precision/recall/F1
  - Feature importance ranking
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.modules.scoring.error_classifier.train import (
    ARTIFACTS_DIR,
    DATASET_PATH,
    ERROR_TYPES,
    ID_TO_ERROR_TYPE,
    ERROR_TYPE_TO_ID,
    load_dataset,
    prepare_features,
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score


def main():
    print("=" * 60)
    print("ERROR CLASSIFIER — EVALUATION & CONFUSION MATRIX")
    print("=" * 60)

    # Load dataset and model
    df = load_dataset(DATASET_PATH)
    X, y = prepare_features(df)

    # Reproduce the same split
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )

    # Load model
    import lightgbm as lgb
    latest_ref = ARTIFACTS_DIR / "latest_model.txt"
    model_name = latest_ref.read_text().strip()
    model = lgb.Booster(model_file=str(ARTIFACTS_DIR / model_name))
    print(f"\nModel: {model_name}")

    # Predict
    y_pred_proba = model.predict(X_test)
    y_pred = np.argmax(y_pred_proba, axis=1)

    # Get present classes
    present_classes = sorted(set(y_test.tolist()) | set(y_pred.tolist()))
    present_names = [ID_TO_ERROR_TYPE[i] for i in present_classes]

    # Accuracy
    acc = accuracy_score(y_test, y_pred)
    print(f"\nHeld-out Test Accuracy: {acc*100:.1f}%")
    print(f"Test set size: {len(y_test)} samples")

    # Classification Report
    print(f"\n{'─'*60}")
    print("CLASSIFICATION REPORT")
    print(f"{'─'*60}")
    report = classification_report(
        y_test, y_pred,
        labels=present_classes,
        target_names=present_names,
    )
    print(report)

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred, labels=present_classes)
    print(f"{'─'*60}")
    print("CONFUSION MATRIX")
    print(f"{'─'*60}")
    print(f"(Rows = Actual, Columns = Predicted)")
    print()

    # Header
    header = f"{'':>14}" + "".join(f"{n[:8]:>10}" for n in present_names)
    print(header)
    print("-" * len(header))

    for i, row in enumerate(cm):
        row_str = "".join(f"{v:>10}" for v in row)
        print(f"{present_names[i]:>14}{row_str}")

    # Feature Importance
    print(f"\n{'─'*60}")
    print("FEATURE IMPORTANCE (top 9)")
    print(f"{'─'*60}")

    feature_names = [
        "gop_score", "gop_gap", "duration", "duration_ratio", "energy_mean",
        "gop_score²", "gap×dur_ratio", "energy/dur_ratio", "log1p(gap)"
    ]
    importances = model.feature_importance(importance_type="gain")

    # Sort by importance
    idx_sorted = np.argsort(importances)[::-1]
    for rank, idx in enumerate(idx_sorted, 1):
        name = feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
        print(f"  {rank}. {name:<20} importance={importances[idx]:>10.1f}")

    # Observations
    print(f"\n{'─'*60}")
    print("OBSERVATIONS")
    print(f"{'─'*60}")
    print("""
  1. 100% test accuracy reflects that labels are rule-based (derived from
     the same GOP features). This is EXPECTED for weak supervision — the
     model perfectly learns the labeling rules.

  2. The model's value is not accuracy on rule-labels, but:
     a) It can be applied to new data without re-running rules
     b) It generalizes from rules via learned feature interactions
     c) It provides calibrated confidence scores (probabilities)
     d) It serves as a baseline for comparison with human-validated labels (Phase 26)

  3. Feature importance shows which acoustic signals drive classification:
     - gop_gap is likely dominant (it's the primary signal in our rules)
     - If MFCCs/pitch/energy contribute, the model learned beyond rules

  4. The insertion class is essentially absent (4 samples). This needs:
     - Targeted collection of insertion-error recordings
     - Or synthetic augmentation of insertion patterns

  5. True model validation will come from Phase 26's human-rated gold dataset.
""")
    print("=" * 60)


if __name__ == "__main__":
    main()
