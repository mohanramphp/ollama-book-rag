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

## Specialized Instructions

Detailed rules are split into scoped files under `.github/instructions/`:

- `architecture.instructions.md`: module responsibilities, ownership boundaries, and naming.
- `python-rag.instructions.md`: Python, RAG, grounding, and validation rules.
- `streamlit.instructions.md`: Streamlit UI, state, upload, and reset behavior.

These files load automatically for matching source files. Keep this file focused on rules that apply to every task.

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

## Configuration and Compatibility

Configuration belongs in `config.py` and is environment-overridable. Read `.env.example` before changing settings. The current source directory is `./knowledge_sources`, Chroma is stored in `./chroma_db`, and the manifest keeps its legacy default filename for compatibility.

`RAG_BOOKS_DIR` remains a backward-compatible fallback. Do not remove it without an explicit migration plan.

## Non-Negotiable Behavior

- Answers must remain grounded strictly in retrieved context; preserve the exact refusal text and the `Reasoning:` then `Answer:` format.
- Keep CLI and Streamlit behavior aligned through `rag_core.py`.
- Do not add web, cloud, telemetry, or external API dependencies. Ollama calls must remain local through `OLLAMA_HOST`.
- Treat user documents and generated indexes as data, not disposable build output.

## Data Safety

Treat `knowledge_sources/`, `chroma_db/`, and the manifest as user data. Do not delete, reset, migrate, or rewrite them during routine work. The reset action in `knowledge_builder_app.py` is intentionally destructive and must remain explicit and clearly labeled.

Do not commit source documents, generated Chroma files, virtual-environment files, model files, credentials, or local `.env` files. Check `.gitignore` before adding data-related files.

## Validation

There is no automated test suite currently. At minimum, validate changed Python files with:

```bat
py -m py_compile config.py rag_core.py knowledge_builder.py knowledge_builder_app.py query.py query_app.py
```

For ingestion, retrieval, model, or prompt changes, perform a focused manual check with Ollama when available: verify models with `ollama list`, run the relevant launcher or CLI, test ingestion and deduplication, ask a covered and unrelated question, and confirm user data remains intact. If Ollama is unavailable, report that runtime validation was not possible.

## Documentation

Update `README.md` and `.env.example` when changing commands, paths, environment variables, supported file types, model defaults, or user-visible behavior. Keep the Knowledge Builder naming consistent in filenames, launcher scripts, UI text, CLI help, and documentation.
