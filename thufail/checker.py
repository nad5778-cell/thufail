import argparse

import pandas as pd
import torch
from torch.utils.data import DataLoader

from thufail.id_rules import check_national_id
from thufail.model import AutoencoderAnomalyDetector


def load_table(path: str | None = None, sheet: str | int = 0, query: str | None = None) -> pd.DataFrame:
    if query:
        from thufail.db import fetch_oracle

        return fetch_oracle(query)
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path, sheet_name=sheet)
    return pd.read_csv(path)


def run_id_checks(df: pd.DataFrame, id_column: str, prefix: str, length: int) -> pd.DataFrame:
    issues = df[id_column].map(lambda v: check_national_id(v, prefix, length))
    df["id_issues"] = issues.map(lambda lst: ";".join(lst) if lst else "")

    dup_mask = df[id_column].notna() & df.duplicated(subset=[id_column], keep=False)
    df.loc[dup_mask, "id_issues"] += df.loc[dup_mask, "id_issues"].map(
        lambda s: ";duplicate_id" if s else "duplicate_id"
    )
    return df


def run_ml_check(df: pd.DataFrame, epochs: int = 30, hidden_dim: int = 32, latent_dim: int = 8) -> pd.DataFrame:
    numeric = df.select_dtypes(include="number")
    numeric = numeric.fillna(numeric.mean(numeric_only=True))

    if numeric.shape[1] == 0 or len(numeric) < 10:
        df["ml_anomaly_score"] = 0.0
        df["is_ml_anomaly"] = False
        return df

    mean, std = numeric.mean(), numeric.std().replace(0, 1)
    features = torch.tensor(((numeric - mean) / std).values, dtype=torch.float32)

    model = AutoencoderAnomalyDetector(features.shape[1], hidden_dim, latent_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.MSELoss()
    loader = DataLoader(features, batch_size=64, shuffle=True)

    model.train()
    for _ in range(epochs):
        for batch in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(batch), batch)
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        scores = model.reconstruction_error(features).numpy()

    threshold = pd.Series(scores).quantile(0.95)
    df["ml_anomaly_score"] = scores
    df["is_ml_anomaly"] = scores > threshold
    return df


def check(
    path: str | None,
    id_column: str,
    sheet: str | int = 0,
    query: str | None = None,
    prefix: str = "784",
    length: int = 15,
    epochs: int = 30,
    output_csv: str | None = None,
) -> pd.DataFrame:
    df = load_table(path, sheet, query)
    df = run_id_checks(df, id_column, prefix, length)
    df = run_ml_check(df, epochs)

    df["is_flagged"] = (df["id_issues"] != "") | df["is_ml_anomaly"]

    print(f"checked {len(df)} rows")
    print(f"id rule violations: {(df['id_issues'] != '').sum()}")
    print(f"ml anomalies (reconstruction error, top 5%): {df['is_ml_anomaly'].sum()}")
    print(f"total flagged: {df['is_flagged'].sum()}")

    if output_csv:
        df.to_csv(output_csv, index=False)
        print(f"saved results to {output_csv}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Combined rule-based + ML anomaly checker for enterprise tabular data."
    )
    parser.add_argument("path", nargs="?", default=None, help="Path to CSV or XLSX file (omit when using --query)")
    parser.add_argument("--id-column", required=True, help="Column name holding the national ID")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (xlsx only)")
    parser.add_argument(
        "--query",
        default=None,
        help="SQL query to run against Oracle instead of reading a file. "
        "Requires ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN env vars.",
    )
    parser.add_argument("--prefix", default="784", help="Expected national ID prefix")
    parser.add_argument("--length", type=int, default=15, help="Expected national ID digit length")
    parser.add_argument("--epochs", type=int, default=30, help="Autoencoder training epochs")
    parser.add_argument("--output-csv", default="flagged.csv")
    args = parser.parse_args()

    sheet = args.sheet
    try:
        sheet = int(sheet)
    except (TypeError, ValueError):
        pass

    if not args.path and not args.query:
        parser.error("provide either a path or --query")

    check(
        args.path,
        id_column=args.id_column,
        sheet=sheet,
        query=args.query,
        prefix=args.prefix,
        length=args.length,
        epochs=args.epochs,
        output_csv=args.output_csv,
    )


if __name__ == "__main__":
    main()
