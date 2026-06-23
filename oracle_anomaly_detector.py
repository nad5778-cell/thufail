"""
Anomaly detection on Oracle query results using z-scores combined
through a small PyTorch scoring model.

Usage:
    python oracle_anomaly_detector.py
"""

import oracledb
import pandas as pd
import numpy as np
import torch
import torch.nn as nn


ORACLE_CONFIG = {
    "user": "your_user",
    "password": "your_password",
    "dsn": "host:port/service_name",
}

QUERY = "SELECT * FROM your_table"

ZSCORE_THRESHOLD = 3.0
ANOMALY_SCORE_THRESHOLD = 0.5


def fetch_query_result(config: dict, query: str) -> pd.DataFrame:
    with oracledb.connect(**config) as conn:
        return pd.read_sql(query, conn)


def compute_zscores(df: pd.DataFrame) -> pd.DataFrame:
    numeric_df = df.select_dtypes(include=[np.number])
    mean = numeric_df.mean()
    std = numeric_df.std().replace(0, 1)
    return (numeric_df - mean) / std


class AnomalyScorer(nn.Module):
    """Combines per-column z-scores into a single anomaly score per row."""

    def __init__(self, num_features: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(num_features, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def score_anomalies(zscores: pd.DataFrame) -> np.ndarray:
    features = torch.tensor(zscores.abs().to_numpy(), dtype=torch.float32)

    model = AnomalyScorer(num_features=features.shape[1])

    # Unsupervised heuristic: train the scorer to reproduce a target derived
    # from the max absolute z-score per row, so high-deviation rows get high scores.
    target = (features.max(dim=1).values / ZSCORE_THRESHOLD).clamp(max=1.0)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()

    model.train()
    for _ in range(200):
        optimizer.zero_grad()
        preds = model(features)
        loss = loss_fn(preds, target)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        scores = model(features).numpy()
    return scores


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    zscores = compute_zscores(df)
    scores = score_anomalies(zscores)

    result = df.copy()
    result["anomaly_score"] = scores
    result["is_anomaly"] = scores >= ANOMALY_SCORE_THRESHOLD
    return result


def main():
    df = fetch_query_result(ORACLE_CONFIG, QUERY)
    result = detect_anomalies(df)

    anomalies = result[result["is_anomaly"]]
    print(f"Fetched {len(df)} rows, found {len(anomalies)} anomalies.")
    print(anomalies)


if __name__ == "__main__":
    main()
