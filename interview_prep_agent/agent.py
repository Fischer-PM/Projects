"""
PM Interview Prep Agent — LLM orchestration layer.
Supports Ollama (local) and Claude API backends via llm.py.
No Streamlit dependencies.
"""

import re
from datetime import date
from pathlib import Path
from typing import Generator

from llm import Backend, complete, stream_complete

INTERVIEW_PREP_DIR = Path(__file__).parent.parent / "portfolio" / "interview-prep"

SYSTEM_PROMPT = """You are a senior product management coach preparing a candidate for PM interviews. \
The candidate is Stephen Fischer — a platform PM with this background:

- Capital One: Omnichannel messaging platform (billions of messages/year), KYC/CDD \
information collection workflows, notifications infrastructure across multiple channels
- Anywhere Real Estate: 0→1 mobile app launch deployed to 200,000 agents
- Developer portal scaling: 4B+ annual API calls, 90+ APIs, 200+ vendor integrations

Your writing follows these principles:
- Direct and specific — name the exact dynamic, not the category
- PM-practitioner voice — write as someone who has done this, not observed it
- Concrete framing — numbers, tradeoffs, and mechanisms over abstractions
- No filler: never write "it is important to note" or "in conclusion"
- Assertions first, reasoning second"""

LEVEL_CONTEXT = {
    "IC4": "mid-level PM, 2-4 years experience, expected to own a feature area independently",
    "IC5 / Staff": "senior PM, 5-8 years, expected to define strategy for a product area and influence cross-functional teams",
    "Senior Staff": "staff-level PM, 8+ years, expected to drive multi-team programs, org influence, and roadmap across a portfolio",
    "Director": "director-level, leading a team of PMs, accountable for organizational outcomes, hiring, and business impact",
    "Group PM": "group PM / GPM, managing other PMs, responsible for a product portfolio and PM team development",
}


def generate_company_brief(client, backend: Backend, model: str, company: str, role_level: str) -> str:
    level_desc = LEVEL_CONTEXT.get(role_level, role_level)
    prompt = (
        f"Company: {company}\n"
        f"Role level: {role_level} ({level_desc})\n\n"
        "Write a 3-paragraph brief covering:\n"
        "1. What this company is really optimizing for as a PM organization\n"
        "2. What PMs at this level are expected to own, decide, and deliver\n"
        "3. What distinguishes strong candidates from adequate ones at this level\n\n"
        "Be specific. If you know concrete things about this company's PM culture, use them."
    )
    return complete(client, backend, SYSTEM_PROMPT, prompt, 700, model)


def generate_interview_themes(
    client, backend: Backend, model: str, company: str, role_level: str, brief: str
) -> list[str]:
    """Returns 5 interview themes. Raises ValueError on malformed output."""
    prompt = (
        f"Company: {company}\n"
        f"Role level: {role_level}\n\n"
        f"Company brief:\n{brief}\n\n"
        "List exactly 5 interview themes that will be emphasized for this role. "
        "Not generic PM competencies — the specific things this company cares about at this level.\n\n"
        "Return only the 5 themes, numbered 1–5. One line each. No explanation."
    )
    text = complete(client, backend, SYSTEM_PROMPT, prompt, 300, model)
    themes = re.findall(r"^\s*\d+[.):\s]+(.+)$", text, re.MULTILINE)
    if len(themes) < 3:
        raise ValueError(f"Unexpected theme format: {text[:200]}")
    return themes[:5]


def generate_questions_by_theme(
    client, backend: Backend, model: str, company: str, role_level: str, themes: list[str]
) -> dict[str, list[str]]:
    """Returns {theme: [q1, q2]} for all 5 themes."""
    themes_block = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(themes))
    prompt = (
        f"Company: {company}\n"
        f"Role level: {role_level}\n\n"
        f"Interview themes:\n{themes_block}\n\n"
        "For each theme, write 2 behavioral interview questions. "
        "Questions should be the actual phrasing an interviewer would use.\n\n"
        "Format exactly as:\n"
        "THEME: [theme name]\n"
        "Q1: [question]\n"
        "Q2: [question]\n\n"
        "Repeat for all 5 themes."
    )
    text = complete(client, backend, SYSTEM_PROMPT, prompt, 1000, model)

    result: dict[str, list[str]] = {}
    blocks = re.split(r"THEME:\s*", text, flags=re.IGNORECASE)
    for block in blocks:
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        theme_name = lines[0].strip()
        questions = re.findall(r"Q\d+:\s*(.+)", block, re.IGNORECASE)
        if theme_name and questions:
            result[theme_name] = questions[:2]

    if not result:
        all_questions = re.findall(r"Q\d+:\s*(.+)", text, re.IGNORECASE)
        for i, theme in enumerate(themes):
            base = i * 2
            result[theme] = all_questions[base : base + 2] if base < len(all_questions) else []

    return result


def compile_prep_guide_stream(
    client,
    backend: Backend,
    model: str,
    company: str,
    role_level: str,
    brief: str,
    themes: list[str],
    questions: dict[str, list[str]],
) -> Generator[str, None, None]:
    """Compiles the full interview prep guide. Yields text chunks."""
    prep_date = date.today().isoformat()
    level_desc = LEVEL_CONTEXT.get(role_level, role_level)
    themes_block = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(themes))
    questions_block = "\n\n".join(
        f"**{theme}**\n" + "\n".join(f"- {q}" for q in qs)
        for theme, qs in questions.items()
    )
    prompt = (
        f"Compile a complete interview prep guide for:\n"
        f"Company: {company}\n"
        f"Role: {role_level} PM ({level_desc})\n"
        f"Date: {prep_date}\n\n"
        f"Structure:\n\n"
        f"# Interview Prep: {company} — {role_level}\n"
        f"*Generated: {prep_date}*\n\n"
        "## Company Context\n[Synthesize the brief into actionable interview framing]\n\n"
        "## What They're Evaluating at This Level\n[The real bar]\n\n"
        "## Interview Themes\n[Numbered list of the 5 themes]\n\n"
        "## Questions by Theme\n"
        "[For each theme: header, both questions, 2-sentence coaching note on what a strong answer demonstrates]\n\n"
        "## Positioning Your Background\n"
        "[How Stephen's Capital One messaging platform, KYC/CDD, and Anywhere RE mobile "
        "launch maps to what this company is looking for. Be specific about which stories land hardest per theme.]\n\n"
        "## Questions to Ask Them\n"
        "[5 specific questions that signal strategic thinking and domain depth]\n\n"
        f"COMPANY BRIEF:\n{brief}\n\n"
        f"THEMES:\n{themes_block}\n\n"
        f"QUESTIONS:\n{questions_block}"
    )
    yield from stream_complete(client, backend, SYSTEM_PROMPT, prompt, 3000, model)


def save_prep_guide(company: str, role_level: str, content: str) -> Path:
    """Saves to portfolio/interview-prep/<company-slug>-<level>-<date>.md"""
    INTERVIEW_PREP_DIR.mkdir(parents=True, exist_ok=True)
    company_slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    level_slug = re.sub(r"[^a-z0-9]+", "-", role_level.lower()).strip("-")
    filename = f"{company_slug}-{level_slug}-{date.today().isoformat()}.md"
    path = INTERVIEW_PREP_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path
