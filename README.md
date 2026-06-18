# thufail

A minimal PyTorch framework for anomaly detection on tabular enterprise data
(CSV/SQL exports). Uses an autoencoder: rows that reconstruct poorly are
flagged as anomalies.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Train on a CSV (numeric columns only are used; non-numeric columns are
dropped):

```bash
python -m thufail.train data.csv --model-out model.pt --scaler-out scaler.pkl
```

Score a CSV for anomalies:

```bash
python -m thufail.detect data.csv --model-path model.pt --scaler-path scaler.pkl --output-csv scored.csv
```

This adds `anomaly_score` and `is_anomaly` columns, flagging rows above the
given reconstruction-error percentile (default: top 5%).

## Structure

- `thufail/data.py` — CSV loading, numeric feature extraction, scaling
- `thufail/model.py` — `AutoencoderAnomalyDetector` (encoder/decoder MLP)
- `thufail/train.py` — training loop, saves model + scaler
- `thufail/detect.py` — loads a trained model, scores new data

## Combined ID-rule + ML anomaly checker

`thufail/checker.py` combines rule-based national ID validation with the
autoencoder anomaly detector, for a single CLI you can point at a CSV or
XLSX export:

```bash
python -m thufail.checker data.xlsx \
  --id-column NATIONAL_IDENTITY \
  --sheet "Sheet1" \
  --prefix 784 \
  --length 15 \
  --output-csv flagged.csv
```

Rule checks (`thufail/id_rules.py`) flag: missing values, placeholder values
(e.g. `xxxxx`), non-numeric characters, wrong digit length, wrong prefix, and
duplicate IDs. The ML side trains the autoencoder on the fly over all numeric
columns and flags the top 5% by reconstruction error. A row is flagged if
either check fires; results and reasons are written to `--output-csv`.

### Querying Oracle directly

Instead of a file, point the checker at a live query:

```bash
export ORACLE_USER=myuser
export ORACLE_PASSWORD=mypassword
export ORACLE_DSN=myhost:1521/myservice   # or a TNS alias, with TNS_ADMIN set

python -m thufail.checker --query "SELECT * FROM members" \
  --id-column NATIONAL_IDENTITY \
  --output-csv flagged.csv
```

This uses [`python-oracledb`](https://python-oracledb.readthedocs.io/) (thin
mode, no Oracle Instant Client install required for host:port/service_name
DSNs). Credentials are read only from environment variables — never pass
them as CLI arguments or commit them to a `.env` file that's tracked by git.
Run this from a machine/network that can reach your Oracle instance (this
sandboxed session cannot).
