"""
BI reports integration client.

Authenticates against the OAuth2 token endpoint using the client_credentials
grant, then calls the BI end point with the resulting bearer token.

Required environment variables:
    BI_ACCESS_TOKEN_URL
    BI_CLIENT_ID
    BI_CLIENT_SECRET_KEY
    BI_END_POINT_URL
"""

import os
import sys
from typing import Optional

import requests


def get_access_token(token_url: str, client_id: str, client_secret: str) -> str:
    response = requests.post(
        token_url,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def call_bi_endpoint(endpoint_url: str, access_token: str, payload: Optional[dict] = None) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(endpoint_url, headers=headers, json=payload or {}, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> int:
    required_vars = [
        "BI_ACCESS_TOKEN_URL",
        "BI_CLIENT_ID",
        "BI_CLIENT_SECRET_KEY",
        "BI_END_POINT_URL",
    ]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        return 1

    token_url = os.environ["BI_ACCESS_TOKEN_URL"]
    client_id = os.environ["BI_CLIENT_ID"]
    client_secret = os.environ["BI_CLIENT_SECRET_KEY"]
    endpoint_url = os.environ["BI_END_POINT_URL"]

    try:
        access_token = get_access_token(token_url, client_id, client_secret)
        result = call_bi_endpoint(endpoint_url, access_token)
        print(result)
    except requests.HTTPError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
