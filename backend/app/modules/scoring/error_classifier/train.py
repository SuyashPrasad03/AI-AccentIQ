#!/usr/bin/env python3
"""
Phase 25 — LightGBM Error-Type Classifier Training Script

Trains a gradient-boosted tree classifier to predict pronunciation error types:
  - correct
  - substitution
  - deletion
  - insertion
  - distortion

Input: labeled_dataset.csv (from label_tool.py)
Output: Versioned model artifact in artifacts/ directory

Re-runnable: can be re-executed as more labeled data is collected.
Reports honest held-out metrics (train/val/test split, stratified by error type).

Usage:
    cd backend
    python -m app.modules.scoring.error_classifier.train

Or directly:
    python app/modules/scoring/error_classifier/train.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
import lightgbm as lgb

# Add paths — ensure the backend root is on sys.path
_backend_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app.modules.scoring.error_classifier.feature_extraction import get_feature_names, FEATURE_COUNT

# ── Configuration ─────────────────────────────────────────────────────────────
DATASET_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "ml" / "labeling" / "labeled_dataset.csv"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
RANDOM_SEED = 42

# Error type encoding
ERROR_TYPES = ["correct", "substitution", "deletion", "insertion", "distortion"]
ERROR_TYPE_TO_ID = {et: i for i, et in enumerate(ERROR_TYPES)}
ID_TO_ERROR_TYPE = {i: et for i, et in enumerate(ERROR_TYPES)}

# LightGBM hyperparameters (tuned for small dataset, prevent overfitting)
LGBM_PARAMS = {
    "objective": "multiclass",
    "num_class": len(ERROR_TYPES),
    "metric": "multi_logloss",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "min_child_samples": 10,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "verbose": -1,
    "seed": RANDOM_SEED,
}
NUM_BOOST_ROUNDS = 200
EARLY_STOPPING_ROUNDS = 30


def load_dataset(path: Path) -> pd.DataFrame:
    """Load and validate the labeled dataset."""
    df = pd.read_csv(path)
    print(f"Loaded dataset: {len(df)} samples from {path.name}")
    print(f"  Error type distribution:")
    for et, count in df["error_type"].value_counts().items():
        print(f"    {et:<14} {count:>5} ({count/len(df)*100:.1f}%)")
    return df


def prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract feature matrix X and label vector y from the dataset.

    Uses the numeric columns from the labeled dataset as features:
      - gop_score, gop_gap, duration, duration_ratio, energy_mean
    Plus derived features from the raw data.
    """
    # Core features from the labeled dataset
    feature_cols = ["gop_score", "gop_gap", "duration", "duration_ratio", "energy_mean"]

    # Verify columns exist
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in dataset: {missing}")

    X = df[feature_cols].values.astype(np.float32)

    # Add derived features
    # 1. GOP score squared (captures non-linear relationships)
    gop_sq = (df["gop_score"].values ** 2).reshape(-1, 1)
    # 2. Gap * duration interaction
    gap_dur = (df["gop_gap"].values * df["duration_ratio"].values).reshape(-1, 1)
    # 3. Energy / duration ratio
    energy_dur = (df["energy_mean"].values / df["duration_ratio"].values.clip(0.01)).reshape(-1, 1)
    # 4. Log gap (captures log-scale relationships)
    log_gap = np.log1p(df["gop_gap"].values).reshape(-1, 1)

    X = np.hstack([X, gop_sq, gap_dur, energy_dur, log_gap])

    # Encode labels
    y = df["error_type"].map(ERROR_TYPE_TO_ID).values.astype(np.int32)

    # Handle NaN/inf
    X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)

    return X, y


def train_model(X: np.ndarray, y: np.ndarray) -> tuple[lgb.Booster, dict]:
    """
    Train the LightGBM classifier with stratified train/val/test split.

    Returns the trained model and metrics dict.
    """
    # Stratified split: 70% train, 15% val, 15% test
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=0.15, random_state=RANDOM_SEED, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=0.176,  # 0.176 of 85% ≈ 15% of total
        random_state=RANDOM_SEED, stratify=y_trainval
    )

    print(f"\n  Split sizes:")
    print(f"    Train: {len(X_train)} ({len(X_train)/len(X)*100:.1f}%)")
    print(f"    Val:   {len(X_val)} ({len(X_val)/len(X)*100:.1f}%)")
    print(f"    Test:  {len(X_test)} ({len(X_test)/len(X)*100:.1f}%)")

    # Verify stratification
    print(f"\n  Class distribution in test set:")
    for cls_id, cls_name in ID_TO_ERROR_TYPE.items():
        count = np.sum(y_test == cls_id)
        if count > 0:
            print(f"    {cls_name:<14} {count:>4}")

    # Create LightGBM datasets
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    # Train with early stopping
    callbacks = [
        lgb.early_stopping(stopping_rounds=EARLY_STOPPING_ROUNDS),
        lgb.log_evaluation(period=50),
    ]

    print(f"\n  Training LightGBM ({NUM_BOOST_ROUNDS} max rounds, early stop at {EARLY_STOPPING_ROUNDS})...")
    model = lgb.train(
        LGBM_PARAMS,
        train_data,
        num_boost_round=NUM_BOOST_ROUNDS,
        valid_sets=[val_data],
        valid_names=["validation"],
        callbacks=callbacks,
    )

    # Evaluate on test set
    y_pred_proba = model.predict(X_test)
    y_pred = np.argmax(y_pred_proba, axis=1)

    test_accuracy = accuracy_score(y_test, y_pred)
    
    # Get labels that actually appear in the data
    present_labels = sorted(set(y_test.tolist()) | set(y_pred.tolist()))
    present_names = [ID_TO_ERROR_TYPE[i] for i in present_labels]
    
    report = classification_report(
        y_test, y_pred,
        labels=present_labels,
        target_names=present_names,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_test, y_pred)

    # Also evaluate on train set (to detect overfitting)
    y_train_pred = np.argmax(model.predict(X_train), axis=1)
    train_accuracy = accuracy_score(y_train, y_train_pred)

    metrics = {
        "test_accuracy": round(test_accuracy, 4),
        "train_accuracy": round(train_accuracy, 4),
        "overfit_gap": round(train_accuracy - test_accuracy, 4),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "best_iteration": model.best_iteration,
        "num_features": X.shape[1],
        "train_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
    }

    return model, metrics


def save_model(model: lgb.Booster, metrics: dict) -> Path:
    """Save the trained model with version in filename."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_filename = f"error_classifier_v1_{timestamp}.txt"
    metrics_filename = f"error_classifier_v1_{timestamp}_metrics.json"

    model_path = ARTIFACTS_DIR / model_filename
    metrics_path = ARTIFACTS_DIR / metrics_filename

    # Save model
    model.save_model(str(model_path))

    # Save metrics
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    # Also save a "latest" symlink-style reference
    latest_ref = ARTIFACTS_DIR / "latest_model.txt"
    latest_ref.write_text(model_filename)

    print(f"\n  Model saved: {model_path.name}")
    print(f"  Metrics saved: {metrics_path.name}")

    return model_path


def print_results(metrics: dict):
    """Print a formatted results summary."""
    print(f"\n{'='*60}")
    print("TRAINING RESULTS")
    print(f"{'='*60}")
    print(f"  Test Accuracy:  {metrics['test_accuracy']*100:.1f}%")
    print(f"  Train Accuracy: {metrics['train_accuracy']*100:.1f}%")
    print(f"  Overfit Gap:    {metrics['overfit_gap']*100:.1f}%")
    print(f"  Best Iteration: {metrics['best_iteration']}")

    print(f"\n  Confusion Matrix (rows=actual, cols=predicted):")
    cm = np.array(metrics["confusion_matrix"])
    labels = [ID_TO_ERROR_TYPE[i] for i in range(len(ERROR_TYPES))]

    # Print header
    header = "            " + "".join(f"{l[:6]:>8}" for l in labels)
    print(f"  {header}")
    for i, row in enumerate(cm):
        if np.sum(row) > 0:  # Only print rows with actual samples
            row_str = "".join(f"{v:>8}" for v in row)
            print(f"  {labels[i]:<12}{row_str}")

    print(f"\n  Per-class metrics:")
    report = metrics["classification_report"]
    for cls_name in ERROR_TYPES:
        if cls_name in report:
            r = report[cls_name]
            if r["support"] > 0:
                print(
                    f"    {cls_name:<14} "
                    f"precision={r['precision']:.2f}  "
                    f"recall={r['recall']:.2f}  "
                    f"f1={r['f1-score']:.2f}  "
                    f"support={r['support']}"
                )
    print(f"{'='*60}")


def main():
    print("Phase 25 — Error-Type Classifier Training")
    print(f"{'─'*60}")

    # Load dataset
    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        print("Run ml/labeling/label_tool.py first to generate labeled data.")
        sys.exit(1)

    df = load_dataset(DATASET_PATH)

    # Prepare features
    X, y = prepare_features(df)
    print(f"\n  Feature matrix shape: {X.shape}")
    print(f"  Classes present: {sorted(set(y.tolist()))}")

    # Train
    model, metrics = train_model(X, y)

    # Save
    model_path = save_model(model, metrics)

    # Report
    print_results(metrics)

    return model_path, metrics


if __name__ == "__main__":
    main()
