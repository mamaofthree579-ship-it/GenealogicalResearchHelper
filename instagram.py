
#!/usr/bin/env python3
"""
Instagram Reel comment evidence processor.

Input:
  A JSON or CSV comment export obtained through an authorized method.

Output:
  evidence_log.csv
  review_summary.txt

This script does not scrape Instagram or bypass login/access controls.
It preserves source text and treats automated flags as review suggestions.
"""

import csv
import json
import re
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone

REEL_URL = (
    "https://www.instagram.com/reel/"
    "Dew-Lw5JurI/"
)

OUTPUT_CSV = Path("evidence_log.csv")
OUTPUT_REPORT = Path("review_summary.txt")

# Conservative screening cues, not a complete harassment detector.
PATTERNS = {
    "possible_threat": [
        r"\bI'll kill you\b",
        r"\bI will kill you\b",
        r"\bI'll hurt you\b",
        r"\bI will hurt you\b",
        r"\bfind where you live\b",
    ],
    "possible_targeted_abuse": [
        r"\bgo die\b",
        r"\byou deserve to die\b",
        r"\bworthless piece of\b",
    ],
    "possible_coordinated_targeting": [
        r"\bgo spam\b",
        r"\bgo after them\b",
        r"\beveryone report this person\b",
    ],
}


def load_export(path):
    """Load a supplied JSON or CSV export."""
    suffix = path.suffix.lower()

    if suffix == ".json":
        with path.open(encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in ("comments", "data", "items"):
                if isinstance(data.get(key), list):
                    return data[key]

        raise ValueError(
            "JSON must contain a comment list or a "
            "'comments', 'data', or 'items' list."
        )

    if suffix == ".csv":
        with path.open(
            encoding="utf-8-sig", newline=""
        ) as f:
            return list(csv.DictReader(f))

    raise ValueError("Input must be .json or .csv")


def first_value(item, *keys):
    """Return the first available source field."""
    for key in keys:
        value = item.get(key)
        if value is not None and value != "":
            return value
    return ""


def normalize(item, index):
    """
    Map common export field names into a consistent schema.
    Inspect and adapt this mapping for your provider's format.
    """
    text = first_value(
        item, "text", "comment_text", "content", "message"
    )

    username = first_value(
        item, "username", "user_name", "owner_username",
        "author", "user"
    )

    # Some exporters return a nested author object.
    if isinstance(username, dict):
        username = first_value(
            username, "username", "name", "handle"
        )

    timestamp = first_value(
        item, "timestamp", "created_at", "created_time",
        "date", "time"
    )

    comment_id = first_value(
        item, "id", "comment_id", "pk"
    )

    parent_id = first_value(
        item, "parent_id", "parent_comment_id",
        "reply_to_id"
    )

    permalink = first_value(
        item, "permalink", "url", "comment_url"
    )

    # Replies may be nested. Preserve their original structure
    # in the source export; process nested replies separately
    # if the provider returns them in a "replies" array.
    reply_items = item.get("replies", [])
    if not isinstance(reply_items, list):
        reply_items = []

    # Stable fallback identifier derived from source fields.
    if not comment_id:
        source_key = json.dumps(
            {
                "username": username,
                "text": text,
                "timestamp": timestamp,
                "parent_id": parent_id,
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        comment_id = hashlib.sha256(
            source_key.encode("utf-8")
        ).hexdigest()[:16]

    return {
        "evidence_id": f"E{index:05d}",
        "reel_url": REEL_URL,
        "comment_id": str(comment_id),
        "username": str(username),
        "comment_text": str(text),
        "timestamp_source": str(timestamp),
        "parent_comment_id": str(parent_id),
        "comment_url": str(permalink),
        "reply_count_in_source": len(reply_items),
        "screening_flags": "",
        "review_status": "Unreviewed",
    }


def screen(text):
    """Flag matching text for human review."""
    flags = []

    for category, patterns in PATTERNS.items():
        if any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        ):
            flags.append(category)

    return flags or ["manual_review"]


def main():
    parser = argparse.ArgumentParser(
        description="Process an authorized comment export."
    )
    parser.add_argument(
        "input_file",
        help="Path to the supplied JSON or CSV export",
    )
    args = parser.parse_args()

    source = Path(args.input_file)
    if not source.is_file():
        raise FileNotFoundError(source)

    raw_items = load_export(source)
    records = []

    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue

        record = normalize(item, index)
        text = record["comment_text"]
        record["screening_flags"] = ";".join(screen(text))
        records.append(record)

        # Flatten nested replies into individual evidence rows.
        replies = item.get("replies", [])
        if isinstance(replies, list):
            for reply in replies:
                if not isinstance(reply, dict):
                    continue

                reply_record = normalize(
                    reply, len(records) + 1
                )
                if not reply_record["parent_comment_id"]:
                    reply_record["parent_comment_id"] = (
                        record["comment_id"]
                    )
                reply_record["screening_flags"] = ";".join(
                    screen(reply_record["comment_text"])
                )
                records.append(reply_record)

    fields = [
        "evidence_id",
        "reel_url",
        "comment_id",
        "username",
        "comment_text",
        "timestamp_source",
        "parent_comment_id",
        "comment_url",
        "reply_count_in_source",
        "screening_flags",
        "review_status",
    ]

    with OUTPUT_CSV.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    flagged = sum(
        "manual_review" not in r["screening_flags"]
        for r in records
    )

    # Hash the source file to help document which export
    # was processed. This does not prove source authenticity.
    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    with OUTPUT_REPORT.open("w", encoding="utf-8") as f:
        f.write("INSTAGRAM COMMENT EVIDENCE PROCESSING REPORT\n")
        f.write(f"Reel: {REEL_URL}\n")
        f.write(f"Source filename: {source.name}\n")
        f.write(f"Source SHA-256: {digest}\n")
        f.write(
            "Processed UTC: "
            + datetime.now(timezone.utc).isoformat()
            + "\n"
        )
        f.write(f"Records processed: {len(records)}\n")
        f.write(f"Records with screening flags: {flagged}\n")
        f.write(
            "\nFlags are preliminary screening cues, not findings "
            "of harassment or legal violations.\n"
        )
        f.write(
            "Verify the source export, timestamps, reply links, "
            "and context against the original Reel.\n"
        )

    print(f"Processed {len(records)} records.")
    print(f"Evidence CSV: {OUTPUT_CSV.resolve()}")
    print(f"Review report: {OUTPUT_REPORT.resolve()}")


if __name__ == "__main__":
    main()
