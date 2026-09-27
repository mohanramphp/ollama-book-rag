---
applyTo: "**/*.py"
---

# Architecture

- `rag_core.py` is the single source of truth for Ollama health checks, model checks, document loading, chunking, deduplication, embedding, Chroma access, retrieval, prompts, and streamed answers.
- `knowledge_builder_app.py` is the Streamlit ingestion/catalog UI and calls `core.ingest_source()`.
- `knowledge_builder.py` is the CLI ingestion wrapper and calls `core.ingest_source()`.
- `query_app.py` is the Streamlit chat UI and calls `core.retrieve_context()` and `core.stream_answer()`.
- `query.py` is the CLI chat wrapper and calls the same shared functions.
- Keep entry points thin. Do not duplicate ingestion, retrieval, embedding, persistence, prompt, or model-health logic outside `rag_core.py`.
- Keep CLI and Streamlit behavior aligned. A shared behavior change normally belongs in `rag_core.py`, with only presentation-specific changes in the entry point.
- Preserve the current naming: `Knowledge Builder`, `knowledge_sources/`, `knowledge_base`, `query_app.py`, `query.py`, and `rag_core.py`.
- Configuration belongs in `config.py` and must remain environment-overridable; do not hardcode paths, models, or tuning values in entry points.
- Use `pathlib.Path` for filesystem paths and keep the Windows batch workflow working from the repository root.
