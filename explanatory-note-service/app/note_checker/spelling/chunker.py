"""Упаковка текстовых фрагментов в запросы к спеллеру."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import TextFragment

DEFAULT_CHUNK_CHARS = 9500


@dataclass
class ChunkEntry:
    fragment: TextFragment
    start: int
    length: int


@dataclass
class Chunk:
    text: str
    entries: list[ChunkEntry] = field(default_factory=list)


def build_chunks(
    fragments: list[TextFragment], max_chars: int = DEFAULT_CHUNK_CHARS
) -> list[Chunk]:
    if max_chars < 1:
        raise ValueError("max_chars должен быть положительным")

    chunks: list[Chunk] = []
    current = Chunk(text="")

    def flush() -> None:
        nonlocal current
        if current.entries:
            chunks.append(current)
        current = Chunk(text="")

    for fragment in fragments:
        text = fragment.text
        if not text:
            continue
        if len(text) > max_chars:
            flush()
            for offset in range(0, len(text), max_chars):
                part = text[offset : offset + max_chars]
                chunks.append(
                    Chunk(
                        text=part,
                        entries=[
                            ChunkEntry(fragment=fragment, start=0, length=len(part))
                        ],
                    )
                )
            continue
        separator = 1 if current.entries else 0
        if len(current.text) + separator + len(text) > max_chars:
            flush()
            separator = 0
        start = len(current.text) + separator
        if separator:
            current.text += "\n"
        current.text += text
        current.entries.append(
            ChunkEntry(fragment=fragment, start=start, length=len(text))
        )

    flush()
    return chunks


def entry_at(chunk: Chunk, position: int) -> ChunkEntry | None:
    for entry in chunk.entries:
        if entry.start <= position < entry.start + entry.length:
            return entry
    return None
