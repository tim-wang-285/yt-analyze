# yt-analyze

## Motivation
If YouTube knows what you're watching, you should know too.

## Setup

Clone the repo, fill in the `WATCH_FILE` path, and run it with `uv`.

```bash
git clone https://github.com/tim-wang-285/yt-analyze.git
cd yt-analyze
touch .env
```

Set `WATCH_FILE` in `.env` to your Google Takeout YouTube `watch-history.html` file:

```dotenv
WATCH_FILE=/absolute/path/to/watch-history.html
```

Install dependencies and run:

```bash
uv sync
uv run python yt-analyze.py --all
```

## What It Does

`yt-analyze` parses a Google Takeout YouTube watch history HTML file, filters to `YouTube` + `Watched` entries, embeds titles and channel context with `sentence-transformers`, groups related watches into semantic topics, and writes topic summaries to disk.

The CLI requires one of these scope options:

- `--all` to analyze every year found in the file
- `--year ...` or `--years ...` to analyze only specific years

If you run the script without either option, it prints help, lists the available years found in the watch history, and exits.

## Requirements

- Python `3.11+`
- A Google Takeout `watch-history.html` file
- `uv` for the default workflow, or `pip` if you prefer

If the path does not exist or is not a file, the CLI exits with an error.

## Usage

Analyze all available years:

```bash
uv run python yt-analyze.py --all
```

Analyze only specific years:

```bash
uv run python yt-analyze.py --year 2023 2024
```

Show CLI help:

```bash
uv run python yt-analyze.py --help
```

Useful options:

- `--embedding-model`: override the default sentence-transformers model
- `--cache-dir`: change the embedding cache directory
- `--cpu-embed`: force embeddings onto CPU
- `--results-output`: change the main JSON output path
- `--results-by-year-output`: change the yearly JSON output path
- `--topic-threshold`: change the cosine-similarity threshold used for topic communities

## Outputs

Running the analyzer writes:

- `outputs/results.json`
- `outputs/results_by_year.json`
- `outputs/results_by_year.md`

The main JSON includes overall topic summaries, excluded-record counts, excluded-record examples, and per-topic metadata. The yearly JSON and Markdown files summarize the top topics by year.

## Notes

- Only `YouTube` + `Watched` entries are included in the semantic analysis.
- Other parsed interactions are counted for scope statistics but excluded from topic outputs.
- Embeddings are cached and reused when the input semantic text and embedding model match.
- The first run may take longer because the sentence-transformers model may need to be downloaded.
- The parser expects the Google Takeout HTML watch-history format, not a JSON export.

## Using pip Instead of uv

Create a virtual environment, install from `requirements.txt`, and run the script directly:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python yt-analyze.py --all
```
