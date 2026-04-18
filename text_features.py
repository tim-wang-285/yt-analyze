from __future__ import annotations

import re
from collections import Counter

from config import (
    ALL_STOPWORDS,
    CJK_RUN_RE,
    CHANNEL_LABEL_MIN_RECORDS,
    CHANNEL_LABEL_MIN_RECORD_SHARE,
    JA_LABEL_STOPWORDS,
    LABEL_STOPWORDS,
    LABEL_TERM_MIN_RECORDS,
    LABEL_TERM_MIN_RECORD_SHARE,
    LABEL_UNIT_RE,
    MIN_SHORT_TITLE_CHARS,
    MIN_TITLE_LABEL_TERMS,
    PHRASE_COMPONENT_SUPPRESSION_RATIO,
    PHRASE_PROMOTION_MIN_RECORD_SHARE,
    PHRASE_PROMOTION_MIN_REP_COUNT,
    PHRASE_SCORE_BOOST,
    UIDISH_TOKEN_RE,
    URLISH_TOKEN_RE,
)
from helpers import clean_title


def is_url_only_title(title: str) -> bool:
    raw = (title or "").strip()
    if not raw:
        return True
    return clean_title(raw) == ""


def normalize_semantic_text(title: str, channel: str) -> str:
    return clean_title(title)


def guess_language(text: str) -> str:
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "ja"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"www\.\S+", " ", text)
    text = re.sub(r"\b(?:youtube|youtu|watch|video|videos|channel|playlist)\b", " ", text)
    text = re.sub(r"\b[a-z0-9_-]{8,}\b", " ", text)

    words = re.findall(r"[^\W_#]+(?:'[^\W_]+)?|#[^\W_#]+", text, flags=re.UNICODE)

    out = []
    for word in words:
        if len(word) < 2:
            continue
        if is_noise_term(word):
            continue
        if word in ALL_STOPWORDS:
            continue
        if word.isdigit():
            continue
        if re.fullmatch(r"[a-z]*\d+[a-z\d]*", word):
            continue
        out.append(word)

    return out


def extract_phrases(text: str) -> list[str]:
    tokens = tokenize(text)
    phrases = []

    for n in (2, 3):
        for i in range(len(tokens) - n + 1):
            gram = tokens[i : i + n]
            if any(tok in ALL_STOPWORDS for tok in gram):
                continue
            phrases.append(" ".join(gram))

    return phrases


def term_tokens(term: str) -> tuple[str, ...]:
    return tuple(tokenize(term))


def is_phrase_term(term: str) -> bool:
    return len(term_tokens(term)) >= 2


def has_cjk(text: str) -> bool:
    return bool(CJK_RUN_RE.search(text))


def split_cjk_runs(text: str) -> list[str]:
    parts = re.findall(r"[A-Za-z]+|\d+|[\u3040-\u30ff]+|[\u4e00-\u9fff]+", text)
    if parts and "".join(parts) == text:
        return parts
    return [text]


def expand_cjk_term(term: str) -> list[str]:
    if len(term) <= 12:
        return [term] if not is_noise_term(term) else []

    pieces: list[str] = []
    window = 4 if len(term) >= 8 else 3
    for i in range(len(term) - window + 1):
        chunk = term[i : i + window]
        if len(chunk) >= 2 and not is_noise_term(chunk):
            pieces.append(chunk)
    return pieces


def is_noise_term(term: str) -> bool:
    normalized = term.strip().strip(".,;:!?()[]{}<>\"'")
    if not normalized:
        return True
    if normalized.lower() in LABEL_STOPWORDS:
        return True
    if normalized in JA_LABEL_STOPWORDS:
        return True
    if normalized.isdigit():
        return True
    if URLISH_TOKEN_RE.search(normalized):
        return True
    if any(sep in normalized for sep in ("/", "\\", "@", "?", "#", "&", "=")):
        return True

    compact = re.sub(r"[-_]", "", normalized)
    if len(compact) >= 10 and UIDISH_TOKEN_RE.fullmatch(compact):
        if any(ch.isdigit() for ch in compact) and any(ch.isalpha() for ch in compact):
            return True
        if re.fullmatch(r"[a-f0-9]+", compact, flags=re.IGNORECASE):
            return True
    if len(compact) >= 12 and compact.isalnum() and sum(ch.isdigit() for ch in compact) >= 2:
        return True
    return False


def extract_label_terms(text: str) -> list[str]:
    text = clean_title(text)
    if not text:
        return []

    terms: list[str] = []
    latin_terms = tokenize(text)
    if latin_terms:
        terms.extend(latin_terms)
        terms.extend(extract_phrases(text))

    for match in LABEL_UNIT_RE.findall(text):
        term = match.strip("#").strip()
        if not term or is_noise_term(term):
            continue

        if has_cjk(term):
            terms.extend(expand_cjk_term(term))
        elif len(term) >= 2:
            terms.append(term.lower())

    return terms


def has_semantic_title_signal(title: str) -> bool:
    cleaned = clean_title(title)
    if not cleaned:
        return False

    normalized_terms = {
        canonicalize_topic_label(term)
        for term in extract_label_terms(cleaned)
        if canonicalize_topic_label(term)
    }
    if len(normalized_terms) >= MIN_TITLE_LABEL_TERMS:
        return True

    return len(cleaned) >= MIN_SHORT_TITLE_CHARS


def canonicalize_topic_label(label: str) -> str:
    normalized = (label or "").strip().lower()
    normalized = re.sub(r"\s*[|/]\s*", " / ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def topic_label_components(label: str) -> list[str]:
    parts = []
    for raw_part in re.split(r"\s*/\s*", (label or "").strip()):
        part = raw_part.strip()
        if part:
            parts.append(part)
    return parts


def canonical_topic_label_components(label: str) -> list[str]:
    components = []
    for part in topic_label_components(label):
        normalized = canonicalize_topic_label(part)
        if normalized:
            components.append(normalized)
    return components


def merge_topic_labels(base_label: str, incoming_label: str) -> str:
    merged_parts: list[str] = []
    seen_parts: set[str] = set()

    for label in (base_label, incoming_label):
        for part in topic_label_components(label):
            normalized = canonicalize_topic_label(part)
            if not normalized or normalized in seen_parts:
                continue
            merged_parts.append(part)
            seen_parts.add(normalized)

    return " / ".join(merged_parts) if merged_parts else canonicalize_topic_label(base_label or incoming_label)


def label_topic(topic_records: list[dict], representative_indices: list[int]) -> str:
    rep_set = set(representative_indices)
    term_scores = Counter()
    rep_term_scores = Counter()
    channel_scores = Counter()
    term_record_counts = Counter()
    term_channel_counts = Counter()
    language_scores = Counter(record["language_hint"] for record in topic_records)

    for idx, record in enumerate(topic_records):
        weight = 2.5 if idx in rep_set else 1.0

        title_terms = extract_label_terms(record["title"])
        channel_terms = extract_label_terms(record["channel"])
        unique_title_terms = set(title_terms)
        unique_channel_terms = set(channel_terms)

        for term in title_terms:
            term_scores[term] += weight * 2.0
            if idx in rep_set:
                rep_term_scores[term] += 1
        for term in unique_title_terms:
            term_record_counts[term] += 1
        for term in channel_terms:
            channel_scores[term] += weight
        for term in unique_channel_terms:
            term_channel_counts[term] += 1

    def is_useful(term: str) -> bool:
        return not is_noise_term(term) and len(term) >= 2

    def phrase_record_share(term: str) -> float:
        if not topic_records:
            return 0.0
        return term_record_counts[term] / len(topic_records)

    def term_record_share(term: str) -> float:
        if not topic_records:
            return 0.0
        base_count = term_record_counts[term] if term_record_counts[term] else term_channel_counts[term]
        return base_count / len(topic_records)

    def phrase_is_supported(term: str) -> bool:
        if not is_phrase_term(term):
            return False
        if rep_term_scores[term] >= PHRASE_PROMOTION_MIN_REP_COUNT:
            return True
        return phrase_record_share(term) >= PHRASE_PROMOTION_MIN_RECORD_SHARE

    def boosted_score(term: str) -> float:
        score = term_scores[term]
        if phrase_is_supported(term):
            token_count = len(term_tokens(term))
            score *= PHRASE_SCORE_BOOST + (0.1 * min(token_count - 2, 1))
        return score

    def title_term_is_label_eligible(term: str) -> bool:
        if not is_useful(term):
            return False
        support_count = term_record_counts[term]
        support_share = term_record_share(term)
        if is_phrase_term(term):
            return phrase_is_supported(term) and support_count >= LABEL_TERM_MIN_RECORDS and support_share >= LABEL_TERM_MIN_RECORD_SHARE
        return support_count >= LABEL_TERM_MIN_RECORDS and support_share >= LABEL_TERM_MIN_RECORD_SHARE

    def channel_term_is_label_eligible(term: str) -> bool:
        if not is_useful(term):
            return False
        support_count = term_channel_counts[term]
        support_share = term_record_share(term)
        return support_count >= CHANNEL_LABEL_MIN_RECORDS and support_share >= CHANNEL_LABEL_MIN_RECORD_SHARE

    def best_covering_phrase(terms: list[str]) -> str | None:
        target_tokens = {token for term in terms for token in term_tokens(term)}
        if len(target_tokens) < 2:
            return None

        candidates = []
        for phrase in supported_phrases:
            phrase_tokens = phrase_components.get(phrase, set())
            if target_tokens.issubset(phrase_tokens):
                candidates.append(phrase)

        if not candidates:
            return None

        candidates.sort(
            key=lambda phrase: (
                boosted_score(phrase),
                rep_term_scores[phrase],
                term_record_counts[phrase],
                len(term_tokens(phrase)),
                len(phrase),
            ),
            reverse=True,
        )
        best_phrase = candidates[0]
        weakest_component_score = min(term_scores[token] for token in target_tokens if term_scores[token])
        if weakest_component_score and term_scores[best_phrase] >= weakest_component_score * PHRASE_COMPONENT_SUPPRESSION_RATIO:
            return best_phrase
        if phrase_record_share(best_phrase) >= PHRASE_PROMOTION_MIN_RECORD_SHARE and rep_term_scores[best_phrase] >= 1:
            return best_phrase
        return None

    phrase_components: dict[str, set[str]] = {}
    supported_phrases: list[str] = []
    for term in term_scores:
        if not phrase_is_supported(term):
            continue
        components = set(term_tokens(term))
        if not components:
            continue
        phrase_components[term] = components
        supported_phrases.append(term)

    suppress_terms: set[str] = set()
    for phrase in supported_phrases:
        phrase_score = term_scores[phrase]
        for component in phrase_components[phrase]:
            if term_scores[component] and phrase_score >= term_scores[component] * PHRASE_COMPONENT_SUPPRESSION_RATIO:
                suppress_terms.add(component)

    ranked_terms: list[str] = []
    seen_terms: set[str] = set()
    ranked_candidates = sorted(
        term_scores,
        key=lambda term: (
            boosted_score(term),
            rep_term_scores[term],
            term_record_counts[term],
            len(term_tokens(term)),
            len(term),
        ),
        reverse=True,
    )
    for term in ranked_candidates:
        normalized = canonicalize_topic_label(term)
        if normalized in seen_terms:
            continue
        if title_term_is_label_eligible(term):
            if term in suppress_terms and not is_phrase_term(term):
                continue
            ranked_terms.append(term)
            seen_terms.add(normalized)
        if len(ranked_terms) >= 2:
            break

    if not ranked_terms:
        channel_candidates = sorted(
            channel_scores,
            key=lambda term: (
                channel_scores[term],
                term_channel_counts[term],
                len(term_tokens(term)),
                len(term),
            ),
            reverse=True,
        )
        for term in channel_candidates:
            normalized = canonicalize_topic_label(term)
            if normalized in seen_terms:
                continue
            if channel_term_is_label_eligible(term):
                ranked_terms.append(term)
                seen_terms.add(normalized)
            if len(ranked_terms) >= 2:
                break

    if not ranked_terms:
        reps = []
        for i in representative_indices[:2]:
            if i >= len(topic_records):
                continue
            rep_title = clean_title(topic_records[i]["title"])
            if not rep_title or is_url_only_title(topic_records[i]["title"]):
                continue
            reps.append(rep_title)
        if reps:
            return " | ".join(reps)
        return "uncategorized"

    if len(ranked_terms) >= 2:
        top_term, second_term = ranked_terms[0], ranked_terms[1]
        recovered_phrase = best_covering_phrase(ranked_terms[:2])
        if recovered_phrase:
            return recovered_phrase
        if language_scores.get("en", 0) >= language_scores.get("ja", 0):
            english_phrase_candidates = [
                term
                for term in supported_phrases
                if set(term_tokens(top_term)).issubset(set(term_tokens(term)))
                and set(term_tokens(second_term)).issubset(set(term_tokens(term)))
            ]
            if english_phrase_candidates:
                english_phrase_candidates.sort(
                    key=lambda term: (
                        boosted_score(term),
                        term_record_counts[term],
                        rep_term_scores[term],
                        len(term_tokens(term)),
                        len(term),
                    ),
                    reverse=True,
                )
                return english_phrase_candidates[0]
        if is_phrase_term(top_term):
            second_tokens = set(term_tokens(second_term))
            if second_tokens and second_tokens.issubset(set(term_tokens(top_term))):
                return top_term
        if rep_term_scores[top_term] >= 2 or language_scores.get("ja", 0) >= language_scores.get("en", 0):
            if rep_term_scores[second_term] == 0 and len(top_term) >= len(second_term):
                return top_term
        if top_term == second_term:
            return top_term
        return " / ".join(ranked_terms[:2])

    return ranked_terms[0]
