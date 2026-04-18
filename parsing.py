from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from helpers import parse_time
from models import RawEntry
from text_features import is_url_only_title


def parse_entries(path: Path) -> list[RawEntry]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    entries: list[RawEntry] = []

    for outer in soup.select("div.outer-cell"):
        header = outer.select_one("div.header-cell")
        body = outer.select_one("div.content-cell.mdl-cell--6-col.mdl-typography--body-1")
        if not header or not body:
            continue

        product = header.get_text(" ", strip=True)
        text = body.get_text("\n", strip=True)
        links = body.find_all("a")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue

        if lines[0].startswith("Watched"):
            action = "Watched"
        elif lines[0].startswith("Viewed"):
            action = "Viewed"
        else:
            continue

        title = links[0].get_text(" ", strip=True) if links else ""
        channel = links[1].get_text(" ", strip=True) if len(links) >= 2 else ""
        watched_at = ""
        parse_flags: list[str] = []

        first = lines[0]
        if first.startswith("Watched"):
            title = title or first.removeprefix("Watched").strip()
        elif first.startswith("Viewed"):
            title = title or first.removeprefix("Viewed").strip()

        parseable_time_lines = [line for line in lines if parse_time(line)]
        if len(parseable_time_lines) == 1 and parse_time(lines[-1]):
            watched_at = parseable_time_lines[0]
            parse_flags.append("single_tail_timestamp")
        else:
            continue

        if len(lines) >= 2 and not channel and not parse_time(lines[1]):
            channel = lines[1]
        if not channel:
            parse_flags.append("missing_channel")
        if is_url_only_title(title):
            parse_flags.append("url_or_empty_title")

        if title and watched_at:
            entries.append(
                {
                    "product": product,
                    "action": action,
                    "title": title,
                    "channel": channel,
                    "time": watched_at,
                    "parse_flags": parse_flags,
                }
            )

    return entries


def filter_rows_by_years(rows: list[RawEntry], years: list[int] | None) -> list[RawEntry]:
    if not years:
        return rows

    selected_years = set(years)
    return [row for row in rows if (dt := parse_time(row["time"])) and dt.year in selected_years]


def is_watched_youtube_record(row: RawEntry) -> bool:
    return row.get("product") == "YouTube" and row.get("action") == "Watched"


def available_years(rows: list[RawEntry]) -> list[int]:
    years = set()
    for row in rows:
        dt = parse_time(row["time"])
        if dt:
            years.add(dt.year)
    return sorted(years)
