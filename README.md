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
