import argparse

import joblib
import pandas as pd
import torch

from thufail.data import TabularDataset
from thufail.model import AutoencoderAnomalyDetector


def detect(
    csv_path: str,
    model_path: str = "model.pt",
    scaler_path: str = "scaler.pkl",
    threshold_percentile: float = 95.0,
    output_csv: str | None = None,
) -> pd.DataFrame:
    checkpoint = torch.load(model_path, weights_only=False)
    scaler = joblib.load(scaler_path)

    dataset = TabularDataset(csv_path, scaler=scaler)
    model = AutoencoderAnomalyDetector(
        checkpoint["num_features"], checkpoint["hidden_dim"], checkpoint["latent_dim"]
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    with torch.no_grad():
        scores = model.reconstruction_error(dataset.features).numpy()

    threshold = pd.Series(scores).quantile(threshold_percentile / 100)

    result = pd.read_csv(csv_path)
    result["anomaly_score"] = scores
    result["is_anomaly"] = scores > threshold

    if output_csv:
        result.to_csv(output_csv, index=False)
        print(f"saved results to {output_csv}")

    print(f"flagged {result['is_anomaly'].sum()} / {len(result)} rows as anomalies "
          f"(threshold at p{threshold_percentile}: {threshold:.6f})")
    return result


def main():
    parser = argparse.ArgumentParser(description="Score rows in a CSV for anomalies using a trained autoencoder.")
    parser.add_argument("csv_path", help="Path to CSV to score")
    parser.add_argument("--model-path", default="model.pt")
    parser.add_argument("--scaler-path", default="scaler.pkl")
    parser.add_argument("--threshold-percentile", type=float, default=95.0)
    parser.add_argument("--output-csv", default=None)
    args = parser.parse_args()

    detect(
        args.csv_path,
        model_path=args.model_path,
        scaler_path=args.scaler_path,
        threshold_percentile=args.threshold_percentile,
        output_csv=args.output_csv,
    )


if __name__ == "__main__":
    main()
