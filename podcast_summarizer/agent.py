"""
Podcast Transcript Summarizer — LLM orchestration layer.
Supports Ollama (local) and Claude API backends via llm.py.
No Streamlit dependencies.
"""

import re
from datetime import date
from pathlib import Path
from typing import Generator

from llm import Backend, complete, stream_complete

SUMMARIES_DIR = Path(__file__).parent.parent / "portfolio" / "podcast-summaries"
MAX_TOKENS_CHUNK = 700
MAX_TOKENS_COMPILE = 4000
CHUNK_WORD_TARGET = 2500

SYSTEM_PROMPT = """You are a research assistant building a learning knowledge base from podcast \
transcripts for a product manager. Your job is to pull out what's actually useful and skip the rest.

Principles:
- Extract concrete claims, tactics, and numbers — not vague topic summaries
- Preserve attribution: distinguish host framing from guest expertise when speaker labels exist
- Quotes must be verbatim from the transcript, never paraphrased or invented
- No filler: never write "the speaker discusses" or "this section covers" — state what was said
- If a segment is mostly small talk or filler, say so briefly rather than padding output
- Frameworks and mental models get named explicitly, even if the speaker didn't name them"""


def clean_transcript(raw: str) -> str:
    """Strips WebVTT/SRT cue numbers and timestamps, collapses duplicate caption lines."""
    text = raw.strip()
    is_captions = text.upper().startswith("WEBVTT") or re.search(
        r"\d\d:\d\d:\d\d[.,]\d\d\d\s*-->\s*\d\d:\d\d:\d\d[.,]\d\d\d", text
    )
    if not is_captions:
        return text

    cleaned = []
    prev = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.upper() == "WEBVTT":
            continue
        if re.fullmatch(r"\d+", line) or "-->" in line:
            continue
        if line == prev:
            continue
        cleaned.append(line)
        prev = line
    return "\n".join(cleaned)


def _split_oversized(paragraph: str, max_words: int) -> list[str]:
    """Splits a single paragraph that alone exceeds max_words into word-bounded pieces."""
    words = paragraph.split()
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def chunk_transcript(text: str, max_words: int = CHUNK_WORD_TARGET) -> list[str]:
    """Splits a cleaned transcript into word-bounded chunks on paragraph breaks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    if not paragraphs:
        return []

    pieces = []
    for para in paragraphs:
        if len(para.split()) > max_words:
            pieces.extend(_split_oversized(para, max_words))
        else:
            pieces.append(para)

    chunks = []
    current: list[str] = []
    current_words = 0
    for piece in pieces:
        piece_words = len(piece.split())
        if current and current_words + piece_words > max_words:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0
        current.append(piece)
        current_words += piece_words
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def extract_chunk_notes(
    client,
    backend: Backend,
    model: str,
    chunk: str,
    chunk_index: int,
    total_chunks: int,
    podcast_title: str,
    episode_title: str,
) -> str:
    """Extracts structured notes from one transcript segment."""
    prompt = (
        f"Podcast: {podcast_title}\n"
        f"Episode: {episode_title}\n"
        f"Transcript segment {chunk_index + 1} of {total_chunks}\n\n"
        "Extract from this segment:\n"
        "1. **Key points** — concrete claims, tactics, or insights (bulleted)\n"
        "2. **Notable quotes** — verbatim, quoted, with speaker if labeled\n"
        "3. **Frameworks/models** — named concepts or mental models, if any\n"
        "4. **Mentions** — tools, books, people, or companies referenced, if any\n\n"
        "Skip a section entirely if the segment has nothing for it. No preamble.\n\n"
        f"TRANSCRIPT SEGMENT:\n\n{chunk}"
    )
    return complete(client, backend, SYSTEM_PROMPT, prompt, MAX_TOKENS_CHUNK, model)


def compile_summary_stream(
    client,
    backend: Backend,
    model: str,
    podcast_title: str,
    episode_title: str,
    guest: str,
    notes: list[str],
) -> Generator[str, None, None]:
    """Compiles per-segment notes into one learning-oriented summary. Yields text chunks."""
    summary_date = date.today().isoformat()
    notes_block = "\n\n---\n\n".join(
        f"### Segment {i + 1} notes\n\n{note}" for i, note in enumerate(notes)
    )
    title = episode_title or podcast_title
    byline = " | ".join(
        part for part in [f"Guest: {guest}" if guest else "", podcast_title, f"Generated: {summary_date}"] if part
    )
    prompt = (
        "Compile a learning summary of this podcast episode from the segment notes below.\n\n"
        f"Podcast: {podcast_title}\n"
        f"Episode: {episode_title or 'Not specified'}\n"
        f"Guest: {guest or 'Not specified'}\n"
        f"Date: {summary_date}\n\n"
        "Use this exact structure:\n\n"
        f"# {title}\n"
        f"*{byline}*\n\n"
        "## Executive Summary\n"
        "[3-4 sentences. The core thesis of the episode, not a table of contents.]\n\n"
        "## Key Takeaways\n"
        "[5-8 bullets. Concrete and actionable, ranked by importance.]\n\n"
        "## Frameworks & Mental Models\n"
        "[Named concept + one-line explanation. Omit section if none surfaced.]\n\n"
        "## Notable Quotes\n"
        "[Verbatim quotes with speaker attribution where available.]\n\n"
        "## Topics Discussed\n"
        "[Chronological list of themes covered, one line each.]\n\n"
        "## Resources & Mentions\n"
        "[Tools, books, people, companies referenced. Omit section if none.]\n\n"
        "## Reflection Questions\n"
        "[3-5 questions for applying this to your own work.]\n\n"
        "Deduplicate across segments — don't repeat the same quote or point twice. "
        "Eliminate hedging and filler.\n\n"
        f"SEGMENT NOTES:\n\n{notes_block}"
    )
    yield from stream_complete(client, backend, SYSTEM_PROMPT, prompt, MAX_TOKENS_COMPILE, model)


def save_summary(podcast_title: str, episode_title: str, content: str) -> Path:
    """Writes to portfolio/podcast-summaries/<slug>-<date>.md."""
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    slug_source = f"{podcast_title}-{episode_title}" if episode_title else podcast_title
    slug = re.sub(r"[^a-z0-9]+", "-", slug_source.lower()).strip("-")
    filename = f"{slug}-{date.today().isoformat()}.md"
    path = SUMMARIES_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path
