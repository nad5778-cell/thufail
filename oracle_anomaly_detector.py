"""
Anomaly detection on Oracle query results for NATIONAL_IDENTITY.

Combines deterministic rule checks (format/empty/duplicate) with an
unsupervised PyTorch autoencoder that learns the typical digit pattern
from the data and flags statistical outliers via reconstruction error.

Usage:
    python oracle_anomaly_detector.py
"""

import re

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

QUERY = (
    "SELECT NATIONAL_IDENTITY, FIRST_NAME FROM RPLMEMBER "
    "WHERE INSURANCE_COMPANY_NUMBER = 501"
)

# 18 chars total: 783-DDDD-DDDDDDD-D (dashes at positions 4, 9, 17)
NATIONAL_IDENTITY_PATTERN = re.compile(r"^783-\d{4}-\d{7}-\d$")


def fetch_query_result(config: dict, query: str) -> pd.DataFrame:
    with oracledb.connect(**config) as conn:
        return pd.read_sql(query, conn)


def extract_violation_flags(
    df: pd.DataFrame,
    column: str = "NATIONAL_IDENTITY",
    name_column: str = "FIRST_NAME",
) -> pd.DataFrame:
    """Flag (1=violation, 0=ok) each NATIONAL_IDENTITY rule per row.

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
            lambda v: names.loc[v.index].nunique() <= 1
        )
        consistent_name = values.map(same_name_per_id)
        is_duplicate = is_dup_id & ~consistent_name
    else:
        is_duplicate = is_dup_id

    return pd.DataFrame({
        "is_empty": is_empty.astype(float),
        "bad_format": bad_format.astype(float),
        "is_duplicate": is_duplicate.astype(float),
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
    flags = extract_violation_flags(df)
    rule_violation = (
        flags["is_empty"].astype(bool)
        | flags["bad_format"].astype(bool)
        | flags["is_duplicate"].astype(bool)
    )

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
    result["is_empty"] = flags["is_empty"].astype(bool)
    result["bad_format"] = flags["bad_format"].astype(bool)
    result["is_duplicate"] = flags["is_duplicate"].astype(bool)
    result["pattern_anomaly"] = pattern_anomaly
    result["reconstruction_error"] = reconstruction_error
    result["anomaly_score"] = anomaly_score
    result["is_anomaly"] = rule_violation.to_numpy() | pattern_anomaly
    return result


def export_dashboard(result: pd.DataFrame, output_path: str = "anomaly_dashboard.xlsx") -> None:
    """Write results to a styled Excel dashboard with a summary sheet and chart."""
    total = len(result)
    anomaly_count = int(result["is_anomaly"].sum())
    normal_count = total - anomaly_count
    anomaly_rate = (anomaly_count / total * 100) if total else 0.0

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        workbook = writer.book

        # ---- Formats ----
        title_fmt = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#1F4E78"})
        subtitle_fmt = workbook.add_format({"font_size": 10, "italic": True, "font_color": "#7F7F7F"})
        kpi_label_fmt = workbook.add_format({"bold": True, "font_size": 11, "font_color": "#FFFFFF",
                                              "bg_color": "#1F4E78", "align": "center", "valign": "vcenter",
                                              "border": 1})
        kpi_value_fmt = workbook.add_format({"bold": True, "font_size": 22, "font_color": "#1F4E78",
                                              "align": "center", "valign": "vcenter", "border": 1,
                                              "bg_color": "#EAF1F8"})
        kpi_alert_fmt = workbook.add_format({"bold": True, "font_size": 22, "font_color": "#C00000",
                                              "align": "center", "valign": "vcenter", "border": 1,
                                              "bg_color": "#FDEBEB"})
        header_fmt = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78",
                                           "align": "center", "valign": "vcenter", "border": 1})

        # ---- Summary sheet ----
        summary = workbook.add_worksheet("Dashboard")
        writer.sheets["Dashboard"] = summary
        summary.hide_gridlines(2)
        summary.set_column("A:A", 3)
        summary.set_column("B:H", 16)

        summary.merge_range("B2:H2", "Anomaly Detection Dashboard", title_fmt)
        summary.merge_range("B3:H3", "NATIONAL_IDENTITY anomalies | INSURANCE_COMPANY_NUMBER = 501",
                             subtitle_fmt)

        kpis = [
            ("Total Records", total, kpi_value_fmt),
            ("Normal Records", normal_count, kpi_value_fmt),
            ("Anomalies Found", anomaly_count, kpi_alert_fmt),
            ("Anomaly Rate", f"{anomaly_rate:.1f}%", kpi_alert_fmt),
        ]
        col = 1
        for label, value, value_fmt in kpis:
            summary.merge_range(4, col, 4, col + 1, label, kpi_label_fmt)
            summary.merge_range(5, col, 6, col + 1, value, value_fmt)
            col += 2

        # Hidden data range backing the donut chart
        summary.write_row("B9", ["Category", "Count"])
        summary.write_row("B10", ["Normal", normal_count])
        summary.write_row("B11", ["Anomaly", anomaly_count])

        chart = workbook.add_chart({"type": "doughnut"})
        chart.add_series({
            "name": "Anomaly Breakdown",
            "categories": ["Dashboard", 9, 1, 10, 1],
            "values": ["Dashboard", 9, 2, 10, 2],
            "points": [{"fill": {"color": "#2E75B6"}}, {"fill": {"color": "#C00000"}}],
            "data_labels": {"percentage": True, "font": {"bold": True}},
        })
        chart.set_title({"name": "Normal vs Anomaly"})
        chart.set_size({"width": 380, "height": 260})
        summary.insert_chart("B13", chart)

        # ---- Detail sheet ----
        result_sorted = result.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
        result_sorted.to_excel(writer, sheet_name="Details", index=False, startrow=1, header=False)
        detail = writer.sheets["Details"]

        for col_idx, col_name in enumerate(result_sorted.columns):
            detail.write(0, col_idx, col_name, header_fmt)
            width = max(14, len(col_name) + 2)
            detail.set_column(col_idx, col_idx, width)

        n_rows = len(result_sorted)
        if n_rows:
            score_col = result_sorted.columns.get_loc("anomaly_score")
            flag_col = result_sorted.columns.get_loc("is_anomaly")
            last_col = len(result_sorted.columns) - 1

            red_fmt = workbook.add_format({"bg_color": "#FDEBEB", "font_color": "#C00000"})
            score_color_fmt = workbook.add_format({"bg_color": "#FFC7CE"})

            detail.conditional_format(1, 0, n_rows, last_col, {
                "type": "formula",
                "criteria": f"=${chr(65 + flag_col)}2=TRUE",
                "format": red_fmt,
            })
            detail.conditional_format(1, score_col, n_rows, score_col, {
                "type": "3_color_scale",
                "min_color": "#63BE7B", "mid_color": "#FFEB84", "max_color": "#F8696B",
            })

        detail.autofilter(0, 0, n_rows, len(result_sorted.columns) - 1)
        detail.freeze_panes(1, 0)

        # ---- Anomalies-only sheet ----
        anomalies = result_sorted[result_sorted["is_anomaly"]].reset_index(drop=True)
        anomalies.to_excel(writer, sheet_name="Anomalies", index=False, startrow=1, header=False)
        anomaly_sheet = writer.sheets["Anomalies"]

        anomaly_header_fmt = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#C00000",
                                                    "align": "center", "valign": "vcenter", "border": 1})
        for col_idx, col_name in enumerate(anomalies.columns):
            anomaly_sheet.write(0, col_idx, col_name, anomaly_header_fmt)
            width = max(14, len(col_name) + 2)
            anomaly_sheet.set_column(col_idx, col_idx, width)

        n_anomaly_rows = len(anomalies)
        if n_anomaly_rows:
            row_fmt = workbook.add_format({"bg_color": "#FDEBEB", "font_color": "#C00000"})
            anomaly_sheet.conditional_format(1, 0, n_anomaly_rows, len(anomalies.columns) - 1, {
                "type": "no_errors",
                "format": row_fmt,
            })
            anomaly_sheet.autofilter(0, 0, n_anomaly_rows, len(anomalies.columns) - 1)
            anomaly_sheet.freeze_panes(1, 0)

    print(f"Dashboard written to {output_path}")


def main():
    df = fetch_query_result(ORACLE_CONFIG, QUERY)
    result = detect_anomalies(df)
    export_dashboard(result)


if __name__ == "__main__":
    main()
