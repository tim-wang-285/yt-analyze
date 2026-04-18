from __future__ import annotations

from collections import Counter

from models import RawEntry, SemanticRecord
from helpers import clean_title, parse_time
from text_features import guess_language, has_semantic_title_signal, normalize_semantic_text


def build_semantic_records(rows: list[RawEntry]) -> tuple[list[SemanticRecord], dict]:
    records: list[SemanticRecord] = []
    skipped_counts: Counter[str] = Counter()
    skipped_examples: list[dict] = []

    def note_skip(reason: str, row: RawEntry) -> None:
        skipped_counts[reason] += 1
        if len(skipped_examples) < 20:
            skipped_examples.append(
                {
                    "reason": reason,
                    "title": row.get("title", ""),
                    "channel": row.get("channel", ""),
                    "time": row.get("time", ""),
                }
            )

    for row in rows:
        if row["product"] != "YouTube" or row["action"] != "Watched":
            continue

        cleaned_title = clean_title(row["title"])
        if not cleaned_title:
            note_skip("url_or_empty_title", row)
            continue
        if not has_semantic_title_signal(row["title"]):
            note_skip("low_information_title", row)
            continue

        dt = parse_time(row["time"])
        if not dt:
            note_skip("invalid_time", row)
            continue

        semantic_text = normalize_semantic_text(row["title"], row["channel"])
        if not semantic_text.strip():
            note_skip("empty_semantic_text", row)
            continue

        records.append(
            {
                "product": row["product"],
                "action": row["action"],
                "title": row["title"],
                "clean_title": cleaned_title,
                "channel": row["channel"],
                "time": row["time"],
                "parsed_time": dt.isoformat(timespec="seconds"),
                "semantic_text": semantic_text,
                "language_hint": guess_language(semantic_text),
            }
        )

    return records, {
        "counts": dict(sorted(skipped_counts.items())),
        "examples": skipped_examples,
    }
