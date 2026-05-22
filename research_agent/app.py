import os

import streamlit as st
from dotenv import load_dotenv

from llm import OLLAMA_DEFAULT_MODEL, Backend, make_client
from agent import (
    compile_report_stream,
    generate_research_questions,
    research_question,
    save_report,
)

load_dotenv()

RESEARCH_TYPES = [
    "Competitive Analysis",
    "Feature Teardown",
    "Market Sizing",
    "Tech Architecture Review",
    "Strategy Review",
]

st.set_page_config(
    page_title="PM Research Agent",
    page_icon="🔍",
    layout="wide",
)


def _init_session_state() -> None:
    defaults = {
        "research_complete": False,
        "questions": [],
        "findings": [],
        "report": "",
        "report_topic": "",
        "report_type": "",
        "error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_state() -> None:
    st.session_state.research_complete = False
    st.session_state.questions = []
    st.session_state.findings = []
    st.session_state.report = ""
    st.session_state.report_topic = ""
    st.session_state.report_type = ""
    st.session_state.error = None


_init_session_state()

with st.sidebar:
    st.title("PM Research Agent")
    st.markdown("Generates PM-style research reports. Saves to `portfolio/research-reports/`.")
    st.divider()

    backend: Backend = st.radio(
        "Backend",
        options=["ollama", "claude"],
        format_func=lambda x: "Ollama (local, free)" if x == "ollama" else "Claude API",
        index=0,
    )

    if backend == "ollama":
        model = st.text_input(
            "Ollama model",
            value=OLLAMA_DEFAULT_MODEL,
            help="Run `ollama pull llama3.1:8b` to download. See ollama.com for options.",
        )
        api_key = ""
        st.caption("Ollama must be running at localhost:11434.")
    else:
        model = ""
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=os.getenv("ANTHROPIC_API_KEY", ""),
            help="console.anthropic.com — ~$0.05–0.10/run",
        )

    st.divider()
    if st.session_state.research_complete:
        st.success("Research complete")
    else:
        st.markdown("**Status:** Ready")

st.title("PM Research Agent")

col_topic, col_type = st.columns([3, 1])

with col_topic:
    topic_input = st.text_input(
        "Research topic",
        placeholder="e.g., Stripe's competitive position in embedded finance",
    )

with col_type:
    research_type = st.selectbox("Research type", options=RESEARCH_TYPES)

ready = (backend == "ollama" and bool(topic_input)) or (
    backend == "claude" and bool(topic_input and api_key)
)
run_button = st.button("Generate Report", type="primary", disabled=not ready)

if backend == "claude" and not api_key:
    st.caption("Enter your Anthropic API key in the sidebar.")
elif not topic_input:
    st.caption("Enter a research topic above.")

if run_button and ready:
    _reset_state()
    st.session_state.report_topic = topic_input
    st.session_state.report_type = research_type

    try:
        client = make_client(backend, api_key)
    except Exception as e:
        st.error(f"Failed to connect to {backend}: {e}")
        st.stop()

    progress = st.progress(0, text="Starting...")
    status = st.empty()

    try:
        status.markdown("**Step 1 / 6** — Generating research questions...")
        questions = generate_research_questions(client, backend, model, topic_input, research_type)
        st.session_state.questions = questions
        progress.progress(1 / 7, text="Questions ready")

        findings = []
        for i, question in enumerate(questions):
            status.markdown(f"**Step {i + 2} / 6** — Researching: _{question}_")
            finding = research_question(
                client, backend, model, topic_input, research_type, question, i
            )
            findings.append(finding)
            st.session_state.findings = findings
            progress.progress((i + 2) / 7, text=f"Question {i + 1} of 5 complete")

        status.markdown("**Step 6 / 6** — Compiling report...")
        report_area = st.empty()
        full_report = ""

        for text in compile_report_stream(
            client, backend, model, topic_input, research_type, questions, findings
        ):
            full_report += text
            report_area.markdown(full_report)

        st.session_state.report = full_report
        st.session_state.research_complete = True
        progress.progress(1.0, text="Complete")
        status.empty()

    except Exception as e:
        try:
            import anthropic as _anthropic
            if isinstance(e, _anthropic.AuthenticationError):
                st.session_state.error = "Claude API key is invalid."
            elif isinstance(e, _anthropic.RateLimitError):
                st.session_state.error = "Rate limit reached. Wait a moment and try again."
            elif isinstance(e, _anthropic.APIConnectionError):
                st.session_state.error = f"Claude connection error: {e}"
            else:
                raise
        except (ImportError, Exception):
            pass
        if not st.session_state.error:
            err_str = str(e)
            if "connection" in err_str.lower() or "refused" in err_str.lower():
                st.session_state.error = (
                    "Cannot reach Ollama at localhost:11434. "
                    "Is Ollama running? Start it with: ollama serve"
                )
            else:
                st.session_state.error = f"Error ({type(e).__name__}): {e}"
        progress.empty()
        status.empty()

if st.session_state.error:
    st.error(st.session_state.error)

if st.session_state.research_complete and st.session_state.report:
    st.divider()

    col_save, col_dl, _ = st.columns([1, 1, 4])

    with col_save:
        if st.button("Save to Portfolio", type="secondary"):
            try:
                saved_path = save_report(
                    st.session_state.report_topic,
                    st.session_state.report_type,
                    st.session_state.report,
                )
                st.success(f"Saved: `{saved_path.name}`")
            except OSError as e:
                st.error(f"Save failed: {e}")

    with col_dl:
        topic_slug = st.session_state.report_topic[:40].replace(" ", "-")
        st.download_button(
            label="Download .md",
            data=st.session_state.report.encode("utf-8"),
            file_name=f"{topic_slug}.md",
            mime="text/markdown",
        )

    st.markdown(st.session_state.report)
