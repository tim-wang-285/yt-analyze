from __future__ import annotations

from datetime import datetime
from pathlib import Path

from embeddings import embed_semantic_records
from parsing import is_watched_youtube_record
from records import build_semantic_records
from reporting import (
    build_topic_yearly_report,
    save_semantic_topic_outputs,
    save_topic_yearly_outputs,
)
from topics import build_topic_report


def print_scope_stats(rows: list[dict], selected_years: list[int] | None, all_years: bool) -> tuple[list[dict], list[dict]]:
    watched_rows = [row for row in rows if is_watched_youtube_record(row)]
    non_watched_rows = [row for row in rows if not is_watched_youtube_record(row)]

    print(f"Parsed entries in scope: {len(rows)}")
    print(f"Watched YouTube entries analyzed: {len(watched_rows)}")
    print(f"Other interactions excluded from statistics: {len(non_watched_rows)}")
    if all_years:
        print("Selected years: all")
    elif selected_years:
        print(f"Selected years: {' '.join(str(year) for year in selected_years)}")

    return watched_rows, non_watched_rows


def run_semantic_step(
    rows: list[dict],
    model_name: str,
    cache_dir: Path,
    embedding_device: str | None,
    results_output: Path,
    results_by_year_output: Path,
    topic_threshold: float,
) -> None:
    records, skipped_meta = build_semantic_records(rows)
    if not records:
        empty_topic_report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model_name": model_name,
            "threshold": topic_threshold,
            "record_count": 0,
            "topic_count": 0,
            "noise_count": 0,
            "excluded_records": skipped_meta["counts"],
            "excluded_examples": skipped_meta["examples"],
            "topics": [],
            "noise": [],
        }
        save_semantic_topic_outputs(empty_topic_report, results_output)
        save_topic_yearly_outputs(
            {
                "generated_at": empty_topic_report["generated_at"],
                "model_name": model_name,
                "topic_count": 0,
                "year_count": 0,
                "years": [],
            },
            results_by_year_output,
        )
        print("\nSemantic topics: no eligible YouTube watch entries found.")
        return

    vectors = embed_semantic_records(
        records,
        model_name=model_name,
        cache_dir=cache_dir,
        device=embedding_device,
    )
    topic_report = build_topic_report(
        records,
        vectors,
        model_name=model_name,
        threshold=topic_threshold,
    )
    topic_report["excluded_records"] = skipped_meta["counts"]
    topic_report["excluded_examples"] = skipped_meta["examples"]
    topic_yearly_report = build_topic_yearly_report(topic_report)
    save_semantic_topic_outputs(topic_report, results_output)
    save_topic_yearly_outputs(topic_yearly_report, results_by_year_output)
    print("\nSemantic topic reports written:")
    print(f"  results: {results_output}")
    print(f"  results_by_year: {results_by_year_output}")
