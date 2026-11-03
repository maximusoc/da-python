import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://www.deviantart.com/api/v1/oauth2"
TOKEN_URL = "https://www.deviantart.com/oauth2/token"
OUTPUT_FILE = "deviations.json"
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


def get_username(headers):
    r = requests.get(f"{API}/user/whoami", headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["username"]


def fetch_all_deviations(headers, username):
    deviations = []
    offset = 0
    while True:
        r = requests.get(
            f"{API}/gallery/all",
            headers=headers,
            params={
                "username": username,
                "limit": 24,
                "offset": offset,
                "mature_content": "true",
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        deviations.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        offset = data["next_offset"]
    return deviations


def simplify(d):
    return {
        "deviationid": d.get("deviationid"),
        "url": d.get("url"),
        "title": d.get("title"),
        "stats": d.get("stats"),
        "published_time": d.get("published_time"),
        "is_premium": bool(d.get("tier")),
    }


def main():
    client_id = os.environ["DA_CLIENT_ID"]
    client_secret = os.environ["DA_CLIENT_SECRET"]

    token = get_access_token(client_id, client_secret)
    headers = {"Authorization": f"Bearer {token}"}
    username = get_username(headers)
    deviations = [simplify(d) for d in fetch_all_deviations(headers, username)]

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "username": username,
        "count": len(deviations),
        "deviations": deviations,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(deviations)} deviations for {username} to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
