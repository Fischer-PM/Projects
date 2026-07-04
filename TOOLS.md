# Fischer PM Tools

A suite of local-first AI tools built for PM research, interview prep, and portfolio generation. All tools run on [Ollama](https://ollama.com) by default — no API key, no cost. Claude API support is available as an optional upgrade.

---

## Tools

### 1. PM Research Agent
**`research_agent/`**

Generates structured PM research reports across five research types: Competitive Analysis, Feature Teardown, Market Sizing, Tech Architecture Review, and Strategy Review.

**How it works:** Generates 5 research questions from your topic, answers each independently, then compiles a cohesive report with Executive Summary, Key Findings, Strategic Implications, and Open Questions.

```bash
cd research_agent
pip install -r requirements.txt
streamlit run app.py
```

---

### 2. PM Interview Prep Agent
**`interview_prep_agent/`**

Generates tailored PM interview prep guides for a target company and role level (IC4 through Director).

**Output includes:** Company PM culture brief, 5 interview themes, 2 behavioral questions per theme with coaching notes, background positioning mapped to your specific experience, and 5 questions to ask the interviewer.

```bash
cd interview_prep_agent
pip install -r requirements.txt
streamlit run app.py
```

---

### 3. ADR Advisor
**`adr_advisor/`**

Generates Architecture Decision Records in retrospective style — as if the decision was accepted 9 months ago and you're documenting what happened, including what went wrong.

**Output includes:** Mermaid architecture diagram (before/after), 3-option context analysis, decision rationale, and an honest Consequences section with a named incident. Matches the style of `portfolio/platform-pm-playbook/adrs/`.

```bash
cd adr_advisor
pip install -r requirements.txt
streamlit run app.py
```

---

### 4. Portfolio Search
**`portfolio_search/`**

BM25-powered CLI search across all portfolio markdown files. No AI backend required — runs entirely locally.

```bash
cd portfolio_search
pip install -r requirements.txt
python search.py "kafka vs sqs"
python search.py "vendor tiering" --top 10
```

---

### 5. PM Digest Generator
**`digest_agent/`**

Generates a structured PM briefing across up to 6 topics: what moved, why it matters for PMs, one open question per topic — plus cross-cutting themes and a "What to Watch" forward-looking section.

```bash
cd digest_agent
pip install -r requirements.txt
streamlit run app.py
```

---

### 6. Data Mapping Prototype
**`data_mapping_prototype/`**

A self-contained HTML walkthrough that helps someone onboard a source dataset onto a shared schema (`commerce.order_event`, used by both a real-time Kafka stream and a nightly batch load). No backend or install — a single static page.

**Walkthrough steps:**
1. **Understand the schema** — every field, its type, required/optional status, and a real example, grouped into core / stream-only / batch-only
2. **Map your fields** — paste a sample source record (a legacy checkout export is prefilled); each schema field gets an auto-suggested source mapping you confirm or correct, with transform notes (casing, date format, type casts, derived fields)
3. **Validate & preview** — the mapped output record plus a required-field checklist, flagging what's missing vs. what just needs a transform
4. **Trace the data flow** — where the record goes after ingestion, with separate diagrams for the stream and batch paths and their downstream consumers

A Stream/Batch toggle in the header changes which fields, mappings, and flow diagram are shown throughout.

```bash
cd data_mapping_prototype
open index.html   # or just double-click it — no server required
```

---

## Backends

All Streamlit tools support two backends, selectable from the sidebar:

| Backend | Cost | Setup |
|---|---|---|
| **Ollama (default)** | Free | Install Ollama, pull a model |
| **Claude API** | ~$0.05–0.10/run | Anthropic API key |

### Ollama Setup

1. Install Ollama: [ollama.com](https://ollama.com)
2. Pull a model:
   ```bash
   ollama pull llama3.1:8b   # recommended
   ollama pull mistral        # alternative, strong writing quality
   ollama pull llama3.2       # smaller and faster
   ```
3. Start Ollama (if not already running):
   ```bash
   ollama serve
   ```
4. Select **Ollama (local, free)** in any tool's sidebar

### Claude API Setup (optional)

1. Get a key at [console.anthropic.com](https://console.anthropic.com)
2. Add to a `.env` file in the tool directory:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Select **Claude API** in the sidebar

---

## Output

Generated content saves as markdown files into `portfolio/`:

| Tool | Output directory |
|---|---|
| Research Agent | `portfolio/research-reports/` |
| Interview Prep | `portfolio/interview-prep/` |
| ADR Advisor | `portfolio/generated-adrs/` |
| Digest Generator | `portfolio/digests/` |
| Portfolio Search | reads from `portfolio/` — no output |

---

## Architecture

Each Streamlit tool follows the same three-file pattern:

- **`agent.py`** — all LLM logic, no Streamlit imports, independently testable
- **`app.py`** — Streamlit UI and orchestration, imports from `agent.py`
- **`llm.py`** — unified backend abstraction (`complete()` and `stream_complete()` for both Ollama and Claude)

The separation means you can test `agent.py` functions directly without a running Streamlit server, and swap backends without touching business logic.
