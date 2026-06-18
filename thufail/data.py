import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset


class TabularDataset(Dataset):
    """Wraps a CSV of numeric enterprise data for unsupervised anomaly detection.

    Non-numeric columns are dropped since the autoencoder expects a numeric
    feature vector per row. Fit the scaler on training data, then reuse it
    (via `scaler=`) when loading data to score, so both share the same scale.
    """

    def __init__(self, csv_path: str, scaler: StandardScaler | None = None):
        df = pd.read_csv(csv_path)
        df = df.select_dtypes(include="number").fillna(df.mean(numeric_only=True))

        self.columns = list(df.columns)
        self.scaler = scaler or StandardScaler().fit(df.values)
        self.features = torch.tensor(
            self.scaler.transform(df.values), dtype=torch.float32
        )

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features[idx]

    @property
    def num_features(self):
        return self.features.shape[1]
