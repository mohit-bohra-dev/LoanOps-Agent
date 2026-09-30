"""Markdown chunker for RAG pipeline."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Chunk:
    """A chunk of text with metadata."""

    chunk_id: str
    content: str
    metadata: dict[str, Any]


class MarkdownChunker:
    """Splits markdown content into chunks with ~600 tokens and 80 token overlap."""

    def __init__(self, target_tokens: int = 600, overlap_tokens: int = 80) -> None:
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, content: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split markdown content into chunks based on headers and approximate token count."""
        # Estimate token count by word count (rough approximation)
        # This is a simplified approach - in production, you might want to use a tokenizer
        words = content.split()

        # If content is shorter than target, return as a single chunk
        if len(words) <= self.target_tokens:
            chunk_id = self._generate_chunk_id(content, metadata or {})
            return [Chunk(chunk_id=chunk_id, content=content, metadata=metadata or {})]

        # Split by headers first to preserve document structure
        sections = self._split_by_headers(content)

        chunks: list[Chunk] = []
        current_chunk_words: list[str] = []
        current_metadata = metadata or {}

        for section in sections:
            section_words = section.split()

            # If this section alone exceeds target, we need to split it further
            if len(section_words) > self.target_tokens:
                # Overlap wider than the window cannot slide forward. Keep the section whole.
                if self.overlap_tokens >= self.target_tokens:
                    chunk_id = self._generate_chunk_id(section, current_metadata)
                    chunks.append(
                        Chunk(
                            chunk_id=chunk_id,
                            content=section,
                            metadata=current_metadata.copy(),
                        )
                    )
                    current_chunk_words = []
                    continue
                sub_chunks = self._split_large_section(section_words, current_metadata)
                chunks.extend(sub_chunks)
                current_chunk_words = []
                continue

            # Check if adding this section would exceed the target
            if (
                len(current_chunk_words) + len(section_words) > self.target_tokens
                and current_chunk_words
            ):
                # Create a chunk with current content
                chunk_content = " ".join(current_chunk_words)
                chunk_id = self._generate_chunk_id(chunk_content, current_metadata)
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id, content=chunk_content, metadata=current_metadata.copy()
                    )
                )

                # Keep overlap for next chunk
                if len(current_chunk_words) > self.overlap_tokens:
                    current_chunk_words = current_chunk_words[-self.overlap_tokens :]
                else:
                    current_chunk_words = []

            # Add the section to the current chunk
            current_chunk_words.extend(section_words)

        # Don't forget the last chunk
        if current_chunk_words:
            chunk_content = " ".join(current_chunk_words)
            chunk_id = self._generate_chunk_id(chunk_content, current_metadata)
            chunks.append(
                Chunk(chunk_id=chunk_id, content=chunk_content, metadata=current_metadata.copy())
            )

        return chunks

    def _split_by_headers(self, content: str) -> list[str]:
        """Split content by markdown headers, preserving headers with their sections."""
        # Split by headers but keep the headers
        parts = re.split(r"(^#{1,6}\s.*)", content, flags=re.MULTILINE)

        sections: list[str] = []
        current_section = ""

        for part in parts:
            if re.match(r"^#{1,6}\s", part):
                # This is a header - start a new section
                if current_section.strip():
                    sections.append(current_section.strip())
                current_section = part
            else:
                # This is content - add to current section
                current_section += part

        # Add the final section
        if current_section.strip():
            sections.append(current_section.strip())

        # If no headers, return the whole content as one section
        return sections if sections else [content]

    def _split_large_section(self, words: list[str], metadata: dict[str, Any]) -> list[Chunk]:
        """Split a large section into smaller chunks."""
        chunks: list[Chunk] = []
        position = 0

        while position < len(words):
            # Take target_tokens words
            end_position = min(position + self.target_tokens, len(words))
            chunk_words = words[position:end_position]
            chunk_content = " ".join(chunk_words)

            # Generate chunk ID
            chunk_id = self._generate_chunk_id(chunk_content, metadata)

            # Create chunk
            chunks.append(
                Chunk(chunk_id=chunk_id, content=chunk_content, metadata=metadata.copy())
            )

            if end_position == len(words):
                break

            # Overlap must not move the window backward (overlap >= target loops forever).
            next_position = end_position - self.overlap_tokens
            if next_position <= position:
                next_position = end_position
            position = next_position
            if position >= len(words):
                break

            # Drop a tiny tail only when overlap is smaller than the step just taken.
            if (
                self.overlap_tokens < self.target_tokens
                and len(words) - position <= self.overlap_tokens
            ):
                break

        return chunks

    def _generate_chunk_id(self, content: str, metadata: dict[str, Any]) -> str:
        """Generate a unique ID for a chunk based on its content and metadata."""
        # Create a hash of content and metadata to generate a consistent ID
        meta_str = str(sorted(metadata.items()))
        hash_input = content + meta_str
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
