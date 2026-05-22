"""
Unified LLM interface — supports Ollama (local, free) and Claude API.

Ollama backend uses the OpenAI-compatible endpoint at localhost:11434.
Claude backend uses the Anthropic SDK with prompt caching.
"""

from typing import Generator, Literal

Backend = Literal["ollama", "claude"]

CLAUDE_MODEL = "claude-sonnet-4-6"
OLLAMA_DEFAULT_MODEL = "llama3.1:8b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


def make_client(backend: Backend, api_key: str = ""):
    if backend == "claude":
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    else:
        from openai import OpenAI
        return OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def complete(
    client,
    backend: Backend,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    model: str = "",
) -> str:
    """Single completion call. Returns response text."""
    if backend == "claude":
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text.strip()
    else:
        response = client.chat.completions.create(
            model=model or OLLAMA_DEFAULT_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()


def stream_complete(
    client,
    backend: Backend,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    model: str = "",
) -> Generator[str, None, None]:
    """Streaming completion. Yields text chunks from both backends."""
    if backend == "claude":
        with client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            yield from stream.text_stream
    else:
        response = client.chat.completions.create(
            model=model or OLLAMA_DEFAULT_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
