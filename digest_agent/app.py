import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv

from llm import OLLAMA_DEFAULT_MODEL, Backend, make_client
from agent import compile_digest_stream, parse_topics, research_topic, save_digest

load_dotenv()

TIME_HORIZONS = ["This week", "This month", "Last quarter"]

st.set_page_config(page_title="PM Digest", page_icon="📰", layout="wide")


def _init_session_state() -> None:
    defaults = {
        "digest_complete": False,
        "topics": [],
        "findings": [],
        "digest": "",
        "error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_state() -> None:
    st.session_state.digest_complete = False
    st.session_state.topics = []
    st.session_state.findings = []
    st.session_state.digest = ""
    st.session_state.error = None


_init_session_state()

with st.sidebar:
    st.title("PM Digest")
    st.markdown("Generates a PM briefing across topics. Saves to `portfolio/digests/`.")
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
    if st.session_state.digest_complete:
        st.success("Digest ready")
    else:
        st.markdown("**Status:** Ready")
    st.caption("Based on training knowledge. Verify before acting.")

st.title("PM Digest Generator")

col_topics, col_horizon = st.columns([3, 1])
with col_topics:
    topics_input = st.text_area(
        "Topics to cover",
        placeholder="One per line, or comma-separated.\ne.g.\nStripe vs. Adyen competitive positioning\nOpenAI API pricing changes",
        height=130,
    )
with col_horizon:
    time_horizon = st.selectbox("Time horizon", options=TIME_HORIZONS)
    st.caption("Up to 6 topics.")

topics_parsed = parse_topics(topics_input) if topics_input else []
ready = bool(topics_parsed) and (backend == "ollama" or bool(api_key))
run_button = st.button("Generate Digest", type="primary", disabled=not ready)

if topics_parsed:
    st.caption(f"Topics: {', '.join(topics_parsed)}")

if run_button and ready:
    _reset_state()

    try:
        client = make_client(backend, api_key)
    except Exception as e:  # noqa: BLE001
        st.error(f"Failed to connect: {e}")
        st.stop()

    total_steps = len(topics_parsed) + 1
    progress = st.progress(0, text="Starting...")
    status = st.empty()

    try:
        findings = []
        for i, topic in enumerate(topics_parsed):
            status.markdown(f"**Step {i + 1} / {total_steps}** — Researching: _{topic}_")
            finding = research_topic(client, backend, model, topic, time_horizon)
            findings.append(finding)
            progress.progress((i + 1) / (total_steps + 1))

        status.markdown(f"**Step {total_steps} / {total_steps}** — Compiling digest...")
        digest_area = st.empty()
        full_digest = ""

        for text in compile_digest_stream(client, backend, model, topics_parsed, findings, time_horizon):
            full_digest += text
            digest_area.markdown(full_digest)

        st.session_state.topics = topics_parsed
        st.session_state.digest = full_digest
        st.session_state.digest_complete = True
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

if st.session_state.digest_complete and st.session_state.digest:
    st.divider()
    col_save, col_dl, _ = st.columns([1, 1, 4])

    with col_save:
        if st.button("Save to Portfolio", type="secondary"):
            try:
                saved_path = save_digest(st.session_state.topics, st.session_state.digest)
                st.success(f"Saved: `{saved_path.name}`")
            except OSError as e:
                st.error(f"Save failed: {e}")

    with col_dl:
        st.download_button(
            label="Download .md",
            data=st.session_state.digest.encode("utf-8"),
            file_name=f"pm-digest-{date.today().isoformat()}.md",
            mime="text/markdown",
        )

    st.markdown(st.session_state.digest)
