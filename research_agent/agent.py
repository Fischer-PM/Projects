"""
PM Research Agent — LLM orchestration layer.
Supports Ollama (local) and Claude API backends via llm.py.
No Streamlit dependencies. All functions independently testable.
"""

import re
from datetime import date
from pathlib import Path
from typing import Generator

from llm import Backend, complete, stream_complete

RESEARCH_REPORTS_DIR = Path(__file__).parent.parent / "portfolio" / "research-reports"
MAX_TOKENS_QUESTION = 1200
MAX_TOKENS_COMPILE = 4000

SYSTEM_PROMPT = """You are a senior product manager and analyst generating research reports \
for a PM portfolio. Your writing follows these principles without exception:

Voice and style:
- Lead with a sharp thesis or assertion, not a topic sentence
- Every paragraph earns its place with a direct claim backed by reasoning
- No filler phrases: never write "it is important to note," "it's worth mentioning," \
"in conclusion," or "this highlights the need for"
- Write as a practitioner, not as an analyst summarizing a category
- Make the PM-relevant implication explicit — what does this mean for how you build, \
price, or position a product?
- Use concrete specifics over abstractions where possible

Structure:
- Headers should name what the section argues, not just what it contains
- Bullet points are acceptable for lists of parallel items; not for disguising paragraphs
- Do not repeat the question you were asked at the start of your answer

Frameworks you may apply (without labeling them as frameworks):
- Jobs to be Done reasoning
- Platform-product tension analysis
- Eigenquestion identification
- Switching cost and moat analysis
- ADR-style consequence reasoning (what improved, what we got wrong, what persists)
- Activation and retention metric decomposition

Output:
- Markdown formatting throughout
- No trailing "key takeaway" boxes or summary bullets at section ends
- Assertions first, evidence second"""

TYPE_GUIDANCE = {
    "Competitive Analysis": (
        "Focus on differentiated positioning, moat durability, "
        "go-to-market mechanics, and the competitive surface area each player "
        "has chosen to contest."
    ),
    "Feature Teardown": (
        "Focus on the design decisions and trade-offs behind the feature, "
        "the user behavior it assumes, what it makes possible vs. impossible, "
        "and what the PM lesson is."
    ),
    "Market Sizing": (
        "Focus on the demand structure, the unit economics that determine "
        "addressability, the segments where the economics are best, "
        "and the assumptions that move the number most."
    ),
    "Tech Architecture Review": (
        "Focus on the architectural bets and their consequences: what the "
        "design makes easy, what it makes hard, what the failure modes are, "
        "and what a PM needs to understand to work effectively inside it."
    ),
    "Strategy Review": (
        "Focus on the diagnosis behind the strategy, the guiding policy it "
        "implies, whether the actions cohere, and what the strategy rules out."
    ),
}


def generate_research_questions(
    client,
    backend: Backend,
    model: str,
    topic: str,
    research_type: str,
) -> list[str]:
    """Generates 5 focused PM research questions. Raises ValueError on malformed output."""
    guidance = TYPE_GUIDANCE.get(research_type, "")
    prompt = (
        f"Topic: {topic}\n"
        f"Research type: {research_type}\n"
        f"{guidance}\n\n"
        "Generate exactly 5 specific, high-leverage research questions for this topic. "
        "These questions should be the ones that, if answered well, produce a complete "
        f"{research_type} a PM could act on.\n\n"
        "Return only the 5 questions, numbered 1–5. No preamble, no explanation."
    )
    text = complete(client, backend, SYSTEM_PROMPT, prompt, 600, model)
    questions = re.findall(r"^\s*\d+[.):\s]+(.+)$", text, re.MULTILINE)
    if len(questions) < 3:
        raise ValueError(f"Unexpected question format: {text[:300]}")
    return questions[:5]


def research_question(
    client,
    backend: Backend,
    model: str,
    topic: str,
    research_type: str,
    question: str,
    question_index: int,
) -> str:
    """Researches a single question. Returns markdown prose."""
    prompt = (
        f"Topic: {topic}\n"
        f"Research type: {research_type}\n"
        f"Question {question_index + 1}: {question}\n\n"
        "Answer this question in 3–5 paragraphs of analytical prose. "
        "Write as a senior PM who knows this domain. "
        "Be specific about mechanics, numbers where known, and the PM-relevant implications. "
        "No hedging language."
    )
    return complete(client, backend, SYSTEM_PROMPT, prompt, MAX_TOKENS_QUESTION, model)


def compile_report_stream(
    client,
    backend: Backend,
    model: str,
    topic: str,
    research_type: str,
    questions: list[str],
    findings: list[str],
) -> Generator[str, None, None]:
    """Compiles findings into a formatted PM report. Yields text chunks."""
    report_date = date.today().isoformat()
    findings_block = "\n\n".join(
        f"### Research Question {i + 1}: {q}\n\n{f}"
        for i, (q, f) in enumerate(zip(questions, findings))
    )
    compile_prompt = (
        f'Compile a {research_type} on "{topic}" for a PM portfolio.\n\n'
        f"Date: {report_date}\n\n"
        "Use this exact structure:\n\n"
        f"# {topic} — {research_type}\n"
        f"*Generated: {report_date}*\n\n"
        "## Executive Summary\n"
        "[2–3 sentences. Sharpest insight first.]\n\n"
        "## Research Questions\n"
        "[Numbered list of the 5 research questions]\n\n"
        "## Key Findings\n\n"
        "### [Q1 title rewritten as an argument]\n"
        "[Integrated findings + synthesis]\n\n"
        "### [Q2 title]\n[etc.]\n\n"
        "## Strategic Implications\n"
        "[3–5 paragraphs. PM-level so-what.]\n\n"
        "## Open Questions\n"
        "[3–5 specific questions this research surfaces but doesn't answer.]\n\n"
        "Eliminate hedging. Executive Summary must be a thesis, not a table of contents.\n\n"
        f"RAW FINDINGS:\n\n{findings_block}"
    )
    yield from stream_complete(
        client, backend, SYSTEM_PROMPT, compile_prompt, MAX_TOKENS_COMPILE, model
    )


def save_report(topic: str, research_type: str, content: str) -> Path:
    """Writes to portfolio/research-reports/<slug>-<type>-<date>.md."""
    RESEARCH_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    type_slug = research_type.lower().replace(" ", "-")
    filename = f"{slug}-{type_slug}-{date.today().isoformat()}.md"
    path = RESEARCH_REPORTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path
