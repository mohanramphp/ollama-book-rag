# Copilot Instructions for Ollama Book RAG

## Project Purpose

This is a Windows-first, fully local Retrieval-Augmented Generation (RAG) application. Users add PDF, EPUB, TXT, or Markdown files to a local knowledge base, then ask questions whose answers must be grounded only in retrieved source content. Ollama provides local embeddings and generation; the application must not add external web, cloud, or API dependencies.

Use the project terminology consistently:

- `Knowledge Builder`: ingestion workflow and UI.
- `knowledge_sources/`: original user-provided documents.
- `knowledge_base`: conceptual indexed content. The current Chroma storage directory is `./chroma_db`.
- `query_app.py`: Streamlit chat UI.
- `query.py`: terminal chat client.
- `rag_core.py`: shared implementation and single source of truth.

## Architecture

- `config.py` contains environment-overridable settings.
- `rag_core.py` owns Ollama health checks, model checks, document loading, chunking, deduplication, embedding, Chroma access, retrieval, and streaming answers.
- `knowledge_builder_app.py` is the Streamlit upload/catalog UI and calls `core.ingest_book()`.
- `knowledge_builder.py` is the CLI ingestion wrapper and calls `core.ingest_book()`.
- `query_app.py` is the Streamlit chat UI and calls `core.retrieve_context()` and `core.stream_answer()`.
- `query.py` is the CLI chat wrapper and calls the same shared functions.
- Do not duplicate ingestion, retrieval, prompt, embedding, or persistence logic in an entry-point file. Put shared behavior in `rag_core.py`.

## Runtime and Commands

The supported environment is Windows with Python, Ollama, and the repository virtual environment.

Initial setup:

```bat
setup.bat
```

The setup script creates `venv` and installs `requirements.txt`. Ollama must be installed separately and these models must be pulled before use:

```bat
ollama pull phi4-mini
ollama pull nomic-embed-text
```

Launch the UIs with:

```bat
run_knowledge_builder.bat
run_query.bat
```

CLI usage, after activating the environment:

```bat
call venv\Scripts\activate.bat
py knowledge_builder.py .\knowledge_sources
py query.py
```

Use `py`, not `python`, in Windows command examples and project scripts. Run commands from the repository root.

## Configuration

Configuration is read from environment variables in `config.py`. Important settings include:

- `RAG_SOURCES_DIR`: source-document directory; defaults to `./knowledge_sources`.
- `RAG_PERSIST_DIR`: Chroma directory; defaults to `./chroma_db`.
- `RAG_MANIFEST_PATH`: ingestion catalog path; currently defaults to `./books_manifest.json` for compatibility.
- `RAG_EMBED_MODEL`: embedding model; defaults to `nomic-embed-text`.
- `RAG_DEFAULT_MODEL`: CLI generation model; defaults to `phi4-mini`.
- `RAG_AVAILABLE_MODELS`: models shown by the query UI.
- `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`: recursive chunking settings.
- `RAG_TOP_K`, `RAG_RELEVANCE_THRESHOLD`, `RAG_TEMPERATURE`, `RAG_MAX_HISTORY_TURNS`: retrieval and chat defaults.
- `RAG_EMBED_BATCH_SIZE`, `RAG_SEMANTIC_EMBED_BATCH_SIZE`, `RAG_MAX_RETRIES`, `RAG_RETRY_DELAY_SECONDS`: embedding resilience settings.
- `OLLAMA_HOST`: local Ollama endpoint; defaults to `http://localhost:11434`.

`RAG_BOOKS_DIR` is retained as a backward-compatible fallback for older local configurations. Do not remove it without an explicit migration plan.

## Behavioral Contracts

- Answers must be grounded strictly in retrieved context. Do not weaken or remove the refusal behavior when no relevant context is found.
- Chroma uses cosine distance. Lower scores are more relevant, and relevance filtering uses `score <= relevance_threshold`.
- Preserve the two-part answer format required by `SYSTEM_PROMPT`: `Reasoning:` followed by `Answer:`.
- Preserve exact refusal text when context is insufficient: `I don't have information about this in the provided knowledge source.`
- Preserve content-based deduplication. The manifest hashes extracted text, not raw file bytes, so renamed or re-saved equivalent documents remain duplicates.
- Preserve source metadata such as `source_book`, `chunking_method`, and `chunk_index`; the UIs expose it to users.
- Preserve streamed generation in both UIs where practical.
- Keep the CLI and Streamlit behavior aligned by routing both through `rag_core.py`.
- Health checks should fail with clear actionable messages before Ollama-dependent work begins.

## Data Safety

Treat `knowledge_sources/`, `chroma_db/`, and the manifest as user data. Do not delete, reset, migrate, or rewrite them as part of a routine code change. The reset action in `knowledge_builder_app.py` is intentionally destructive and must remain explicit and clearly labeled.

Do not commit books, generated Chroma files, virtual-environment files, model files, credentials, or local `.env` files. Check `.gitignore` before adding data-related files.

## Implementation Guidance

- Keep changes minimal and consistent with the existing simple module structure.
- Prefer the standard library and existing dependencies over adding new packages.
- Keep path handling cross-platform in Python with `pathlib`, while preserving the Windows batch workflow.
- Escape or validate uploaded filenames before using them as filesystem paths; do not introduce path traversal through uploads.
- Preserve the current accepted extensions: `.pdf`, `.epub`, `.txt`, and `.md`.
- Keep UI-only presentation in the Streamlit modules and domain behavior in `rag_core.py`.
- Avoid broad refactors, unrelated formatting churn, and API renames without updating all four entry points and the README.
- Do not add network calls except the existing local `OLLAMA_HOST` calls required by the application.
- Do not use one-off scripts to rewrite user data or generated indexes.

## Validation

There is no automated test suite currently. At minimum, validate changed Python files with:

```bat
py -m py_compile config.py rag_core.py knowledge_builder.py knowledge_builder_app.py query.py query_app.py
```

For changes involving ingestion, retrieval, models, or prompts, also perform a focused manual check with Ollama available:

1. Confirm `ollama list` contains the embedding model and selected generation model.
2. Run the relevant batch launcher or CLI command from the repository root.
3. Ingest a small test document and verify progress, catalog metadata, and deduplication behavior.
4. Ask a covered question and an unrelated question; verify grounded answering and exact refusal behavior.
5. Confirm source files, Chroma data, and the manifest remain intact.

If Ollama is unavailable, report that runtime validation was not possible; do not replace it with invented test results.

## Documentation

Update `README.md` and `.env.example` when changing commands, paths, environment variables, supported file types, model defaults, or user-visible behavior. Keep the Knowledge Builder naming consistent in filenames, launcher scripts, UI text, CLI help, and documentation.
