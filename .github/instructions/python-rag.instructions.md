---
applyTo: "**/*.py"
---

# Python and RAG Rules

- Use `py` rather than `python` in Windows command examples, CLI help, and project scripts.
- Preserve supported source extensions: `.pdf`, `.epub`, `.txt`, and `.md`.
- Preserve content-based deduplication: hashes are based on extracted text, not raw file bytes.
- Preserve source metadata, including `source_name`, `chunking_method`, and `chunk_index`.
- Keep semantic chunks bounded by `RAG_SEMANTIC_MAX_CHUNK_SIZE` after semantic splitting.
- Treat embedding-model or chunking-setting changes as reindexing events; do not mix incompatible vectors in the same Chroma collection.
- Preserve transactional ingestion: write the manifest only after all chunks are embedded successfully, and clean up IDs from failed attempts.
- Chroma uses cosine distance. Lower scores are more relevant, and relevant results satisfy `score <= relevance_threshold`.
- Answers must use retrieved context only. Do not weaken refusal behavior or introduce outside knowledge.
- Preserve the exact refusal text: `I don't have information about this in the provided knowledge source.`
- Preserve the required `Reasoning:` then `Answer:` response structure from `SYSTEM_PROMPT`.
- Preserve streamed generation in both UI and CLI flows where practical.
- Keep Ollama calls local through `OLLAMA_HOST`; do not add web, cloud, telemetry, or external API dependencies.
- Use capped exponential retry delays for transient embedding failures.
- Health and model checks should produce clear actionable errors before Ollama-dependent work begins.
- Prefer the standard library and existing dependencies. Avoid broad refactors, unrelated formatting churn, and public API renames.
- Validate changed Python files with:

```bat
py -m py_compile config.py rag_core.py knowledge_builder.py knowledge_builder_app.py query.py query_app.py
```
