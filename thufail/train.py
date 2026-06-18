import argparse

import joblib
import torch
from torch.utils.data import DataLoader

from thufail.data import TabularDataset
from thufail.model import AutoencoderAnomalyDetector


def train(
    csv_path: str,
    model_out: str = "model.pt",
    scaler_out: str = "scaler.pkl",
    hidden_dim: int = 32,
    latent_dim: int = 8,
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 1e-3,
):
    dataset = TabularDataset(csv_path)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = AutoencoderAnomalyDetector(dataset.num_features, hidden_dim, latent_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = torch.nn.MSELoss()

    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for batch in loader:
            optimizer.zero_grad()
            recon = model(batch)
            loss = loss_fn(recon, batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * batch.size(0)
        print(f"epoch {epoch + 1}/{epochs} - loss: {total_loss / len(dataset):.6f}")

    torch.save(
        {
            "state_dict": model.state_dict(),
            "num_features": dataset.num_features,
            "hidden_dim": hidden_dim,
            "latent_dim": latent_dim,
            "columns": dataset.columns,
        },
        model_out,
    )
    joblib.dump(dataset.scaler, scaler_out)
    print(f"saved model to {model_out}, scaler to {scaler_out}")


def main():
    parser = argparse.ArgumentParser(description="Train an anomaly-detection autoencoder on a CSV of tabular data.")
    parser.add_argument("csv_path", help="Path to training CSV")
    parser.add_argument("--model-out", default="model.pt")
    parser.add_argument("--scaler-out", default="scaler.pkl")
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--latent-dim", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    train(
        args.csv_path,
        model_out=args.model_out,
        scaler_out=args.scaler_out,
        hidden_dim=args.hidden_dim,
        latent_dim=args.latent_dim,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )


if __name__ == "__main__":
    main()
