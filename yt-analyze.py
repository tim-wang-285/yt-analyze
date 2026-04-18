from __future__ import annotations

import argparse
from pathlib import Path

from analysis_pipeline import print_scope_stats, run_semantic_step
from config import (
    DEFAULT_CACHE_DIR,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_RESULTS_BY_YEAR_OUTPUT,
    DEFAULT_RESULTS_OUTPUT,
    WATCH_FILE,
)
from parsing import available_years, filter_rows_by_years, parse_entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze YouTube watch history.")
    parser.add_argument(
        "--year",
        "--years",
        dest="years",
        type=int,
        nargs="+",
        help="Space-delimited list of years to include in the analysis.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all available years from the parsed watch history.",
    )
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="Sentence-transformers model used for semantic embeddings.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Directory used to cache semantic embeddings and metadata.",
    )
    parser.add_argument(
        "--cpu-embed",
        action="store_true",
        help="Force sentence-transformer embeddings to run on CPU.",
    )
    parser.add_argument(
        "--results-output",
        "--topics-output",
        type=Path,
        default=DEFAULT_RESULTS_OUTPUT,
        help="JSON file where the high-level semantic topic summary is written.",
    )
    parser.add_argument(
        "--results-by-year-output",
        "--topic-yearly-output",
        type=Path,
        default=DEFAULT_RESULTS_BY_YEAR_OUTPUT,
        help="JSON file where top topics by year are written.",
    )
    parser.add_argument(
        "--topic-threshold",
        type=float,
        default=0.60,
        help="Cosine similarity threshold used to form topic communities.",
    )
    args = parser.parse_args()

    if not WATCH_FILE.exists():
        parser.error(
            f"WATCH_FILE does not exist: {WATCH_FILE}. Set WATCH_FILE in .env or export it in the environment."
        )
    if not WATCH_FILE.is_file():
        parser.error(f"WATCH_FILE is not a file: {WATCH_FILE}")

    all_rows = parse_entries(WATCH_FILE)
    years_in_data = available_years(all_rows)
    if not args.all and not args.years:
        parser.print_help()
        available_years_text = " ".join(str(year) for year in years_in_data) if years_in_data else "(none found)"
        print(f"\nAvailable years: {available_years_text}")
        raise SystemExit(1)

    selected_years = None if args.all else sorted(set(args.years or []))
    rows = filter_rows_by_years(all_rows, selected_years)
    watched_rows, _ = print_scope_stats(rows, selected_years, args.all)

    run_semantic_step(
        watched_rows,
        model_name=args.embedding_model,
        cache_dir=args.cache_dir,
        embedding_device="cpu" if args.cpu_embed else None,
        results_output=args.results_output,
        results_by_year_output=args.results_by_year_output,
        topic_threshold=args.topic_threshold,
    )

if __name__ == "__main__":
    main()
