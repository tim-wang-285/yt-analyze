from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from helpers import (
    build_channel_title_groups,
    build_title_counts,
    month_key,
    record_datetime,
)


def _append_markdown_kv(lines: list[str], key: str, value: object, indent: int = 0) -> None:
    prefix = "  " * indent
    if isinstance(value, list):
        lines.append(f"{prefix}- **{key}**:")
        _append_markdown_list(lines, value, indent + 1)
        return
    if isinstance(value, dict):
        lines.append(f"{prefix}- **{key}**:")
        _append_markdown_dict(lines, value, indent + 1)
        return
    lines.append(f"{prefix}- **{key}**: {value}")


def _append_markdown_dict(lines: list[str], data: dict, indent: int = 0) -> None:
    for key, value in data.items():
        _append_markdown_kv(lines, key, value, indent)


def _append_markdown_list(lines: list[str], items: list[object], indent: int = 0) -> None:
    prefix = "  " * indent
    for item in items:
        if isinstance(item, dict):
            label = item.get("channel") or item.get("month")
            if label:
                lines.append(f"{prefix}- **{label}**")
                for key, value in item.items():
                    if key in {"channel", "month"}:
                        continue
                    _append_markdown_kv(lines, key, value, indent + 1)
            else:
                lines.append(f"{prefix}-")
                _append_markdown_dict(lines, item, indent + 1)
            continue
        if isinstance(item, list):
            lines.append(f"{prefix}-")
            _append_markdown_list(lines, item, indent + 1)
            continue
        lines.append(f"{prefix}- {item}")


def build_topic_timeline(topic_records: list[dict]) -> dict:
    monthly_counts: Counter[str] = Counter()
    yearly_counts: Counter[str] = Counter()
    times: list[datetime] = []

    for record in topic_records:
        dt = record_datetime(record)
        if not dt:
            continue
        times.append(dt)
        monthly_counts[month_key(dt)] += 1
        yearly_counts[str(dt.year)] += 1

    if not times:
        return {
            "first_seen": None,
            "last_seen": None,
            "peak_month": None,
            "monthly_counts": [],
            "yearly_counts": [],
        }

    times.sort()
    peak_month = None
    if monthly_counts:
        peak_month = max(monthly_counts.items(), key=lambda item: (item[1], item[0]))[0]

    return {
        "first_seen": times[0].isoformat(timespec="seconds"),
        "last_seen": times[-1].isoformat(timespec="seconds"),
        "peak_month": peak_month,
        "monthly_counts": [
            {"month": month, "count": count}
            for month, count in sorted(monthly_counts.items())
        ],
        "yearly_counts": [
            {"year": year, "count": count}
            for year, count in sorted(yearly_counts.items())
        ],
    }


def build_topic_yearly_report(topic_report: dict) -> dict:
    yearly_topics: dict[str, dict[int, dict]] = defaultdict(dict)

    for topic in topic_report["topics"]:
        per_year_monthly_counts: dict[str, Counter[str]] = defaultdict(Counter)
        per_year_counts: Counter[str] = Counter()
        per_year_first_seen: dict[str, datetime] = {}
        per_year_last_seen: dict[str, datetime] = {}

        for member in topic["members"]:
            dt = record_datetime(member)
            if not dt:
                continue

            year = str(dt.year)
            month = month_key(dt)
            per_year_counts[year] += 1
            per_year_monthly_counts[year][month] += 1

            if year not in per_year_first_seen or dt < per_year_first_seen[year]:
                per_year_first_seen[year] = dt
            if year not in per_year_last_seen or dt > per_year_last_seen[year]:
                per_year_last_seen[year] = dt

        for year, count in per_year_counts.items():
            year_members = [
                member
                for member in topic["members"]
                if (dt := record_datetime(member)) is not None and str(dt.year) == year
            ]
            title_counts = build_title_counts(year_members)
            representative_channels = build_channel_title_groups(year_members)
            yearly_topics[year][topic["topic_id"]] = {
                "topic_id": topic["topic_id"],
                "label": topic["label"],
                "size": topic["size"],
                "count": count,
                "first_seen": per_year_first_seen[year].isoformat(timespec="seconds"),
                "last_seen": per_year_last_seen[year].isoformat(timespec="seconds"),
                "monthly_counts": [
                    {"month": month, "count": month_count}
                    for month, month_count in sorted(per_year_monthly_counts[year].items())
                ],
                "title_counts": title_counts,
                "representative_channels": representative_channels,
            }

    years = []
    for year in sorted(yearly_topics):
        topics = sorted(
            yearly_topics[year].values(),
            key=lambda item: (-item["count"], item["label"], item["topic_id"]),
        )[:50]
        years.append(
            {
                "year": year,
                "topic_count": len(yearly_topics[year]),
                "topics": topics,
            }
        )

    return {
        "generated_at": topic_report["generated_at"],
        "model_name": topic_report["model_name"],
        "topic_count": topic_report["topic_count"],
        "year_count": len(years),
        "years": years,
    }


def save_semantic_topic_outputs(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def save_topic_yearly_outputs(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = output_path.with_suffix(".md")
    lines = [
        "# Semantic Topic Yearly Summary",
        "",
        f"- **generated_at**: {report['generated_at']}",
        f"- **model_name**: {report['model_name']}",
        f"- **topic_count**: {report['topic_count']}",
        f"- **year_count**: {report['year_count']}",
        "",
    ]

    for year in sorted(report["years"], key=lambda item: item["year"], reverse=True):
        lines.extend(
            [
                f"## Year {year['year']}",
                f"- **topic_count**: {year['topic_count']}",
                "",
            ]
        )
        for topic in year["topics"]:
            lines.append(f"### {topic['label']}")
            _append_markdown_kv(lines, "count", topic["count"])
            _append_markdown_kv(lines, "size", topic["size"])
            _append_markdown_kv(lines, "first_seen", topic["first_seen"])
            _append_markdown_kv(lines, "last_seen", topic["last_seen"])
            _append_markdown_kv(lines, "monthly_counts", topic["monthly_counts"])
            _append_markdown_kv(
                lines,
                "representative_channels",
                topic.get("representative_channels", [])[:5],
            )
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
