from __future__ import annotations

from typing import TypedDict


class RawEntry(TypedDict, total=False):
    product: str
    action: str
    title: str
    channel: str
    time: str
    parse_flags: list[str]


class SemanticRecord(TypedDict, total=False):
    product: str
    action: str
    title: str
    clean_title: str
    channel: str
    time: str
    parsed_time: str
    semantic_text: str
    language_hint: str


class TopicMember(TypedDict, total=False):
    index: int
    title: str
    channel: str
    time: str
    parsed_time: str
    language_hint: str


class TopicData(TypedDict, total=False):
    topic_id: int
    size: int
    label: str
    language_hints: dict
    time_range: dict
    timeline: dict
    title_counts: list[dict]
    representative_channels: list[dict]
    members: list[TopicMember]
