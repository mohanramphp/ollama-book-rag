---
applyTo: "**/*_app.py"
---

# Streamlit Rules

- Keep UI presentation and Streamlit session-state handling in the Streamlit modules; keep domain behavior in `rag_core.py`.
- Perform Ollama health and required-model checks before vector-store access, ingestion, retrieval, or generation.
- Preserve streamed answers with `st.write_stream()` where the existing flow supports streaming.
- Preserve source transparency: retrieved source names, chunking method, scores, and relevant excerpts should remain available to users.
- Preserve the explicit refusal path when retrieval returns no results under the configured relevance threshold.
- Keep the destructive reset action clearly labeled and explicit. It may remove the vector database, manifest, and source files only when the user activates that action.
- Uploaded files must remain confined to `config.SOURCES_DIR`; validate or safely normalize uploaded filenames before constructing destination paths.
- Keep Streamlit rerun and cache behavior intentional. Do not move model or vector-store initialization into unrelated UI branches without checking rerun effects.
- Update visible labels and help text consistently with the `Knowledge Builder`, `knowledge_sources`, and knowledge-base terminology.
