import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from da_client import API, get_access_token

load_dotenv()

DATA_FILE = Path("data.json")
DRY_RUN = os.environ.get("DRY_RUN") == "1"

# Required by the API when is_mature is true: "strict" or "moderate".
MATURE_LEVEL = os.environ.get("DA_MATURE_LEVEL", "strict")
# Optional comma-separated gallery folder UUIDs and group/group-folder pairs.
GALLERY_IDS = [g for g in os.environ.get("DA_GALLERY_IDS", "").split(",") if g]
GROUPS = [g for g in os.environ.get("DA_GROUPS", "").split(",") if g]
GROUP_FOLDERS = [g for g in os.environ.get("DA_GROUP_FOLDERS", "").split(",") if g]

MAX_TAGS = 30


def build_payload(item):
    is_mature = not item["is_sfw"]
    payload = {
        "itemid": item["da_stash_id"],
        "is_mature": str(is_mature).lower(),
        "feature": str(item["premium_level"] == "NONE").lower(),
        "display_resolution": 5,
        "allow_free_download": "false",
        "is_ai_generated": "true",
    }
    if is_mature:
        payload["mature_level"] = MATURE_LEVEL
        payload["mature_classification[]"] = ["sexual"]

    tags = [t.strip() for t in item["da_tags"].split(",") if t.strip()]
    payload["tags[]"] = tags[:MAX_TAGS]
    if GALLERY_IDS:
        payload["galleryids[]"] = GALLERY_IDS
    if GROUPS:
        payload["groups[]"] = GROUPS
        payload["group_folders[]"] = GROUP_FOLDERS
    return payload


def save(items):
    DATA_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    items = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    item = next(
        (i for i in items if i.get("da_stash_id") and not i.get("published_deviationid")),
        None,
    )
    if item is None:
        print("Nothing left to publish.")
        return

    payload = build_payload(item)
    print(f"Publishing {item['filename']} ({item['character']}) stash id {item['da_stash_id']}")
    if DRY_RUN:
        print(json.dumps(payload, indent=2))
        return

    token = get_access_token(os.environ["DA_CLIENT_ID"], os.environ["DA_CLIENT_SECRET"])
    r = requests.post(
        f"{API}/stash/publish",
        headers={"Authorization": f"Bearer {token}"},
        data=payload,
        timeout=60,
    )
    body = r.json()

    if r.ok:
        item["published_deviationid"] = body["deviationid"]
        item["published_url"] = body["url"]
        item["published_at"] = datetime.now(timezone.utc).isoformat()
        save(items)
        print(f"Published: {body['url']}")
    elif body.get("error_code") == 9:
        # Already published (e.g. manually); mark done so the queue moves on.
        item["published_deviationid"] = "already_published"
        item["published_at"] = datetime.now(timezone.utc).isoformat()
        save(items)
        print("Already published; marked as done.")
    else:
        print(f"Publish failed: {r.status_code} {body}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
