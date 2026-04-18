# 2026-04-18: Split the analysis pipeline into stage modules

- reduced `yt-analyze.py` to CLI orchestration and delegated work into parsing, records, text feature, embeddings, topics, and analysis pipeline modules
- added lightweight typed models for raw entries, semantic records, and topic data
- preserved the local-first semantic pipeline and existing JSON plus Markdown report outputs
- hardened semantic topic inputs by skipping low-information titles, dropping raw channel text from embedding inputs, tightening topic-label support thresholds, and recomputing representative titles after topic merges
