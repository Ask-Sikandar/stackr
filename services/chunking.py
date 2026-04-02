"""
SemanticChunker — paragraph-aware chunking with sentence-boundary fallback.

Strategy (justified here and in DECISIONS.md):
1. Split on double newlines first — these mark paragraph/section boundaries in
   Markdown and plain text, preserving semantic units better than arbitrary char counts.
2. If a paragraph exceeds chunk_size, split at ". " (sentence boundary) to avoid
   cutting mid-thought.
3. Lines matching the Markdown table pattern (|...|) are collected and emitted as
   a single atomic "table" chunk — splitting a pricing table row mid-way loses meaning.
4. Bullet lists (lines starting with - or *) are kept as one chunk for the same reason.
5. 50-char overlap is prepended from the START of the next chunk to give the LLM
   enough context for boundary chunks.
6. Section headings (# / ## / ###) are tracked and stored in metadata.section_title
   so retrieved chunks carry their topic label for citation.
"""

import re

from .interfaces.chunker import ChunkData, IChunker

_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$")
_TABLE_LINE_RE = re.compile(r"^\|.+\|$")
_LIST_LINE_RE = re.compile(r"^[-*]\s")


def _is_table_line(line: str) -> bool:
    return bool(_TABLE_LINE_RE.match(line.strip()))


def _is_list_line(line: str) -> bool:
    return bool(_LIST_LINE_RE.match(line.strip()))


class SemanticChunker(IChunker):
    """
    Implements IChunker with semantic paragraph/table/list awareness.
    """

    def chunk(self, content: str, chunk_size: int = 500, overlap: int = 50) -> list[ChunkData]:
        paragraphs = self._split_into_paragraphs(content)
        raw_chunks = self._paragraphs_to_chunks(paragraphs, chunk_size)
        return self._apply_overlap(raw_chunks, overlap)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _split_into_paragraphs(self, content: str) -> list[tuple[str, str]]:
        """
        Returns list of (text, chunk_type) tuples.
        chunk_type: "paragraph" | "table" | "list" | "heading"
        """
        result: list[tuple[str, str]] = []
        current_section: str = ""
        table_buf: list[str] = []
        list_buf: list[str] = []

        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            # Track headings so subsequent chunks get section_title metadata
            if _HEADING_RE.match(line):
                if table_buf:
                    result.append(("\n".join(table_buf), "table"))
                    table_buf = []
                if list_buf:
                    result.append(("\n".join(list_buf), "list"))
                    list_buf = []
                current_section = _HEADING_RE.match(line).group(1)  # type: ignore[union-attr]
                result.append((line, "heading"))
                i += 1
                continue

            # Accumulate table rows
            if _is_table_line(line):
                if list_buf:
                    result.append(("\n".join(list_buf), "list"))
                    list_buf = []
                table_buf.append(line)
                i += 1
                continue
            else:
                if table_buf:
                    result.append(("\n".join(table_buf), "table"))
                    table_buf = []

            # Accumulate list items
            if _is_list_line(line):
                if table_buf:
                    result.append(("\n".join(table_buf), "table"))
                    table_buf = []
                list_buf.append(line)
                i += 1
                continue
            else:
                if list_buf:
                    result.append(("\n".join(list_buf), "list"))
                    list_buf = []

            # Regular paragraph line
            if line.strip():
                result.append((line, "paragraph"))
            i += 1

        # Flush buffers
        if table_buf:
            result.append(("\n".join(table_buf), "table"))
        if list_buf:
            result.append(("\n".join(list_buf), "list"))

        return result

    def _paragraphs_to_chunks(
        self, paragraphs: list[tuple[str, str]], chunk_size: int
    ) -> list[dict]:
        """
        Merge consecutive paragraphs up to chunk_size.
        Tables/lists are always emitted as their own chunk (atomic).
        """
        chunks: list[dict] = []
        buf = ""
        buf_type = "paragraph"
        current_heading = ""
        char_start = 0

        def flush(text: str, ctype: str, start: int) -> None:
            text = text.strip()
            if text:
                chunks.append(
                    {
                        "content": text,
                        "chunk_type": ctype,
                        "section_title": current_heading,
                        "char_start": start,
                    }
                )

        for text, ctype in paragraphs:
            if ctype == "heading":
                current_heading = _HEADING_RE.match(text).group(1)  # type: ignore[union-attr]
                continue

            if ctype in ("table", "list"):
                # Flush current buffer before emitting atomic block
                if buf.strip():
                    flush(buf, buf_type, char_start)
                    char_start += len(buf)
                    buf = ""
                flush(text, ctype, char_start)
                char_start += len(text)
                continue

            # Normal paragraph: try to merge into buffer
            candidate = (buf + "\n\n" + text).strip() if buf else text
            if len(candidate) <= chunk_size:
                buf = candidate
                buf_type = "paragraph"
            else:
                # Buffer full — flush then handle oversized paragraph
                if buf.strip():
                    flush(buf, buf_type, char_start)
                    char_start += len(buf)
                    buf = ""

                if len(text) > chunk_size:
                    # Split at sentence boundaries
                    for sentence_chunk in self._split_at_sentences(text, chunk_size):
                        flush(sentence_chunk, "paragraph", char_start)
                        char_start += len(sentence_chunk)
                else:
                    buf = text
                    buf_type = "paragraph"

        if buf.strip():
            flush(buf, buf_type, char_start)

        return chunks

    @staticmethod
    def _split_at_sentences(text: str, chunk_size: int) -> list[str]:
        """Split a long paragraph at '. ' boundaries."""
        sentences = re.split(r"(?<=\.)\s+", text)
        chunks: list[str] = []
        buf = ""
        for sent in sentences:
            candidate = (buf + " " + sent).strip() if buf else sent
            if len(candidate) <= chunk_size:
                buf = candidate
            else:
                if buf:
                    chunks.append(buf)
                buf = sent
        if buf:
            chunks.append(buf)
        return chunks or [text]

    @staticmethod
    def _apply_overlap(raw_chunks: list[dict], overlap: int) -> list[ChunkData]:
        """
        Append the first `overlap` chars of the NEXT chunk to the end of each chunk.
        This gives boundary chunks enough context for embedding similarity to work well.
        """
        result: list[ChunkData] = []
        for i, chunk in enumerate(raw_chunks):
            content = chunk["content"]
            if i + 1 < len(raw_chunks):
                next_start = raw_chunks[i + 1]["content"][:overlap]
                if next_start and not content.endswith(next_start):
                    content = content + " " + next_start
            result.append(
                ChunkData(
                    content=content.strip(),
                    chunk_index=i,
                    metadata={
                        "section_title": chunk["section_title"],
                        "chunk_type": chunk["chunk_type"],
                        "char_start": chunk["char_start"],
                    },
                )
            )
        return result
