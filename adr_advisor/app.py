import os

import streamlit as st
from dotenv import load_dotenv

from llm import OLLAMA_DEFAULT_MODEL, Backend, make_client
from agent import analyze_decision, generate_adr_stream, save_adr, suggest_company_name

load_dotenv()

DOMAINS = [
    "Messaging / Async",
    "API Design",
    "Data Storage",
    "Auth / Identity",
    "Infrastructure / Compute",
    "Observability",
    "Other",
]

st.set_page_config(page_title="ADR Advisor", page_icon="📐", layout="wide")


def _init_session_state() -> None:
    defaults = {
        "adr_complete": False,
        "analysis": "",
        "adr": "",
        "adr_company": "",
        "adr_decision": "",
        "show_analysis": False,
        "error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_state() -> None:
    st.session_state.adr_complete = False
    st.session_state.analysis = ""
    st.session_state.adr = ""
    st.session_state.adr_company = ""
    st.session_state.adr_decision = ""
    st.session_state.show_analysis = False
    st.session_state.error = None


_init_session_state()

with st.sidebar:
    st.title("ADR Advisor")
    st.markdown(
        "Generates Architecture Decision Records in retrospective style — "
        "Mermaid diagrams, honest consequences. Saves to `portfolio/generated-adrs/`."
    )
    st.divider()

    backend: Backend = st.radio(
        "Backend",
        options=["ollama", "claude"],
        format_func=lambda x: "Ollama (local, free)" if x == "ollama" else "Claude API",
        index=0,
    )

    if backend == "ollama":
        model = st.text_input("Ollama model", value=OLLAMA_DEFAULT_MODEL)
        api_key = ""
        st.caption("Ollama must be running at localhost:11434.")
    else:
        model = ""
        api_key = st.text_input(
            "Anthropic API Key", type="password", value=os.getenv("ANTHROPIC_API_KEY", "")
        )

    st.divider()
    if st.session_state.adr_complete:
        st.success("ADR ready")
    else:
        st.markdown("**Status:** Ready")
    st.markdown("**Style:** Matches `portfolio/platform-pm-playbook/adrs/`")

st.title("ADR Advisor")

decision_input = st.text_area(
    "Describe the architectural decision",
    placeholder=(
        "e.g., We need to decide between synchronous REST calls vs. async queues "
        "for inter-service communication in our notification pipeline."
    ),
    height=120,
)

col_company, col_domain = st.columns([2, 2])
with col_company:
    company_input = st.text_input(
        "Fictional company name",
        placeholder=f"e.g., {suggest_company_name()} (leave blank to auto-assign)",
    )
with col_domain:
    domain = st.selectbox("Domain", options=DOMAINS)

ready = bool(decision_input) and (backend == "ollama" or bool(api_key))
run_button = st.button("Generate ADR", type="primary", disabled=not ready)

if run_button and ready:
    _reset_state()
    company_name = company_input.strip() if company_input.strip() else suggest_company_name()
    st.session_state.adr_company = company_name
    st.session_state.adr_decision = decision_input

    try:
        client = make_client(backend, api_key)
    except Exception as e:  # noqa: BLE001
        st.error(f"Failed to connect: {e}")
        st.stop()

    progress = st.progress(0, text="Starting...")
    status = st.empty()

    try:
        status.markdown(f"**Step 1 / 2** — Analyzing decision for *{company_name}*...")
        analysis = analyze_decision(client, backend, model, decision_input, domain)
        st.session_state.analysis = analysis
        progress.progress(1 / 3)

        status.markdown("**Step 2 / 2** — Drafting ADR...")
        adr_area = st.empty()
        full_adr = ""

        for text in generate_adr_stream(
            client, backend, model, decision_input, company_name, domain, analysis
        ):
            full_adr += text
            adr_area.markdown(full_adr)

        st.session_state.adr = full_adr
        st.session_state.adr_complete = True
        progress.progress(1.0, text="Complete")
        status.empty()

    except Exception as e:  # noqa: BLE001
        err = str(e)
        if "connection" in err.lower() or "refused" in err.lower():
            st.session_state.error = "Cannot reach Ollama at localhost:11434. Run: ollama serve"
        else:
            st.session_state.error = f"Error ({type(e).__name__}): {e}"
        progress.empty()
        status.empty()

if st.session_state.error:
    st.error(st.session_state.error)

if st.session_state.adr_complete and st.session_state.adr:
    st.divider()
    col_save, col_dl, col_analysis, _ = st.columns([1, 1, 1, 3])

    with col_save:
        if st.button("Save to Portfolio", type="secondary"):
            try:
                saved_path = save_adr(
                    st.session_state.adr_company,
                    st.session_state.adr_decision,
                    st.session_state.adr,
                )
                st.success(f"Saved: `{saved_path.name}`")
            except OSError as e:
                st.error(f"Save failed: {e}")

    with col_dl:
        company_slug = st.session_state.adr_company.replace(" ", "-").lower()
        st.download_button(
            label="Download .md",
            data=st.session_state.adr.encode("utf-8"),
            file_name=f"adr-{company_slug}.md",
            mime="text/markdown",
        )

    with col_analysis:
        if st.button("Show Analysis"):
            st.session_state.show_analysis = not st.session_state.show_analysis

    if st.session_state.show_analysis and st.session_state.analysis:
        with st.expander("Decision Analysis (Step 1)", expanded=True):
            st.markdown(f"```\n{st.session_state.analysis}\n```")

    st.markdown(st.session_state.adr)
