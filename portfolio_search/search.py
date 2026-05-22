#!/usr/bin/env python3
"""
Search your PM portfolio using BM25 ranking.
Usage: python search.py "your query"
       python search.py "kafka vs sqs" --top 10
"""

import re
import sys
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    print("Missing dependency. Run: pip install rank-bm25")
    sys.exit(1)

PORTFOLIO_DIR = Path(__file__).parent.parent / "portfolio"
DEFAULT_TOP_N = 5
EXCERPT_CHARS = 300
SKIP_NAMES = {".gitkeep", "README.md"}


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z]{2,}\b", text.lower())


def strip_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"^\s*[-*>]\s+", "", text, flags=re.MULTILINE)
    return text


def load_documents() -> list[tuple[Path, str]]:
    docs = []
    for path in sorted(PORTFOLIO_DIR.rglob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            docs.append((path, text))
        except OSError:
            pass
    return docs


def find_excerpt(text: str, query_tokens: list[str]) -> str:
    plain = strip_markdown(text)
    for token in query_tokens:
        match = re.search(re.escape(token), plain, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 60)
            raw = plain[start : start + EXCERPT_CHARS].strip()
            return re.sub(r"\s+", " ", raw)
    return re.sub(r"\s+", " ", plain[:EXCERPT_CHARS].strip())


def search(query: str, top_n: int = DEFAULT_TOP_N) -> None:
    docs = load_documents()
    if not docs:
        print(f"No documents found under {PORTFOLIO_DIR}")
        return

    paths, texts = zip(*docs)
    corpus = [tokenize(t) for t in texts]
    bm25 = BM25Okapi(corpus)

    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    print(f'\nTop {top_n} results for: "{query}"\n{"─" * 50}')
    shown = 0
    for i in ranked:
        if scores[i] == 0:
            break
        if shown >= top_n:
            break
        rel = paths[i].relative_to(PORTFOLIO_DIR.parent)
        excerpt = find_excerpt(texts[i], query_tokens)
        print(f"\n{shown + 1}. {rel}")
        print(f"   Score: {scores[i]:.2f}")
        print(f"   ...{excerpt}...")
        shown += 1

    if shown == 0:
        print("No matching documents found.")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    top_n = DEFAULT_TOP_N
    if "--top" in args:
        idx = args.index("--top")
        try:
            top_n = int(args[idx + 1])
            args = args[:idx] + args[idx + 2 :]
        except (IndexError, ValueError):
            print("Usage: --top <number>")
            sys.exit(1)

    query = " ".join(args)
    search(query, top_n)


if __name__ == "__main__":
    main()
