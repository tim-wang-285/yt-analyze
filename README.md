# yt-analyze

Local-first analysis for Google Takeout YouTube watch history.

The recent refactor split the pipeline into small, readable modules with clearer boundaries: parsing, record shaping, embeddings, topic construction, reporting, and CLI/config glue. The behavior is still the same core model: parse Takeout HTML locally, analyze only `YouTube` + `Watched` entries, and persist semantic outputs to disk as a high-level JSON summary plus yearly JSON/Markdown results.

## What It Does

- Parses Google Takeout `watch-history.html`
- Distinguishes watch entries from other activity such as `Viewed`
- Requires explicit scope selection with `--year ...` or `--all`
- Prints watch-only activity stats for the selected scope
- Builds semantic records from `title + channel`
- Runs multilingual sentence-transformer embeddings locally with cache reuse
- Clusters recurring watch themes into topics
- Persists semantic topic outputs as high-level JSON plus yearly JSON/Markdown

## Repo Layout

The codebase is now intentionally flat at the repo root so each module is easy to find and inspect.

### CLI And Orchestration

- `yt-analyze.py`: CLI entrypoint. Parses arguments, loads Takeout rows, enforces year selection, prints help when no scope is chosen, and kicks off the semantic pipeline.
- `analysis_pipeline.py`: High-level orchestration for the selected scope. Prints watch/non-watch statistics, builds semantic records, runs embeddings and topic clustering, and writes all persisted outputs.
- `config.py`: Central home for file paths, default model names, cache/output locations, and term-labeling constants.

### Input And Record Shaping

- `parsing.py`: Extracts structured entries from the Google Takeout HTML file, detects parseable timestamps, recovers missing channel names when possible, and exposes helpers for year filtering and watch detection.
- `records.py`: Converts raw parsed rows into semantic records ready for embedding, while tracking skipped-record reasons and example exclusions.
- `models.py`: TypedDict models for raw entries, semantic records, and topic-shaped output data.
- `helpers.py`: Shared utilities for timestamp parsing, title cleanup, grouping, stable title sampling, and title/channel aggregation helpers used across reports.

### Text And Topic Logic

- `text_features.py`: Tokenization, phrase extraction, language guessing, label-term extraction, stopword filtering, and topic-label merge helpers.
- `topics.py`: Topic clustering and consolidation. Builds communities from embeddings, labels topics, merges overlapping labels with safeguards, computes representative titles, timelines, and per-topic summaries.

### Embeddings And Reporting

- `embeddings.py`: Embedding cache management and local sentence-transformer execution. Reuses cached vectors when the semantic text digest and model match.
- `reporting.py`: Builds yearly topic summaries and writes the high-level JSON plus the yearly JSON/Markdown outputs.

### Supporting Files

- `outputs/`: Generated JSON and Markdown artifacts.
- `.cache/yt-analyze/`: Cached embedding vectors, record manifests, and metadata.
- `changelog/`: Running notes for meaningful pipeline changes.

## Pipeline Flow

1. `parsing.py` reads the Takeout HTML and returns structured rows.
2. `yt-analyze.py` applies `--year ...` or `--all` scope selection.
3. `analysis_pipeline.py` prints activity and watch-only statistics.
4. `records.py` converts eligible watch rows into semantic records.
5. `embeddings.py` loads cached vectors or computes new embeddings locally.
6. `topics.py` clusters records, labels topics, and merges overlapping topic groups.
7. `reporting.py` writes the high-level JSON output and the yearly JSON/Markdown outputs.

## Outputs

The semantic pipeline persists these files:

- `outputs/results.json`
- `outputs/results_by_year.json`
- `outputs/results_by_year.md`

The high-level JSON includes topic labels, sizes, time ranges, timelines, representative channel groups, raw title counts, and excluded-record summaries. The yearly outputs include yearly topic breakdowns with representative channel groups in both JSON and Markdown, while raw title counts stay in JSON only.

## Usage

Set `WATCH_FILE` in `.env` to point at your Takeout `watch-history.html`, then run the analyzer:

```bash
uv run yt-analyze.py --all
```

Limit analysis to specific years:

```bash
uv run yt-analyze.py --year 2025 2026
```

Useful flags:

- `--year 2025 2026`: only analyze the listed years
- `--all`: analyze all available years in the Takeout file
- `--embedding-model`: override the sentence-transformers model
- `--cache-dir`: override the embedding cache directory
- `--cpu-embed`: force embeddings onto CPU instead of using sentence-transformers default device selection
- `--results-output`: override the high-level semantic results JSON path
- `--results-by-year-output`: override the yearly semantic results JSON path
- `--topic-threshold`: adjust community-detection similarity threshold

If neither `--year ...` nor `--all` is provided, the script prints help, lists discovered years from the Takeout file, and exits.
If `WATCH_FILE` is missing or points to a non-file path, the CLI exits immediately with a config error.

## Notes

- The pipeline stays local-first by default.
- Provide your own Google Takeout `watch-history.html`; the repo does not ship sample personal history data.
- Semantic outputs are persisted as a high-level JSON file plus yearly JSON/Markdown files.
- Non-watch interactions are parsed for activity accounting but excluded from watch statistics and semantic outputs.
- Embeddings are cached under `.cache/yt-analyze/` to avoid recomputation.
