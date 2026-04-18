from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

import numpy as np

from helpers import build_channel_title_groups, build_title_counts, record_datetime
from reporting import build_topic_timeline
from text_features import (
    canonical_topic_label_components,
    label_topic,
    merge_topic_labels,
)
def time_range(records: list[dict]) -> dict:
    times = sorted(dt for dt in (record_datetime(record) for record in records) if dt is not None)
    if not times:
        return {"start": None, "end": None}
    return {
        "start": times[0].isoformat(timespec="seconds"),
        "end": times[-1].isoformat(timespec="seconds"),
    }


def canonical_topic_signature(label: str) -> tuple[str, ...]:
    return tuple(sorted(set(canonical_topic_label_components(label))))


def topic_counts_within_merge_tolerance(count1: int, count2: int) -> bool:
    if count1 <= 0 or count2 <= 0:
        return False
    difference = abs(count1 - count2)
    return (difference / count1) <= 0.5 or (difference / count2) <= 0.5


def merge_topics_by_label_overlap(
    topics: list[dict],
    records: list[dict],
    vectors,
) -> list[dict]:
    merged_topics: list[dict] = []

    def merge_topic_into(base: dict, incoming: dict) -> None:
        base_size = base["size"]
        incoming_size = incoming["size"]
        weighted_centroid = (base["_centroid"] * base_size) + (incoming["_centroid"] * incoming_size)
        norm = np.linalg.norm(weighted_centroid)
        if norm:
            weighted_centroid = weighted_centroid / norm
        base["_centroid"] = weighted_centroid
        base["size"] = base_size + incoming_size
        base["label"] = merge_topic_labels(base["label"], incoming["label"])
        base["_label_components"] = canonical_topic_label_components(base["label"])
        base["members"].extend(incoming["members"])
        base["representative_titles"] = list(dict.fromkeys(base["representative_titles"] + incoming["representative_titles"]))[:5]

    def finalize_equivalent_and_subset_topics() -> list[dict]:
        exact_grouped_topics: dict[tuple[str, ...], list[dict]] = defaultdict(list)
        passthrough_topics: list[dict] = []

        for topic in merged_topics:
            signature = canonical_topic_signature(topic["label"])
            topic["_label_signature"] = signature
            if signature:
                exact_grouped_topics[signature].append(topic)
            else:
                passthrough_topics.append(topic)

        collapsed_topics: list[dict] = passthrough_topics[:]
        for signature, grouped_topics in exact_grouped_topics.items():
            canonical_label = " / ".join(signature)
            base_topic = sorted(grouped_topics, key=lambda item: (-item["size"], item["label"]))[0]
            base_topic["label"] = canonical_label
            base_topic["_label_components"] = list(signature)
            base_topic["_label_signature"] = signature
            for duplicate_topic in grouped_topics:
                if duplicate_topic is base_topic:
                    continue
                merge_topic_into(base_topic, duplicate_topic)
                base_topic["label"] = canonical_label
                base_topic["_label_components"] = list(signature)
                base_topic["_label_signature"] = signature
            collapsed_topics.append(base_topic)

        active_topics = collapsed_topics
        changed = True
        while changed:
            changed = False
            ordered_topics = sorted(
                active_topics,
                key=lambda item: (-len(item.get("_label_signature", ())), -item["size"], item["label"]),
            )
            for topic in list(reversed(ordered_topics)):
                topic_signature = set(topic.get("_label_signature", ()))
                if not topic_signature:
                    continue
                strict_supersets = [
                    candidate
                    for candidate in ordered_topics
                    if candidate is not topic and topic_signature < set(candidate.get("_label_signature", ()))
                ]
                if not strict_supersets:
                    continue
                target = sorted(
                    strict_supersets,
                    key=lambda item: (len(item.get("_label_signature", ())), -item["size"], item["label"]),
                )[0]
                merge_topic_into(target, topic)
                target_signature = target.get("_label_signature", ())
                if target_signature:
                    target["label"] = " / ".join(target_signature)
                    target["_label_components"] = list(target_signature)
                active_topics = [item for item in active_topics if item is not topic]
                changed = True
                break

        return active_topics

    for topic in sorted(topics, key=lambda item: item["size"], reverse=True):
        components = canonical_topic_label_components(topic["label"])
        topic["_label_components"] = components
        if not components:
            merged_topics.append(topic)
            continue

        target = None
        for candidate in merged_topics:
            candidate_components = set(candidate.get("_label_components", []))
            topic_component_set = set(components)
            shared_components = sorted(candidate_components.intersection(topic_component_set))
            if not shared_components:
                continue
            if not topic_counts_within_merge_tolerance(candidate["size"], topic["size"]):
                continue

            multi_component_overlap = len(candidate_components) > 1 and len(topic_component_set) > 1
            subset_compatible_overlap = candidate_components.issubset(topic_component_set) or topic_component_set.issubset(candidate_components)
            if multi_component_overlap and not subset_compatible_overlap:
                continue

            target = candidate
            break

        if target is None:
            merged_topics.append(topic)
        else:
            merge_topic_into(target, topic)

    merged_topics = finalize_equivalent_and_subset_topics()

    for topic in merged_topics:
        topic["language_hints"] = dict(Counter(member["language_hint"] for member in topic["members"] if member.get("language_hint")))
        topic["title_counts"] = build_title_counts(topic["members"])
        topic["representative_channels"] = build_channel_title_groups(topic["members"])
        topic["time_range"] = time_range(topic["members"])
        topic["timeline"] = build_topic_timeline(topic["members"])
        representative_indices = sorted(
            (member["index"] for member in topic["members"]),
            key=lambda idx: float(vectors[idx] @ topic["_centroid"]),
            reverse=True,
        )[:5]
        topic["representative_titles"] = [records[idx]["title"] for idx in representative_indices]

    return merged_topics


def build_topic_report(
    records: list[dict],
    vectors,
    model_name: str,
    threshold: float = 0.60,
) -> dict:
    try:
        from sentence_transformers.util import community_detection
    except ImportError as exc:
        raise RuntimeError("sentence-transformers is required for topic clustering.") from exc

    communities = community_detection(
        vectors,
        threshold=threshold,
        min_community_size=2,
        show_progress_bar=False,
    )

    assigned = set()
    topics = []

    for topic_id, member_indices in enumerate(communities):
        member_indices = list(member_indices)
        member_index_map = {idx: pos for pos, idx in enumerate(member_indices)}
        assigned.update(member_indices)
        member_vectors = vectors[member_indices]
        centroid = member_vectors.mean(axis=0)
        centroid_norm = np.linalg.norm(centroid)
        if centroid_norm:
            centroid = centroid / centroid_norm
        topic_records = [records[i] for i in member_indices]
        representative_indices = sorted(member_indices, key=lambda idx: float(vectors[idx] @ centroid), reverse=True)[:5]
        representative_local_indices = [member_index_map[idx] for idx in representative_indices if idx in member_index_map]

        topics.append(
            {
                "topic_id": topic_id,
                "size": len(member_indices),
                "label": label_topic(topic_records, representative_local_indices),
                "language_hints": dict(Counter(record["language_hint"] for record in topic_records)),
                "time_range": time_range(topic_records),
                "timeline": build_topic_timeline(topic_records),
                "representative_titles": [records[i]["title"] for i in representative_indices],
                "_centroid": centroid,
                "members": [
                    {
                        "index": idx,
                        "title": records[idx]["title"],
                        "channel": records[idx]["channel"],
                        "time": records[idx]["time"],
                        "parsed_time": records[idx].get("parsed_time"),
                        "language_hint": records[idx]["language_hint"],
                    }
                    for idx in member_indices
                ],
            }
        )

    noise = []
    for idx, record in enumerate(records):
        if idx in assigned:
            continue
        noise.append(
            {
                "index": idx,
                "title": record["title"],
                "channel": record["channel"],
                "time": record["time"],
                "parsed_time": record.get("parsed_time"),
                "language_hint": record["language_hint"],
            }
        )

    topics = merge_topics_by_label_overlap(topics, records, vectors)
    topics.sort(key=lambda item: item["size"], reverse=True)
    for new_id, topic in enumerate(topics):
        topic["topic_id"] = new_id
        topic.pop("_centroid", None)
        topic.pop("_label_components", None)
        topic.pop("_label_signature", None)
        topic.pop("representative_titles", None)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model_name": model_name,
        "threshold": threshold,
        "record_count": len(records),
        "topic_count": len(topics),
        "noise_count": len(noise),
        "topics": topics,
        "noise": noise,
    }
