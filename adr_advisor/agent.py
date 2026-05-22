"""
ADR Advisor — LLM orchestration layer.
Supports Ollama (local) and Claude API backends via llm.py.
No Streamlit dependencies.
"""

import re
from datetime import date, timedelta
from pathlib import Path
from random import choice
from typing import Generator

from llm import Backend, complete, stream_complete

GENERATED_ADRS_DIR = Path(__file__).parent.parent / "portfolio" / "generated-adrs"

FICTIONAL_COMPANIES = [
    "Vantara", "Nexar", "Cordia", "Prism", "Halcyon",
    "Meridian", "Stratum", "Celeris", "Orion", "Luminal",
]

SYSTEM_PROMPT = """You are a senior platform PM writing Architecture Decision Records for a portfolio. \
Your ADRs follow a specific style:

Voice and structure:
- Written in retrospective voice — the decision was made 6–12 months ago
- Status section names a real operational outcome, not just "Accepted"
- Architecture section includes a Mermaid flowchart diagram (before/after or topology)
- Context section presents exactly 3 lettered options with trade-offs
- Decision section names the chosen option and argues against alternatives explicitly
- Consequences has three subsections: "What worked", "What we got wrong", "What persists"
- "What we got wrong" includes a named incident with specifics: timeline, detection vector, \
number of users affected, or other concrete detail
- "What persists" is honest about the lasting constraint the decision introduced

Tone:
- PM-practitioner voice, not academic
- Numbers and specifics wherever plausible
- Honest about organizational friction, timeline overruns, and unintended consequences
- No hedging — assertions about what happened"""


def suggest_company_name() -> str:
    return choice(FICTIONAL_COMPANIES)


def analyze_decision(client, backend: Backend, model: str, decision_text: str, domain: str) -> str:
    """Extracts problem, identifies 3 options, surfaces the forcing function."""
    prompt = (
        f"Domain: {domain}\n"
        f"Decision: {decision_text}\n\n"
        "Analyze this architectural decision. Return:\n\n"
        "PROBLEM: [One sentence — what operational pressure forced this decision]\n\n"
        "OPTION A: [Name] — [2-sentence description and primary trade-off]\n"
        "OPTION B: [Name] — [2-sentence description]\n"
        "OPTION C: [Name] — [2-sentence description]\n\n"
        "RECOMMENDED: [A, B, or C] — [One sentence on why]\n\n"
        "FORCING FUNCTION: [What made the status quo untenable]\n\n"
        "Be specific to the domain. Name real technologies or patterns where relevant."
    )
    return complete(client, backend, SYSTEM_PROMPT, prompt, 700, model)


def generate_adr_stream(
    client,
    backend: Backend,
    model: str,
    decision_text: str,
    company_name: str,
    domain: str,
    analysis: str,
) -> Generator[str, None, None]:
    """Generates the full ADR document. Yields text chunks."""
    acceptance_date = date.today() - timedelta(days=270)
    acceptance_str = acceptance_date.strftime("%B %Y")

    prompt = (
        f"Write a complete Architecture Decision Record for {company_name}.\n\n"
        f"Decision: {decision_text}\n"
        f"Domain: {domain}\n"
        f"Acceptance date (retrospective): {acceptance_str}\n\n"
        f"Analysis:\n{analysis}\n\n"
        "Generate the full ADR:\n\n"
        f"# ADR: [Concise decision title]\n"
        f"*{company_name} — internal architecture decision record*\n\n"
        "## Status\n"
        f"Accepted — {acceptance_str}. [One honest sentence on the operational outcome 9 months later.]\n\n"
        "## Architecture: Before and After\n\n"
        "```mermaid\n"
        "[flowchart LR or TD showing before-state and after-state. "
        "Use real service/component names relevant to the domain. 6–10 nodes.]\n"
        "```\n\n"
        "*[One sentence caption explaining what changed.]*\n\n"
        "## Context\n\n"
        "[3–4 paragraphs: the problem, what made the status quo untenable, constraints.]\n\n"
        "**Option A — [Name]:** [Description + trade-offs]\n\n"
        "**Option B — [Name]:** [Description + trade-offs]\n\n"
        "**Option C — [Name]:** [Description + trade-offs]\n\n"
        "## Decision\n\n"
        "[Chosen option in the first sentence. 2–3 paragraphs arguing against the alternatives.]\n\n"
        "## Consequences\n\n"
        "### What worked\n\n"
        "[2–3 specific operational improvements with concrete signals.]\n\n"
        "### What we got wrong\n\n"
        "[A named incident: what happened, when detected, impact, root cause.]\n\n"
        "### What persists\n\n"
        "[The lasting constraint this decision introduced — be honest it's a real trade-off.]\n"
    )
    yield from stream_complete(client, backend, SYSTEM_PROMPT, prompt, 3000, model)


def save_adr(company_name: str, decision_text: str, content: str) -> Path:
    """Saves to portfolio/generated-adrs/<company-slug>-<decision-slug>-<date>.md"""
    GENERATED_ADRS_DIR.mkdir(parents=True, exist_ok=True)
    company_slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
    decision_slug = re.sub(r"[^a-z0-9]+", "-", decision_text.lower()).strip("-")[:40]
    filename = f"{company_slug}-{decision_slug}-{date.today().isoformat()}.md"
    path = GENERATED_ADRS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path
