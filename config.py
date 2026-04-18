from __future__ import annotations

import os
import re
from pathlib import Path


def _read_dotenv_value(name: str, dotenv_path: Path | None = None) -> str | None:
    path = dotenv_path or Path(".env")
    if not path.exists():
        return None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        return value.strip().strip("\"'")
    return None


WATCH_FILE = Path(
    os.environ.get("WATCH_FILE")
    or _read_dotenv_value("WATCH_FILE")
    or "watch-history.html"
)
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_CACHE_DIR = Path(".cache/yt-analyze")
DEFAULT_RESULTS_OUTPUT = Path("outputs/results.json")
DEFAULT_RESULTS_BY_YEAR_OUTPUT = Path("outputs/results_by_year.json")
TOPIC_PREVIEW_LIMIT = 20
PHRASE_PROMOTION_MIN_RECORD_SHARE = 0.15
PHRASE_PROMOTION_MIN_REP_COUNT = 1
PHRASE_SCORE_BOOST = 1.6
PHRASE_COMPONENT_SUPPRESSION_RATIO = 0.6
MIN_TITLE_LABEL_TERMS = 2
MIN_SHORT_TITLE_CHARS = 8
LABEL_TERM_MIN_RECORD_SHARE = 0.18
LABEL_TERM_MIN_RECORDS = 2
CHANNEL_LABEL_MIN_RECORD_SHARE = 0.5
CHANNEL_LABEL_MIN_RECORDS = 3

GENERIC_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those",
    "how", "why", "what", "when", "where", "which", "who",
    "from", "into", "about", "than", "then", "there", "here",
    "your", "you", "my", "our", "their", "his", "her", "its",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "can", "could", "will", "would", "should", "may", "might",
    "just", "more", "most", "some", "any", "all", "only",
    "it", "it's", "im", "i'm", "we", "they", "he", "she",
    "at", "by", "as", "if", "but", "not",
    "www", "http", "https", "com", "net", "org",
    "youtube", "youtu", "watch", "video", "videos", "channel",
    "new", "end", "check", "no", "yes", "vs", "sound", "sounds",
    "short", "shorts", "#shorts", "official", "music", "mv",
    "try", "tried", "take", "took", "human", "me", "get", "gets"
}

LABEL_STOPWORDS = GENERIC_STOPWORDS | {
    "live", "version", "ver", "feat", "ft", "full", "audio", "lyrics",
    "sub", "subs", "subtitle", "subtitles", "topic", "officially",
    "cover", "remix", "mix", "performance", "concert", "clip", "highlights",
    "trailer", "teaser", "reaction", "review", "stream", "broadcast",
    "episode", "ep", "part", "pt", "season", "series",
}

JA_GENERIC_STOPWORDS = {
    "日本", "アメリカ", "する"
}

JA_LABEL_STOPWORDS = JA_GENERIC_STOPWORDS | {
    "公式", "動画", "配信", "実況", "切り抜き", "歌詞", "音楽", "ライブ",
    "放送", "番組", "予告", "本編", "前編", "後編", "最新", "限定", "特集",
}

LABEL_UNIT_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9'&+._-]*|[\u3040-\u30ff]+|[\u4e00-\u9fff]+|#[^\W_#]+",
    re.UNICODE,
)

CJK_RUN_RE = re.compile(r"[\u3040-\u30ff]+|[\u4e00-\u9fff]+")
URLISH_TOKEN_RE = re.compile(r"(?i)(?:https?://|www\.|(?:[\w-]+\.)+[a-z]{2,})(?:/[^\s]*)?$")
UIDISH_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")

CUSTOM_STOPWORDS = set()
ALL_STOPWORDS = GENERIC_STOPWORDS | CUSTOM_STOPWORDS
