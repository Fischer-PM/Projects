# Projects

A suite of local-first AI tools built for PM research, interview prep, and portfolio generation. All tools run on [Ollama](https://ollama.com) by default — no API key, no cost. Claude API support is available as an optional upgrade.

## Tools

| Tool | Directory | What it does |
|---|---|---|
| **PM Research Agent** | `research_agent/` | Generates structured PM research reports: Competitive Analysis, Feature Teardown, Market Sizing, Tech Architecture Review, Strategy Review |
| **PM Interview Prep Agent** | `interview_prep_agent/` | Tailored interview prep guides by company and role level (IC4 → Director) |
| **ADR Advisor** | `adr_advisor/` | Architecture Decision Records in retrospective style — Mermaid diagrams, honest consequences |
| **Portfolio Search** | `portfolio_search/` | BM25-powered CLI search across portfolio markdown files. No AI backend required |
| **PM Digest Generator** | `digest_agent/` | Structured PM briefings across up to 6 topics with cross-cutting themes |

See [TOOLS.md](TOOLS.md) for setup instructions and full documentation.

## Quick Start

```bash
# Install Ollama (free, local)
brew install ollama   # or download from ollama.com
ollama pull llama3.1:8b
ollama serve

# Run any tool
cd research_agent
pip install -r requirements.txt
streamlit run app.py
```

All Streamlit tools default to Ollama. Switch to Claude API from the sidebar if preferred.
