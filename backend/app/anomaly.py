"""Anomaly detection on NATIONAL_IDENTITY data for a single PIC.

Combines deterministic rule checks (format/empty/duplicate) with an
unsupervised PyTorch autoencoder that learns the typical digit pattern
from the data and flags statistical outliers via reconstruction error.
"""

import re

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

# 18 chars total: 783-DDDD-DDDDDDD-D (dashes at positions 4, 9, 17)
NATIONAL_IDENTITY_PATTERN = re.compile(r"^783-\d{4}-\d{7}-\d$")


def extract_violation_flags(
    df: pd.DataFrame,
    column: str = "NATIONAL_IDENTITY",
    name_column: str = "FIRST_NAME",
) -> pd.DataFrame:
    """Flag (bool) each NATIONAL_IDENTITY rule per row.

    A duplicate NATIONAL_IDENTITY is only treated as a violation if the
    records sharing it disagree on FIRST_NAME. Same ID + same first name
    across all matching rows is a valid test case (e.g. re-issued/renewal
    records for the same person), not an anomaly.
    """
    raw = df[column]
    values = raw.astype(str).str.strip()

    is_empty = raw.isna() | (values == "")
    bad_format = ~values.str.match(NATIONAL_IDENTITY_PATTERN) & ~is_empty

    is_dup_id = values.duplicated(keep=False) & ~is_empty
    if name_column in df.columns:
        names = df[name_column].astype(str).str.strip().str.lower()
        same_name_per_id = values.groupby(values).apply(
            lambda v: bool(names.loc[v.index].nunique() <= 1)
        )
        consistent_name = values.map(same_name_per_id).astype(bool)
        is_duplicate = is_dup_id & ~consistent_name
    else:
        is_duplicate = is_dup_id

    return pd.DataFrame({
        "is_empty": is_empty.astype(bool),
        "bad_format": bad_format.astype(bool),
        "is_duplicate": is_duplicate.astype(bool),
    })


def _digit_entropy(digits: str) -> float:
    counts = np.bincount([int(d) for d in digits], minlength=10)
    probs = counts[counts > 0] / len(digits)
    return float(-(probs * np.log2(probs)).sum())


def _sequential_ratio(digits: str) -> float:
    nums = [int(d) for d in digits]
    if len(nums) < 2:
        return 0.0
    rises = sum(1 for a, b in zip(nums, nums[1:]) if b == a + 1)
    return rises / (len(nums) - 1)


def _max_repeat_ratio(digits: str) -> float:
    counts = np.bincount([int(d) for d in digits], minlength=10)
    return float(counts.max() / len(digits))


def extract_pattern_features(df: pd.DataFrame, column: str = "NATIONAL_IDENTITY") -> pd.DataFrame:
    """
    Derive numeric features describing the digit pattern of each ID
    (independent of the hard format rules), so an unsupervised model
    can learn what a "typical" ID looks like and flag statistical
    outliers that still pass the format/duplicate/empty checks.
    """
    digits_only = df[column].astype(str).str.replace(r"\D", "", regex=True)

    rows = []
    for digits in digits_only:
        if len(digits) != 15:
            # Malformed/empty rows already get caught by the rule checks;
            # use neutral feature values so they don't distort training.
            rows.append([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            continue
        group2 = int(digits[3:7]) / 9999
        group3 = int(digits[7:14]) / 9999999
        group4 = int(digits[14:15]) / 9
        entropy = _digit_entropy(digits) / np.log2(10)
        max_repeat = _max_repeat_ratio(digits)
        sequential = _sequential_ratio(digits)
        rows.append([group2, group3, group4, entropy, max_repeat, sequential])

    return pd.DataFrame(
        rows,
        columns=["group2", "group3", "group4", "entropy", "max_repeat", "sequential"],
    )


class PatternAutoencoder(nn.Module):
    """Unsupervised autoencoder: learns to reconstruct typical digit-pattern
    features. Rows whose pattern is unusual reconstruct poorly, giving a
    high reconstruction error -> high anomaly score."""

    def __init__(self, num_features: int, latent_dim: int = 2):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(num_features, 4),
            nn.ReLU(),
            nn.Linear(4, latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 4),
            nn.ReLU(),
            nn.Linear(4, num_features),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


def score_pattern_anomalies(features: pd.DataFrame, epochs: int = 300) -> np.ndarray:
    """
    Train the autoencoder unsupervised (no labels) on all rows' pattern
    features, then return each row's reconstruction error as a raw
    anomaly signal. Since most IDs are assumed normal, the network learns
    to reconstruct the common pattern well; rows that deviate from it
    (unusual digit groupings, repeated/sequential digits, low entropy)
    reconstruct poorly.
    """
    mean = features.mean()
    std = features.std().replace(0, 1)
    standardized = (features - mean) / std

    x = torch.tensor(standardized.to_numpy(), dtype=torch.float32)

    model = PatternAutoencoder(num_features=x.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()

    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        reconstructed = model(x)
        loss = loss_fn(reconstructed, x)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        reconstructed = model(x)
        reconstruction_error = ((x - reconstructed) ** 2).mean(dim=1).numpy()
    return reconstruction_error


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Run rule checks + pattern-based anomaly scoring over NATIONAL_IDENTITY rows."""
    flags = extract_violation_flags(df)
    rule_violation = flags["is_empty"] | flags["bad_format"] | flags["is_duplicate"]

    pattern_features = extract_pattern_features(df)
    reconstruction_error = score_pattern_anomalies(pattern_features)

    # Statistical threshold learned from the data itself: rows whose
    # reconstruction error is more than 2 std above the mean (among
    # rule-valid rows) are flagged as pattern anomalies.
    valid_errors = reconstruction_error[~rule_violation.to_numpy()]
    if len(valid_errors) > 1:
        err_mean, err_std = valid_errors.mean(), valid_errors.std() or 1.0
    else:
        err_mean, err_std = reconstruction_error.mean(), reconstruction_error.std() or 1.0
    pattern_anomaly = reconstruction_error > (err_mean + 2 * err_std)

    anomaly_score = 1 / (1 + np.exp(-(reconstruction_error - err_mean) / err_std))

    result = df.copy()
    result["is_empty"] = flags["is_empty"]
    result["bad_format"] = flags["bad_format"]
    result["is_duplicate"] = flags["is_duplicate"]
    result["pattern_anomaly"] = pattern_anomaly
    result["reconstruction_error"] = reconstruction_error
    result["anomaly_score"] = anomaly_score
    result["is_anomaly"] = rule_violation.to_numpy() | pattern_anomaly
    return result
