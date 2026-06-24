FROM python:3.12-slim

WORKDIR /app

# Oracle Instant Client thin mode (python-oracledb) needs no extra system libs,
# but libaio1 is required if you later switch to thick mode.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
