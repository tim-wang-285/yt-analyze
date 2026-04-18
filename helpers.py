from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime


def month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def parse_time(text: str) -> datetime | None:
    text = text.strip()
    text = re.sub(r"GMT([+-]\d{2}):(\d{2})$", r"\1\2", text)
    for candidate in (text, text.replace(",", "")):
        try:
            dt = parsedate_to_datetime(candidate)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            pass
    return None


def clean_title(title: str) -> str:
    title = re.sub(r"https?://\S+", " ", title)
    title = re.sub(r"www\.\S+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def record_datetime(record: dict) -> datetime | None:
    parsed = record.get("parsed_time")
    if parsed:
        try:
            return datetime.fromisoformat(parsed)
        except Exception:
            pass
    time_value = record.get("time", "")
    if time_value:
        return parse_time(time_value)
    return None


def build_title_counts(records: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}

    for record in records:
        raw_title = (record.get("title") or "").strip()
        cleaned_title = clean_title(raw_title)
        if not cleaned_title:
            continue

        key = cleaned_title.casefold()
        entry = grouped.setdefault(
            key,
            {
                "title": cleaned_title,
                "raw_titles": Counter(),
                "count": 0,
            },
        )
        entry["count"] += 1
        entry["raw_titles"][raw_title or cleaned_title] += 1

    title_counts = []
    for entry in grouped.values():
        display_title = sorted(
            entry["raw_titles"].items(),
            key=lambda item: (-item[1], len(item[0]), item[0]),
        )[0][0]
        title_counts.append(
            {
                "title": display_title,
                "count": entry["count"],
            }
        )

    title_counts.sort(key=lambda item: (-item["count"], item["title"]))
    return title_counts


def stable_title_sample(title_counts: list[dict], seed: str, limit: int = 5) -> list[str]:
    ranked = sorted(
        title_counts,
        key=lambda item: (
            hashlib.sha256(f"{seed}\n{item['title']}".encode("utf-8")).hexdigest(),
            -item["count"],
            item["title"],
        ),
    )
    return [item["title"] for item in ranked[:limit]]


def build_channel_title_groups(records: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}

    for record in records:
        channel = (record.get("channel") or "").strip()
        if not channel:
            continue

        entry = grouped.setdefault(
            channel,
            {
                "channel": channel,
                "count": 0,
                "titles": [],
            },
        )
        entry["count"] += 1

        raw_title = (record.get("title") or "").strip()
        cleaned_title = clean_title(raw_title)
        if cleaned_title:
            entry["titles"].append(raw_title or cleaned_title)

    channels = []
    for entry in grouped.values():
        channels.append(
            {
                "channel": entry["channel"],
                "count": entry["count"],
                "titles": sorted(entry["titles"]),
            }
        )

    channels.sort(key=lambda item: (-item["count"], item["channel"]))
    return channels
