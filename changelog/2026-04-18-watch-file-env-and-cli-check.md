`WATCH_FILE` now loads from `.env` or the process environment instead of being hard-coded in `config.py`, and the CLI now exits early with a clear error if that path does not exist or is not a file.
