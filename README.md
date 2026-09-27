# Ollama Knowledge Sources RAG

A fully offline Retrieval-Augmented Generation (RAG) system: upload your own
knowledge sources, and ask questions that get answered strictly from their content — no
internet calls, no outside knowledge, no accounts. Runs entirely on your
machine via Ollama.

---

## What's in this project

| File                                          | Purpose                                                                                                                                                                                  |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `config.py`                                   | Every setting in one place (paths, models, chunk size, retrieval defaults). Overridable via environment variables — see `.env.example`.                                                  |
| `rag_core.py`                                 | The actual logic: loading knowledge sources, chunking, embedding, dedup tracking, retrieval, and chat. Everything else imports from here, so there's one implementation to keep correct. |
| `knowledge_builder_app.py`                    | **Streamlit UI** — add knowledge sources, watch live ingestion progress, browse a catalog of what's ingested.                                                                            |
| `query_app.py`                                | **Streamlit UI** — chat interface with markdown/code rendering, model picker, and sliders for top_k / relevance threshold / temperature.                                                 |
| `knowledge_builder.py`                        | CLI equivalent of the Knowledge Builder UI, for scripting/automation.                                                                                                                    |
| `query.py`                                    | CLI equivalent of the query UI, for quick terminal testing.                                                                                                                              |
| `requirements.txt`                            | This project's exact dependencies, isolated in its own virtual environment.                                                                                                              |
| `setup.bat`                                   | One-time setup: creates the venv, installs dependencies.                                                                                                                                 |
| `run_knowledge_builder.bat` / `run_query.bat` | Activate the venv and launch each UI.                                                                                                                                                    |
| `.env.example`                                | Every config value you can override, documented.                                                                                                                                         |

---

## System this was built and tuned for

| Component | Spec                                                                                    |
| --------- | --------------------------------------------------------------------------------------- |
| CPU       | 12th Gen Intel i7-12700H                                                                |
| RAM       | 32 GB                                                                                   |
| GPU       | Intel Arc A370M (4 GB VRAM) — too small for reliable model offload, so this runs on CPU |
| OS        | Windows 11                                                                              |

Everything here runs on CPU. 32 GB of RAM is what makes SLMs (and mid-size
LLMs, for comparison) comfortable despite no real GPU acceleration.

---

## One-time setup

1. **Install Ollama** from https://ollama.com/download (no account needed for local use)
2. **Pull the models**:
   ```
   ollama pull phi4-mini
   ollama pull nomic-embed-text
   ```
   Optionally, for later SLM vs. LLM comparison:
   ```
   ollama pull qwen3:8b
   ollama pull gemma3:4b
   ```
3. **Unzip this project** anywhere, e.g. `F:\mohan-work\ollama-book-rag`
4. **Run the setup script** — this creates an isolated virtual environment in `.\venv` and installs only this project's packages into it (nothing touches your global Python):
   ```
   setup.bat
   ```

You only need to do this setup once. If `python`/`py` isn't recognized at all, install Python from https://python.org (check "Add python.exe to PATH" during install) before running `setup.bat`.

---

## Running it

**Build the knowledge base** (upload UI):

```
run_knowledge_builder.bat
```

Opens a browser tab. Drag in PDF/EPUB/TXT/MD files, choose recursive or semantic chunking, and watch the sources ingest with a live progress bar. Already-ingested sources (checked by content, not filename) are automatically skipped.

**Ask questions** (chat UI):

```
run_query.bat
```

Opens a browser tab. Pick a model from the sidebar, adjust `top_k` / relevance threshold / temperature if needed, and start chatting. Code in answers renders as proper formatted code blocks. Each answer has an expandable "Retrieved sources" section showing exactly which source chunks and relevance scores were used.

You can run both at once (two terminals) — they share the same on-disk database.

**CLI alternative**, if you prefer the terminal over a browser:

```
call venv\Scripts\activate.bat
py knowledge_builder.py ./knowledge_sources
py query.py
```

---

## Architecture

```
Knowledge sources (PDF/EPUB/TXT/MD)
        |
        v
   Knowledge Builder (chunk + embed)
        |
        v
  Vector DB (Chroma, cosine distance, stored locally in ./chroma_db)
        ^                      |
        | retrieved chunks     v
  You (ask a question) --> SLM (grounded, no outside calls) --> reasoning + answer
```

The model never queries the internet and refuses (rather than guesses) when
retrieved content isn't relevant enough to the question.

---

## Key design decisions

- **Isolated environment**: `setup.bat` creates a dedicated `venv` so this project's dependencies never conflict with or pollute your global Python install.
- **Single source of truth**: all four entry points (`knowledge_builder_app.py`, `query_app.py`, `knowledge_builder.py`, `query.py`) call into `rag_core.py` — no duplicated logic to fall out of sync.
- **Health checks**: both UIs and both CLI scripts check that Ollama is actually reachable (and that required models are pulled) before doing anything, and fail with a clear message instead of a raw connection traceback.
- **Content-based dedup**: knowledge sources are hashed (SHA-256) on upload, so a renamed re-upload of the same file is still caught.
- **Cosine distance**: the vector store explicitly uses cosine similarity (bounded 0–2), so the relevance threshold is a meaningful, tunable number rather than an arbitrary guess against an unknown default metric.
- **Resilient ingestion**: embedding happens in retryable batches (both for normal and semantic chunking) with capped exponential backoff, and failed attempts clean up their chunk IDs before reporting an error.
- **Bounded semantic chunks**: semantic boundaries are preserved, but oversized semantic chunks are split at `RAG_SEMANTIC_MAX_CHUNK_SIZE` before embedding so generation context remains predictable.
- **Configuration-aware indexing**: the manifest records the embedding model and chunking settings used. Changing those settings requires an explicit knowledge-base reset and rebuild rather than silently mixing incompatible vectors.
- **Configurable, not hardcoded**: every tunable value (chunk size, semantic maximum, top_k, temperature, batch sizes, retry behavior) lives in `config.py` and can be overridden via environment variables without touching code.
- **Streaming + transparency**: answers stream token-by-token, and every answer shows its `Reasoning:` (which source it used) before the `Answer:`, plus an expandable view of the raw retrieved chunks and their scores.

---

## Models used

| Role                            | Model                    | Why                                                                             |
| ------------------------------- | ------------------------ | ------------------------------------------------------------------------------- |
| Generator (SLM), default        | `phi4-mini` (3.8B)       | MIT licensed, ~3 GB, stays tightly grounded in context, 128K context window     |
| Generator (Small LLM)           | `gemma3:4b` / `llama3.2` | Balanced speed and reasoning for local CPU use                                  |
| Generator (LLM, for comparison) | `qwen3:8b` / `qwen3:14b` | Stronger reasoning, still workable on CPU                                       |
| Embeddings                      | `nomic-embed-text`       | Shared by both, so retrieval quality doesn't confound an SLM vs. LLM comparison |

Switch models anytime from the sidebar dropdown in `query_app.py`, or by changing `RAG_DEFAULT_MODEL` for the CLI version.

---

## Troubleshooting

- **"Ollama isn't reachable"** on either UI — make sure the Ollama app/service is actually running (check Task Manager), then refresh the page.
- **"Required model(s) not pulled yet"** — run the `ollama pull ...` command shown in the error.
- **`python`/`py` not recognized** — install Python from python.org with "Add to PATH" checked, or disable the Microsoft Store alias at Settings > Apps > Advanced app settings > App execution aliases.
- **A question the knowledge sources clearly cover gets refused** — lower the relevance threshold slider (or `RAG_RELEVANCE_THRESHOLD`) slightly; it defaults to a fairly strict `0.8` on cosine distance.
- **Semantic chunking fails partway with a connection error** — this is CPU load, not a real crash; it retries automatically. If it keeps failing, close other heavy applications and re-run.

---

## Not done yet / possible next steps

- [ ] Automated benchmark script comparing SLM vs. LLM (latency + answer quality) across a fixed question set
- [ ] Investigate Ollama's Vulkan backend for partial Intel Arc GPU offload once it matures further on Windows
- [ ] Optional authentication if this is ever exposed beyond your own machine (currently assumes local, single-user use)

---

_Everything in this project runs entirely on-device. No API keys, no accounts, and no data leaves the machine at any stage._
