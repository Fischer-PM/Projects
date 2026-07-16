import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv

from llm import OLLAMA_DEFAULT_MODEL, Backend, make_client
from agent import (
    chunk_transcript,
    clean_transcript,
    compile_summary_stream,
    extract_chunk_notes,
    save_summary,
)

load_dotenv()

st.set_page_config(page_title="Podcast Summarizer", page_icon="🎙️", layout="wide")


def _init_session_state() -> None:
    defaults = {
        "summary_complete": False,
        "podcast_title": "",
        "episode_title": "",
        "summary": "",
        "error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_state() -> None:
    st.session_state.summary_complete = False
    st.session_state.summary = ""
    st.session_state.error = None


_init_session_state()

with st.sidebar:
    st.title("Podcast Summarizer")
    st.markdown(
        "Extracts key points, quotes, and frameworks from a podcast transcript "
        "and compiles a learning summary. Saves to `portfolio/podcast-summaries/`."
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
    if st.session_state.summary_complete:
        st.success("Summary ready")
    else:
        st.markdown("**Status:** Ready")
    st.caption("Example use case: Lenny's Podcast episode transcripts.")

st.title("Podcast Transcript Summarizer")

col_podcast, col_episode, col_guest = st.columns(3)
with col_podcast:
    podcast_title = st.text_input("Podcast name", placeholder="Lenny's Podcast")
with col_episode:
    episode_title = st.text_input("Episode title", placeholder="How to run a great retro")
with col_guest:
    guest = st.text_input("Guest (optional)", placeholder="Jane Doe")

uploaded_file = st.file_uploader(
    "Upload transcript (.txt, .vtt, .srt)", type=["txt", "vtt", "srt"]
)
transcript_input = st.text_area(
    "Or paste transcript text",
    placeholder="Paste the full episode transcript here...",
    height=260,
)

raw_transcript = ""
if uploaded_file is not None:
    raw_transcript = uploaded_file.read().decode("utf-8", errors="ignore")
elif transcript_input:
    raw_transcript = transcript_input

cleaned = clean_transcript(raw_transcript) if raw_transcript else ""
chunks = chunk_transcript(cleaned) if cleaned else []

if chunks:
    word_count = len(cleaned.split())
    st.caption(f"{word_count:,} words · {len(chunks)} segment(s) to process")

ready = bool(podcast_title) and bool(chunks) and (backend == "ollama" or bool(api_key))
run_button = st.button("Generate Summary", type="primary", disabled=not ready)

if run_button and ready:
    _reset_state()

    try:
        client = make_client(backend, api_key)
    except Exception as e:  # noqa: BLE001
        st.error(f"Failed to connect: {e}")
        st.stop()

    total_steps = len(chunks) + 1
    progress = st.progress(0, text="Starting...")
    status = st.empty()

    try:
        notes = []
        for i, chunk in enumerate(chunks):
            status.markdown(f"**Step {i + 1} / {total_steps}** — Reading segment {i + 1} of {len(chunks)}...")
            note = extract_chunk_notes(
                client, backend, model, chunk, i, len(chunks), podcast_title, episode_title
            )
            notes.append(note)
            progress.progress((i + 1) / (total_steps + 1))

        status.markdown(f"**Step {total_steps} / {total_steps}** — Compiling summary...")
        summary_area = st.empty()
        full_summary = ""

        for text in compile_summary_stream(
            client, backend, model, podcast_title, episode_title, guest, notes
        ):
            full_summary += text
            summary_area.markdown(full_summary)

        st.session_state.podcast_title = podcast_title
        st.session_state.episode_title = episode_title
        st.session_state.summary = full_summary
        st.session_state.summary_complete = True
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

if st.session_state.summary_complete and st.session_state.summary:
    st.divider()
    col_save, col_dl, _ = st.columns([1, 1, 4])

    with col_save:
        if st.button("Save to Portfolio", type="secondary"):
            try:
                saved_path = save_summary(
                    st.session_state.podcast_title, st.session_state.episode_title, st.session_state.summary
                )
                st.success(f"Saved: `{saved_path.name}`")
            except OSError as e:
                st.error(f"Save failed: {e}")

    with col_dl:
        st.download_button(
            label="Download .md",
            data=st.session_state.summary.encode("utf-8"),
            file_name=f"podcast-summary-{date.today().isoformat()}.md",
            mime="text/markdown",
        )

    st.markdown(st.session_state.summary)
