import os

import pandas as pd


def fetch_oracle(query: str) -> pd.DataFrame:
    """Run a query against Oracle using ORACLE_USER/ORACLE_PASSWORD/ORACLE_DSN env vars.

    ORACLE_DSN is host:port/service_name, or a TNS alias if TNS_ADMIN is set.
    Credentials are never read from CLI args so they don't end up in shell history.
    """
    import oracledb  # imported lazily so file-based usage doesn't require it

    user = os.environ["ORACLE_USER"]
    password = os.environ["ORACLE_PASSWORD"]
    dsn = os.environ["ORACLE_DSN"]

    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        return pd.read_sql(query, conn)
