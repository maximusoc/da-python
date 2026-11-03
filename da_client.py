import os
from pathlib import Path

import requests

API = "https://www.deviantart.com/api/v1/oauth2"
TOKEN_URL = "https://www.deviantart.com/oauth2/token"
REFRESH_TOKEN_FILE = Path(".refresh_token")


def load_refresh_token():
    # A rotated token saved locally takes priority over the (possibly stale) env var.
    if REFRESH_TOKEN_FILE.exists():
        return REFRESH_TOKEN_FILE.read_text().strip()
    return os.environ["DA_REFRESH_TOKEN"]


def get_access_token(client_id, client_secret):
    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": load_refresh_token(),
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    # DeviantArt refresh tokens are single-use; keep the new one.
    REFRESH_TOKEN_FILE.write_text(data["refresh_token"])
    return data["access_token"]
