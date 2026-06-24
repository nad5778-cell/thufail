"""
BI reports integration client.

Authenticates against the OAuth2 token endpoint using the client_credentials
grant, then calls the BI end point with the resulting bearer token.
"""

import sys
from typing import Optional

import requests

BI_ACCESS_TOKEN_URL = "https://bicloud.mrhealthtech.com/ords/montools/oauth/token"
BI_CLIENT_ID = "WhYOC-x79mgi1J0QEI6T-Q.."
BI_CLIENT_SECRET_KEY = "6C42jLcCTvzsipYfy9eROA.."
BI_END_POINT_URL = "https://bicloud.mrhealthtech.com/ords/montools/metlife_ssp_integration/par"


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
    try:
        access_token = get_access_token(BI_ACCESS_TOKEN_URL, BI_CLIENT_ID, BI_CLIENT_SECRET_KEY)
        result = call_bi_endpoint(BI_END_POINT_URL, access_token)
        print(result)
    except requests.HTTPError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
