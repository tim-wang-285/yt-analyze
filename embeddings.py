from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from contextlib import contextmanager

import numpy as np

from config import DEFAULT_CACHE_DIR, DEFAULT_EMBEDDING_MODEL


class _SuppressHarmlessBertLoadReport(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not (
            "BertModel LOAD REPORT" in message
            and "embeddings.position_ids | UNEXPECTED" in message
            and "can be ignored when loading from different task/architecture" in message
        )


@contextmanager
def suppress_harmless_bert_load_report():
    logger = logging.getLogger("transformers.modeling_utils")
    log_filter = _SuppressHarmlessBertLoadReport()
    logger.addFilter(log_filter)
    try:
        yield
    finally:
        logger.removeFilter(log_filter)


def semantic_cache_paths(cache_dir: Path) -> dict[str, Path]:
    return {
        "vectors": cache_dir / "vectors.npy",
        "records": cache_dir / "records.jsonl",
        "manifest": cache_dir / "manifest.json",
    }


def semantic_text_digest(texts: list[str], model_name: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(model_name.encode("utf-8"))
    hasher.update(b"\n")
    for text in texts:
        hasher.update(text.encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def load_semantic_cache(cache_dir: Path, model_name: str, digest: str) -> np.ndarray | None:
    paths = semantic_cache_paths(cache_dir)
    if not paths["manifest"].exists() or not paths["vectors"].exists():
        return None

    try:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    except Exception:
        return None

    if manifest.get("model_name") != model_name or manifest.get("text_digest") != digest:
        return None

    return np.load(paths["vectors"])


def save_semantic_cache(
    cache_dir: Path,
    model_name: str,
    digest: str,
    records: list[dict],
    vectors: np.ndarray,
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = semantic_cache_paths(cache_dir)
    np.save(paths["vectors"], vectors.astype(np.float32))
    with paths["records"].open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    manifest = {
        "model_name": model_name,
        "text_digest": digest,
        "record_count": len(records),
        "embedding_dim": int(vectors.shape[1]) if vectors.ndim == 2 and len(vectors.shape) > 1 else 0,
    }
    paths["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def embed_semantic_records(
    records: list[dict],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    device: str | None = None,
) -> np.ndarray:
    texts = [record["semantic_text"] for record in records]
    digest = semantic_text_digest(texts, model_name)

    cached = load_semantic_cache(cache_dir, model_name, digest)
    if cached is not None:
        return cached

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for semantic embeddings. Install project dependencies first."
        ) from exc

    model_kwargs = {"device": device} if device is not None else {}
    with suppress_harmless_bert_load_report():
        model = SentenceTransformer(model_name, **model_kwargs)
    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    save_semantic_cache(cache_dir, model_name, digest, records, vectors)
    return vectors
