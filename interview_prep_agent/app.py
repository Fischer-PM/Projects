import os

import streamlit as st
from dotenv import load_dotenv

from llm import OLLAMA_DEFAULT_MODEL, Backend, make_client
from agent import (
    compile_prep_guide_stream,
    generate_company_brief,
    generate_interview_themes,
    generate_questions_by_theme,
    save_prep_guide,
)

load_dotenv()

ROLE_LEVELS = ["IC4", "IC5 / Staff", "Senior Staff", "Director", "Group PM"]

st.set_page_config(page_title="PM Interview Prep", page_icon="🎯", layout="wide")


def _init_session_state() -> None:
    defaults = {
        "prep_complete": False,
        "brief": "",
        "themes": [],
        "questions": {},
        "guide": "",
        "guide_company": "",
        "guide_level": "",
        "error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_state() -> None:
    st.session_state.prep_complete = False
    st.session_state.brief = ""
    st.session_state.themes = []
    st.session_state.questions = {}
    st.session_state.guide = ""
    st.session_state.guide_company = ""
    st.session_state.guide_level = ""
    st.session_state.error = None


_init_session_state()

with st.sidebar:
    st.title("PM Interview Prep")
    st.markdown("Generates tailored PM interview prep guides. Saves to `portfolio/interview-prep/`.")
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
    if st.session_state.prep_complete:
        st.success("Guide ready")
    else:
        st.markdown("**Status:** Ready")

st.title("PM Interview Prep")

col_company, col_level = st.columns([3, 1])
with col_company:
    company_input = st.text_input("Target company", placeholder="e.g., Stripe, Notion, Datadog")
with col_level:
    role_level = st.selectbox("Role level", options=ROLE_LEVELS)

ready = (backend == "ollama" and bool(company_input)) or (
    backend == "claude" and bool(company_input and api_key)
)
run_button = st.button("Generate Prep Guide", type="primary", disabled=not ready)

if backend == "claude" and not api_key:
    st.caption("Enter your Anthropic API key in the sidebar.")

if run_button and ready:
    _reset_state()
    st.session_state.guide_company = company_input
    st.session_state.guide_level = role_level

    try:
        client = make_client(backend, api_key)
    except Exception as e:  # noqa: BLE001
        st.error(f"Failed to connect: {e}")
        st.stop()

    progress = st.progress(0, text="Starting...")
    status = st.empty()

    try:
        status.markdown(f"**Step 1 / 4** — Researching {company_input}...")
        brief = generate_company_brief(client, backend, model, company_input, role_level)
        st.session_state.brief = brief
        progress.progress(1 / 5)

        status.markdown("**Step 2 / 4** — Identifying interview themes...")
        themes = generate_interview_themes(client, backend, model, company_input, role_level, brief)
        st.session_state.themes = themes
        progress.progress(2 / 5)

        status.markdown("**Step 3 / 4** — Generating questions...")
        questions = generate_questions_by_theme(client, backend, model, company_input, role_level, themes)
        st.session_state.questions = questions
        progress.progress(3 / 5)

        status.markdown("**Step 4 / 4** — Compiling guide...")
        guide_area = st.empty()
        full_guide = ""

        for text in compile_prep_guide_stream(
            client, backend, model, company_input, role_level, brief, themes, questions
        ):
            full_guide += text
            guide_area.markdown(full_guide)

        st.session_state.guide = full_guide
        st.session_state.prep_complete = True
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

if st.session_state.prep_complete and st.session_state.guide:
    st.divider()
    col_save, col_dl, _ = st.columns([1, 1, 4])

    with col_save:
        if st.button("Save to Portfolio", type="secondary"):
            try:
                saved_path = save_prep_guide(
                    st.session_state.guide_company,
                    st.session_state.guide_level,
                    st.session_state.guide,
                )
                st.success(f"Saved: `{saved_path.name}`")
            except OSError as e:
                st.error(f"Save failed: {e}")

    with col_dl:
        slug = st.session_state.guide_company[:30].replace(" ", "-")
        st.download_button(
            label="Download .md",
            data=st.session_state.guide.encode("utf-8"),
            file_name=f"{slug}-prep.md",
            mime="text/markdown",
        )

    st.markdown(st.session_state.guide)
